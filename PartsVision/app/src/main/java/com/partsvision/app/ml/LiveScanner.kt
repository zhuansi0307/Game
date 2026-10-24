package com.partsvision.app.ml

import android.graphics.Bitmap
import android.graphics.Matrix
import android.os.SystemClock
import android.util.Log
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import com.partsvision.app.data.Part

/** What the live camera currently believes it is looking at. */
data class LiveResult(
    /** Stable best match, or null when nothing in the library fits well enough. */
    val match: MatchResult?,
    /** Part-number-like text read on the part (shown even when it is not in the library). */
    val readNumber: String?,
    /** True when [match] passes the confident threshold; otherwise it is only a "maybe". */
    val confident: Boolean,
)

/**
 * CameraX analyzer that recognizes parts continuously: every ~[intervalMs] it OCRs and embeds
 * the latest frame, ranks the library, and only reports a match after it wins
 * [STABLE_FRAMES] frames in a row so the overlay does not flicker between candidates.
 */
class LiveScanner(
    private val embedder: ImageEmbedderHelper,
    private val ocr: OcrHelper,
    private val parts: () -> List<Part>,
    private val onResult: (LiveResult) -> Unit,
    private val intervalMs: Long = 350,
) : ImageAnalysis.Analyzer {

    @Volatile var lastFrame: Bitmap? = null
        private set

    private var lastRun = 0L
    private var candidateId: String? = null
    private var streak = 0
    private var misses = 0

    override fun analyze(image: ImageProxy) {
        try {
            val now = SystemClock.elapsedRealtime()
            if (now - lastRun < intervalMs) return
            lastRun = now

            val frame = upright(image)
            lastFrame = frame

            val lines = runCatching { ocr.readLinesBlocking(frame) }.getOrDefault(emptyList())
            val embedding = embedder.embed(frame)
            val top = PartMatcher.rank(parts(), embedding, lines, limit = 1).firstOrNull()
            val readNumber = OcrHelper.partNumberCandidates(lines).maxByOrNull { it.length }

            val good = top != null && (top.isTextHit || top.imageScore >= MAYBE_IMAGE_SCORE)
            if (good) {
                misses = 0
                if (top!!.part.id == candidateId) streak++ else { candidateId = top.part.id; streak = 1 }
                // A text hit is unambiguous, so show it immediately.
                if (top.isTextHit || streak >= STABLE_FRAMES) {
                    onResult(LiveResult(top, readNumber, top.isTextHit || top.imageScore >= CONFIDENT_IMAGE_SCORE))
                }
            } else if (++misses >= STABLE_FRAMES) {
                candidateId = null
                streak = 0
                onResult(LiveResult(null, readNumber, false))
            }
        } catch (e: Exception) {
            Log.w(TAG, "Frame analysis failed", e)
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
        private const val STABLE_FRAMES = 2
        const val MAYBE_IMAGE_SCORE = 0.62f
        const val CONFIDENT_IMAGE_SCORE = 0.75f
    }
}
