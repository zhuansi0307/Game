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
import com.partsvision.app.ml.MatchResult
import com.partsvision.app.ml.OcrHelper
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

    val parts: StateFlow<List<Part>> = repo.parts

    private val _recognize = MutableStateFlow(RecognizeState())
    val recognize: StateFlow<RecognizeState> = _recognize.asStateFlow()

    private val _sketch = MutableStateFlow(SketchState())
    val sketch: StateFlow<SketchState> = _sketch.asStateFlow()

    private var recognizeJob: Job? = null
    private var sketchJob: Job? = null

    init {
        viewModelScope.launch { repo.load() }
    }

    suspend fun decode(uri: Uri): Bitmap? = withContext(Dispatchers.IO) { ImageUtils.decode(getApplication(), uri) }

    // ---------------------------------------------------------------- recognition

    fun recognize(photo: Bitmap) {
        recognizeJob?.cancel()
        _recognize.value = RecognizeState(photo = photo, analyzing = true)
        recognizeJob = viewModelScope.launch {
            try {
                val lines = runCatching { ocr.readLines(photo) }.getOrDefault(emptyList())
                val embedding = withContext(Dispatchers.Default) { embedder.embed(photo) }
                val matches = withContext(Dispatchers.Default) { PartMatcher.rank(parts.value, embedding, lines) }
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
            val verdict = withContext(Dispatchers.IO) {
                val references = matches.take(MAX_AI_CANDIDATES).map { m ->
                    val ref = m.part.photos.firstOrNull()?.let { BitmapFactory.decodeFile(it.path) }
                    ReferencePart(m.part.partNumber, m.part.name, ref?.let { ImageUtils.toBase64Jpeg(ImageUtils.scaleDown(it, 512), 80) })
                }
                val raw = ClaudeService(settings.apiKey, settings.model)
                    .identifyPart(ImageUtils.toBase64Jpeg(ImageUtils.scaleDown(photo, 1024)), lines, references)
                parseVerdict(raw)
            }
            _recognize.update { it.copy(aiLoading = false, ai = verdict) }
        } catch (e: Exception) {
            _recognize.update { it.copy(aiLoading = false, error = e.message ?: "AI 识别失败") }
        }
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
            photos.map { ImageUtils.scaleDown(it, 1024).let { b -> b to embedder.embed(b) } }
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
    }

    companion object {
        private const val MAX_AI_CANDIDATES = 5
    }
}
