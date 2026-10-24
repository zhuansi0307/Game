package com.partsvision.app.ml

import android.graphics.Bitmap
import android.graphics.Matrix
import android.os.SystemClock
import android.util.Log
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import com.partsvision.app.data.Part

/** A library part with its appearance score smoothed over recent frames. */
data class LiveCandidate(val match: MatchResult, val smoothedScore: Float)

/** What the live camera currently believes it is looking at. */
data class LiveResult(
    /** Best candidates first; empty only when the library is empty. */
    val candidates: List<LiveCandidate>,
    /** Part-number-like text read on the part (shown even when it is not in the library). */
    val readNumber: String?,
    /** The top candidate is a text hit, or clearly ahead on appearance. */
    val confident: Boolean,
    /** Wall time of the last analysis cycle, for the on-screen speed readout. */
    val frameMs: Long,
    /** Set when frames cannot be analyzed (e.g. the embedding model failed to load). */
    val problem: String? = null,
) {
    val top: LiveCandidate? get() = candidates.firstOrNull()

    /** Worth showing as "maybe" even when not confident. */
    val plausible: Boolean get() = top?.let { it.match.isTextHit || it.smoothedScore >= LiveScanner.MAYBE_SCORE } == true
}

/**
 * CameraX analyzer that recognizes parts continuously and reports after every frame it
 * processes, so the overlay always shows the current best guess. Appearance scores are
 * smoothed per part across frames (EMA) to stop the top answer flickering, and OCR — the
 * slow step — runs on every other frame while the embedding runs on all of them.
 */
class LiveScanner(
    private val embedder: ImageEmbedderHelper,
    private val ocr: OcrHelper,
    private val parts: () -> List<Part>,
    private val onResult: (LiveResult) -> Unit,
    private val intervalMs: Long = 120,
) : ImageAnalysis.Analyzer {

    @Volatile var lastFrame: Bitmap? = null
        private set

    private var lastRun = 0L
    private var cycle = 0
    private var lastLines: List<String> = emptyList()
    private val smoothed = HashMap<String, Float>()

    override fun analyze(image: ImageProxy) {
        try {
            val start = SystemClock.elapsedRealtime()
            if (start - lastRun < intervalMs) return
            lastRun = start

            val frame = upright(image)
            lastFrame = frame

            if (cycle++ % 2 == 0) lastLines = runCatching { ocr.readLinesBlocking(frame) }.getOrDefault(emptyList())
            val embeddings = embedder.embedCrops(frame)
            val library = parts()
            val ranked = PartMatcher.rank(library, embeddings, lastLines, limit = library.size)

            val seen = HashSet<String>()
            val candidates = ranked.map { m ->
                seen += m.part.id
                val prev = smoothed[m.part.id] ?: m.imageScore
                val s = prev + SMOOTHING * (m.imageScore - prev)
                smoothed[m.part.id] = s
                LiveCandidate(m, if (m.isTextHit) maxOf(s, m.textScore) else s)
            }.sortedWith(compareByDescending<LiveCandidate> { it.match.isTextHit }.thenByDescending { it.smoothedScore })
            smoothed.keys.retainAll(seen)

            val top = candidates.getOrNull(0)
            val second = candidates.getOrNull(1)?.smoothedScore ?: 0f
            val confident = top != null && (top.match.isTextHit ||
                (top.smoothedScore >= CONFIDENT_SCORE && top.smoothedScore - second >= CONFIDENT_MARGIN))

            onResult(
                LiveResult(
                    candidates = candidates.take(3),
                    readNumber = OcrHelper.partNumberCandidates(lastLines).maxByOrNull { it.length },
                    confident = confident,
                    frameMs = SystemClock.elapsedRealtime() - start,
                    problem = if (embedder.isAvailable) null else "外观识别模型加载失败，只能识别零件上的文字",
                )
            )
        } catch (e: Exception) {
            Log.w(TAG, "Frame analysis failed", e)
            onResult(LiveResult(emptyList(), null, false, 0, "识别出错：${e.message}"))
        } finally {
            image.close()
        }
    }

    private fun upright(image: ImageProxy): Bitmap {
        val bitmap = image.toBitmap()
        val rotation = image.imageInfo.rotationDegrees
        if (rotation == 0) return bitmap
        val m = Matrix().apply { postRotate(rotation.toFloat()) }
        return Bitmap.createBitmap(bitmap, 0, 0, bitmap.width, bitmap.height, m, true)
    }

    companion object {
        private const val TAG = "LiveScanner"
        private const val SMOOTHING = 0.5f
        const val MAYBE_SCORE = 0.55f
        const val CONFIDENT_SCORE = 0.70f
        const val CONFIDENT_MARGIN = 0.04f
    }
}
