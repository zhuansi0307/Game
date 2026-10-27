package com.partsvision.app.ui

import android.app.Application
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.partsvision.app.ai.ClaudeService
import com.partsvision.app.ai.ReferencePart
import com.partsvision.app.data.Part
import com.partsvision.app.data.PartRepository
import com.partsvision.app.data.SettingsStore
import com.partsvision.app.ml.ImageEmbedderHelper
import com.partsvision.app.ml.DetectedPart
import com.partsvision.app.ml.LiveFrame
import com.partsvision.app.ml.LiveScanner
import com.partsvision.app.ml.MatchResult
import com.partsvision.app.ml.ObjectFinder
import com.partsvision.app.ml.OcrHelper
import com.partsvision.app.ml.PileResult
import com.partsvision.app.ml.PileScanner
import com.partsvision.app.ml.PartMatcher
import com.partsvision.app.util.ImageUtils
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject

data class AiVerdict(val partNumber: String, val confidence: Int, val textOnPart: String, val reason: String)

data class RecognizeState(
    val photo: Bitmap? = null,
    val analyzing: Boolean = false,
    val ocrLines: List<String> = emptyList(),
    val matches: List<MatchResult> = emptyList(),
    val aiLoading: Boolean = false,
    val ai: AiVerdict? = null,
    val error: String? = null,
)

/** Cloud answers for live objects, keyed by [DetectedPart.key]. */
data class LiveAiState(
    val loadingKey: Int? = null,
    val verdicts: Map<Int, AiVerdict> = emptyMap(),
    val error: String? = null,
)

data class PileState(val running: Boolean = false, val progress: Float = 0f, val result: PileResult? = null, val error: String? = null) {
    val active: Boolean get() = running || result != null || error != null
}

data class SketchState(
    val generating: Boolean = false,
    val progressChars: Int = 0,
    val svg: String? = null,
    val error: String? = null,
)

class AppViewModel(app: Application) : AndroidViewModel(app) {
    val repo = PartRepository(app)
    val settings = SettingsStore(app)
    private val ocr = OcrHelper()
    private val embedder by lazy { ImageEmbedderHelper(app) }
    private val finder by lazy { ObjectFinder(app) }
    private val pileScanner by lazy { PileScanner(embedder, finder) }

    val parts: StateFlow<List<Part>> = repo.parts

    private val _recognize = MutableStateFlow(RecognizeState())
    val recognize: StateFlow<RecognizeState> = _recognize.asStateFlow()

    private val _sketch = MutableStateFlow(SketchState())
    val sketch: StateFlow<SketchState> = _sketch.asStateFlow()

    private val _live = MutableStateFlow<LiveFrame?>(null)
    val live: StateFlow<LiveFrame?> = _live.asStateFlow()

    private val _liveAi = MutableStateFlow(LiveAiState())
    val liveAi: StateFlow<LiveAiState> = _liveAi.asStateFlow()
    private var liveScanner: LiveScanner? = null
    private var lastAiAt = 0L
    private val aiAskedAt = HashMap<Int, Long>()

    private val _pile = MutableStateFlow(PileState())
    val pile: StateFlow<PileState> = _pile.asStateFlow()
    private var pileJob: Job? = null

    /** True while stored photos are re-embedded after a model upgrade. */
    private val _reindexing = MutableStateFlow(false)
    val reindexing: StateFlow<Boolean> = _reindexing.asStateFlow()

    private var recognizeJob: Job? = null
    private var sketchJob: Job? = null

    init {
        viewModelScope.launch {
            repo.load()
            if (repo.embeddingVersion != ImageEmbedderHelper.VERSION) {
                _reindexing.value = true
                repo.reembed(ImageEmbedderHelper.VERSION) { photoFeatures(ImageUtils.scaleDown(it, 1024)) }
                _reindexing.value = false
            }
        }
    }

    /** Library-side features of a still photo; blocking, call off the main thread. */
    private fun photoFeatures(photo: Bitmap): ImageEmbedderHelper.PhotoFeatures {
        // The part cut out of its background, matching how live and pile scans cut out candidates.
        val cutouts = runCatching { finder.mainObject(photo) }.getOrNull()?.let { (set, p) ->
            listOf(finder.maskedCrop(photo, set, p))
        }.orEmpty()
        return embedder.embedPhoto(photo, cutouts)
    }

    suspend fun decode(uri: Uri): Bitmap? = withContext(Dispatchers.IO) { ImageUtils.decode(getApplication(), uri) }

    // ---------------------------------------------------------------- recognition

    /** Analyzer for the live camera; results are published on [live]. */
    fun newLiveScanner(): LiveScanner =
        LiveScanner(embedder, ocr, finder, parts = { parts.value }, onResult = ::onLiveFrame).also { liveScanner = it }

    fun clearLive() {
        _live.value = null
        _liveAi.value = LiveAiState()
        aiAskedAt.clear()
    }

    private fun onLiveFrame(result: LiveFrame) {
        _live.value = result
        val keys = result.objects.map { it.key }.toSet()
        _liveAi.update { s -> s.copy(verdicts = s.verdicts.filterKeys { it in keys }) }

        // Ask the cloud model about the biggest object the library is unsure about — at most one
        // request at a time, one every few seconds, and the same object again only after a while.
        if (!settings.cloudAssist || !settings.hasApiKey || _liveAi.value.loadingKey != null) return
        val now = System.currentTimeMillis()
        if (now - lastAiAt < LIVE_AI_COOLDOWN_MS) return
        val target = result.objects
            .filter { !it.confident && now - (aiAskedAt[it.key] ?: 0L) > LIVE_AI_REPEAT_MS }
            .maxByOrNull { it.box.width() * it.box.height() } ?: return
        lastAiAt = now
        aiAskedAt[target.key] = now
        _liveAi.update { it.copy(loadingKey = target.key, error = null) }
        val crop = ObjectFinder.crop(result.frame, target.box, pad = 0.2f)
        viewModelScope.launch {
            try {
                val verdict = identifyWithAi(crop, emptyList(), target.candidates.map { it.match })
                _liveAi.update { it.copy(loadingKey = null, verdicts = it.verdicts + (target.key to verdict)) }
            } catch (e: Exception) {
                _liveAi.update { it.copy(loadingKey = null, error = e.message ?: "AI 识别失败") }
            }
        }
    }

    /** Finds every library part in a still [frame] of a pile (takes a few seconds). */
    fun scanPile(frame: Bitmap) {
        pileJob?.cancel()
        _pile.value = PileState(running = true)
        pileJob = viewModelScope.launch {
            _pile.value = try {
                PileState(result = withContext(Dispatchers.Default) {
                    pileScanner.scan(frame, parts.value) { p -> _pile.update { it.copy(progress = p) } }
                })
            } catch (e: Exception) {
                PileState(error = e.message ?: "整堆识别失败")
            }
        }
    }

    fun clearPile() {
        pileJob?.cancel()
        _pile.value = PileState()
    }

    /** Adds [obj]'s crop from [frame] to [part]'s photos so future scans match it better. */
    fun confirmLive(part: Part, obj: DetectedPart, frame: Bitmap) {
        val crop = ObjectFinder.crop(frame, obj.box, pad = 0.15f)
        viewModelScope.launch { savePart(part.partNumber, "", "", listOf(crop)) }
    }

    fun recognize(photo: Bitmap) {
        recognizeJob?.cancel()
        _recognize.value = RecognizeState(photo = photo, analyzing = true)
        recognizeJob = viewModelScope.launch {
            try {
                val lines = runCatching { ocr.readLines(photo) }.getOrDefault(emptyList())
                val matches = withContext(Dispatchers.Default) {
                    val features = photoFeatures(photo)
                    val ranked = PartMatcher.rank(parts.value, features.embeddings, lines)
                    // Look-alike parts are ordered by the region-by-region comparison.
                    val regions = PartMatcher.regionScores(features.regions.firstOrNull(), ranked)
                    ranked.sortedByDescending { m -> regions[m.part.id]?.let { 2f + it } ?: m.score }
                }
                _recognize.update { it.copy(analyzing = false, ocrLines = lines, matches = matches) }
                if (settings.cloudAssist && settings.hasApiKey) askAi(photo, lines, matches)
            } catch (e: Exception) {
                _recognize.update { it.copy(analyzing = false, error = e.message ?: "识别失败") }
            }
        }
    }

    fun retryAi() {
        val s = _recognize.value
        val photo = s.photo ?: return
        viewModelScope.launch { askAi(photo, s.ocrLines, s.matches) }
    }

    private suspend fun askAi(photo: Bitmap, lines: List<String>, matches: List<MatchResult>) {
        if (!settings.hasApiKey) {
            _recognize.update { it.copy(error = "请先在“设置”中填写 API Key") }
            return
        }
        _recognize.update { it.copy(aiLoading = true, error = null) }
        try {
            val verdict = identifyWithAi(photo, lines, matches)
            _recognize.update { it.copy(aiLoading = false, ai = verdict) }
        } catch (e: Exception) {
            _recognize.update { it.copy(aiLoading = false, error = e.message ?: "AI 识别失败") }
        }
    }

    private suspend fun identifyWithAi(photo: Bitmap, lines: List<String>, matches: List<MatchResult>): AiVerdict =
        withContext(Dispatchers.IO) {
            val references = matches.take(MAX_AI_CANDIDATES).map { m ->
                val ref = m.part.photos.firstOrNull()?.let { BitmapFactory.decodeFile(it.path) }
                ReferencePart(m.part.partNumber, m.part.name, ref?.let { ImageUtils.toBase64Jpeg(ImageUtils.scaleDown(it, 512), 80) })
            }
            val raw = ClaudeService(settings.apiKey, settings.model)
                .identifyPart(ImageUtils.toBase64Jpeg(ImageUtils.scaleDown(photo, 1024)), lines, references)
            parseVerdict(raw)
        }

    private fun parseVerdict(raw: String): AiVerdict {
        val json = JSONObject(raw.substring(raw.indexOf('{'), raw.lastIndexOf('}') + 1))
        return AiVerdict(
            partNumber = json.optString("part_number"),
            confidence = json.optInt("confidence"),
            textOnPart = json.optString("text_on_part"),
            reason = json.optString("reason"),
        )
    }

    fun clearRecognition() {
        recognizeJob?.cancel()
        _recognize.value = RecognizeState()
    }

    // ---------------------------------------------------------------- library

    /** Saves photos under [partNumber]; creates the part if needed. Returns the part id. */
    suspend fun savePart(partNumber: String, name: String, note: String, photos: List<Bitmap>): String {
        val withEmbeddings = withContext(Dispatchers.Default) {
            photos.map { ImageUtils.scaleDown(it, 1024).let { b -> b to photoFeatures(b) } }
        }
        return repo.upsert(partNumber, name, note, withEmbeddings).id
    }

    fun deletePart(id: String) = viewModelScope.launch { repo.delete(id) }

    fun deletePhoto(partId: String, photoId: String) = viewModelScope.launch { repo.deletePhoto(partId, photoId) }

    // ---------------------------------------------------------------- sketch → drawing

    fun generateDrawing(sketch: Bitmap, isPhoto: Boolean, description: String, partNumber: String) {
        if (!settings.hasApiKey) {
            _sketch.value = SketchState(error = "请先在“设置”中填写 API Key")
            return
        }
        sketchJob?.cancel()
        _sketch.value = SketchState(generating = true)
        sketchJob = viewModelScope.launch {
            try {
                val svg = withContext(Dispatchers.IO) {
                    ClaudeService(settings.apiKey, settings.model).sketchToDrawing(
                        sketchPngBase64 = ImageUtils.toBase64Png(ImageUtils.scaleDown(sketch, 1568)),
                        isPhoto = isPhoto,
                        description = description,
                        partNumber = partNumber,
                    ) { chars -> _sketch.update { it.copy(progressChars = chars) } }
                }
                _sketch.value = SketchState(svg = svg)
            } catch (e: Exception) {
                _sketch.value = SketchState(error = e.message ?: "生成失败")
            }
        }
    }

    fun clearDrawing() {
        sketchJob?.cancel()
        _sketch.value = SketchState()
    }

    override fun onCleared() {
        ocr.close()
        embedder.close()
        finder.close()
        pileJob?.cancel()
    }

    companion object {
        private const val MAX_AI_CANDIDATES = 5
        private const val LIVE_AI_COOLDOWN_MS = 8_000L
        private const val LIVE_AI_REPEAT_MS = 30_000L
    }
}
