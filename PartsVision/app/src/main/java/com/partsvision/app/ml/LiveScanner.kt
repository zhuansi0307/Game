package com.partsvision.app.ml

import android.graphics.Bitmap
import android.graphics.Matrix
import android.graphics.Rect
import android.os.SystemClock
import android.util.Log
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import com.partsvision.app.data.Part

/** A library part with its appearance similarity (raw cosine) smoothed over recent frames. */
data class LiveCandidate(val match: MatchResult, val smoothedScore: Float) {
    /** 0..1 for display: text hits count fully, appearance goes through [Calibration]. */
    val confidence: Float get() =
        if (match.isTextHit) maxOf(match.textScore, Calibration.confidence(smoothedScore)) else Calibration.confidence(smoothedScore)
}

/** One object found in the frame and what it most likely is. */
data class DetectedPart(
    /** Stable across frames while the object stays in view (tracking id). */
    val key: Int,
    /** Position in [LiveFrame.frame] pixels. */
    val box: Rect,
    /** Best candidates first; empty only when the library is empty. */
    val candidates: List<LiveCandidate>,
    /** Part-number-like text read inside the box. */
    val readNumber: String?,
    /** No object was detected, so this is just the centre of the frame. */
    val isFallback: Boolean,
) {
    val top: LiveCandidate? get() = candidates.firstOrNull()

    /** Top candidate is a text hit, or clearly ahead of the runner-up on appearance. */
    val confident: Boolean get() {
        val t = top ?: return false
        val second = candidates.getOrNull(1)?.smoothedScore ?: 0f
        return t.match.isTextHit ||
            (t.smoothedScore >= LiveScanner.CONFIDENT_SCORE && t.smoothedScore - second >= LiveScanner.CONFIDENT_MARGIN)
    }

    /** Worth labelling as "maybe" even when not confident. */
    val plausible: Boolean get() = top?.let { it.match.isTextHit || it.smoothedScore >= LiveScanner.MAYBE_SCORE } == true
}

/** Result of analyzing one camera frame. */
class LiveFrame(
    /** The upright frame the boxes refer to. */
    val frame: Bitmap,
    val objects: List<DetectedPart>,
    val frameMs: Long,
    val frameNo: Int,
    /** Set when frames cannot be analyzed (e.g. a model failed to load). */
    val problem: String? = null,
)

/**
 * CameraX analyzer that works like a YOLO-style detector over the user's own parts library:
 * ML Kit finds every object in the frame (with tracking ids), each object's crop is embedded and
 * matched against the library, and OCR text inside a box counts towards that box's match.
 * Scores are smoothed per tracked object so labels do not flicker. To keep the frame rate up
 * with several objects in view, a tracked object's embedding is reused for a short while and at
 * most [MAX_EMBEDS_PER_FRAME] objects are re-embedded per frame; OCR runs on alternate frames.
 */
class LiveScanner(
    private val embedder: ImageEmbedderHelper,
    private val ocr: OcrHelper,
    private val finder: ObjectFinder,
    private val parts: () -> List<Part>,
    private val onResult: (LiveFrame) -> Unit,
    private val intervalMs: Long = 100,
) : ImageAnalysis.Analyzer {

    @Volatile var lastFrame: Bitmap? = null
        private set

    private var lastRun = 0L
    private var frameNo = 0
    private var lastLines: List<OcrLine> = emptyList()
    /** tracking key → (part id → smoothed score) */
    private val smoothed = HashMap<Int, HashMap<String, Float>>()
    /** tracking key → (embedding, when it was computed) */
    private val embeddings = HashMap<Int, Pair<FloatArray, Long>>()

    override fun analyze(image: ImageProxy) {
        try {
            val start = SystemClock.elapsedRealtime()
            if (start - lastRun < intervalMs) return
            lastRun = start

            val frame = upright(image)
            lastFrame = frame
            frameNo++

            if (frameNo % 2 == 1) lastLines = runCatching { ocr.readBoxedLinesBlocking(frame) }.getOrDefault(emptyList())
            val found = runCatching { finder.detectInStream(frame) }.getOrDefault(emptyList())
                .sortedByDescending { it.box.width() * it.box.height() }
                .take(MAX_OBJECTS)
            val regions = found.ifEmpty { listOf(FoundObject(centerBox(frame), FALLBACK_KEY)) }

            val library = parts()
            val keys = regions.mapIndexed { i, obj -> obj.trackId ?: (UNTRACKED_KEY_BASE - i) }
            refreshEmbeddings(frame, regions, keys, start)
            val objects = regions.mapIndexed { i, obj ->
                val key = keys[i]
                val texts = lastLines.filter { line -> line.box?.let { obj.box.contains(it.centerX(), it.centerY()) } ?: false }
                    .map { it.text }
                val query = embeddings[key]?.first?.takeIf { it.isNotEmpty() }
                val ranked = PartMatcher.rank(library, listOfNotNull(query), texts, limit = MAX_CANDIDATES)
                DetectedPart(
                    key = key,
                    box = obj.box,
                    candidates = smooth(key, ranked),
                    readNumber = OcrHelper.partNumberCandidates(texts).maxByOrNull { it.length },
                    isFallback = found.isEmpty(),
                )
            }
            smoothed.keys.retainAll(keys.toSet())
            embeddings.keys.retainAll(keys.toSet())

            onResult(
                LiveFrame(
                    frame = frame,
                    objects = objects,
                    frameMs = SystemClock.elapsedRealtime() - start,
                    frameNo = frameNo,
                    problem = if (embedder.isAvailable) null else "外观识别模型加载失败，只能识别零件上的文字",
                )
            )
        } catch (t: Throwable) {
            // Throwable so that native-library errors show up on screen instead of silently stopping analysis.
            Log.w(TAG, "Frame analysis failed", t)
            lastFrame?.let { onResult(LiveFrame(it, emptyList(), 0, frameNo, "识别出错：${t.message ?: t.javaClass.simpleName}")) }
        } finally {
            image.close()
        }
    }

    /** New objects first, then the stalest; at most [MAX_EMBEDS_PER_FRAME] model runs per frame. */
    private fun refreshEmbeddings(frame: Bitmap, regions: List<FoundObject>, keys: List<Int>, now: Long) {
        regions.indices
            .filter { i -> embeddings[keys[i]]?.let { now - it.second > REFRESH_MS } ?: true }
            .sortedBy { i -> embeddings[keys[i]]?.second ?: Long.MIN_VALUE }
            .take(MAX_EMBEDS_PER_FRAME)
            .forEach { i -> embeddings[keys[i]] = embedder.embed(ObjectFinder.crop(frame, regions[i].box)) to now }
    }

    private fun smooth(key: Int, ranked: List<MatchResult>): List<LiveCandidate> {
        val scores = smoothed.getOrPut(key) { HashMap() }
        val seen = HashSet<String>()
        val result = ranked.map { m ->
            seen += m.part.id
            val prev = scores[m.part.id] ?: m.imageScore
            val s = prev + SMOOTHING * (m.imageScore - prev)
            scores[m.part.id] = s
            LiveCandidate(m, if (m.isTextHit) maxOf(s, m.textScore) else s)
        }
        scores.keys.retainAll(seen)
        return result.sortedWith(compareByDescending<LiveCandidate> { it.match.isTextHit }.thenByDescending { it.smoothedScore })
    }

    private fun upright(image: ImageProxy): Bitmap {
        val bitmap = image.toBitmap()
        val rotation = image.imageInfo.rotationDegrees
        if (rotation == 0) return bitmap
        val m = Matrix().apply { postRotate(rotation.toFloat()) }
        return Bitmap.createBitmap(bitmap, 0, 0, bitmap.width, bitmap.height, m, true)
    }

    private fun centerBox(frame: Bitmap): Rect {
        val side = (minOf(frame.width, frame.height) * 0.6f).toInt()
        val l = (frame.width - side) / 2
        val t = (frame.height - side) / 2
        return Rect(l, t, l + side, t + side)
    }

    companion object {
        private const val TAG = "LiveScanner"
        private const val SMOOTHING = 0.5f
        private const val MAX_OBJECTS = 5
        private const val MAX_CANDIDATES = 4
        const val FALLBACK_KEY = -1
        private const val UNTRACKED_KEY_BASE = -100
        private const val MAX_EMBEDS_PER_FRAME = 2
        private const val REFRESH_MS = 500L
        // Raw DINOv2 cosine thresholds (see Calibration): ≈30% / ≈88% displayed confidence.
        const val MAYBE_SCORE = 0.31f
        const val CONFIDENT_SCORE = 0.42f
        const val CONFIDENT_MARGIN = 0.05f
    }
}
