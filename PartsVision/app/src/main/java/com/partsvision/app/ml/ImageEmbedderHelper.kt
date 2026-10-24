package com.partsvision.app.ml

import android.content.Context
import android.graphics.Bitmap
import android.util.Log
import com.google.mediapipe.framework.image.BitmapImageBuilder
import com.google.mediapipe.tasks.core.BaseOptions
import com.google.mediapipe.tasks.vision.core.RunningMode
import com.google.mediapipe.tasks.vision.imageembedder.ImageEmbedder
import kotlin.math.sqrt

/**
 * On-device image feature extractor (MobileNetV3-Large via MediaPipe). Photos of the same part
 * produce nearby vectors, so a cosine-similarity search over the library finds matches offline.
 *
 * Each image is embedded as several crops (whole frame + centre) because a part held in the
 * hand often fills only the middle of the frame; comparing crop pairs ignores more background.
 */
class ImageEmbedderHelper(context: Context) {
    private val embedder: ImageEmbedder? = try {
        val options = ImageEmbedder.ImageEmbedderOptions.builder()
            .setBaseOptions(BaseOptions.builder().setModelAssetPath(MODEL_ASSET).build())
            .setRunningMode(RunningMode.IMAGE)
            .setL2Normalize(true)
            .setQuantize(false)
            .build()
        ImageEmbedder.createFromOptions(context, options)
    } catch (e: Exception) {
        Log.e(TAG, "Image embedder unavailable", e)
        null
    }

    val isAvailable: Boolean get() = embedder != null

    /** Embeddings of the whole image and of its centre, in that order. */
    fun embedCrops(bitmap: Bitmap): List<FloatArray> =
        listOf(bitmap, centerCrop(bitmap, CENTER_FRACTION)).map(::embed).filter { it.isNotEmpty() }

    @Synchronized
    fun embed(bitmap: Bitmap): FloatArray {
        val e = embedder ?: return FloatArray(0)
        val argb = if (bitmap.config == Bitmap.Config.ARGB_8888) bitmap else bitmap.copy(Bitmap.Config.ARGB_8888, false)
        val result = e.embed(BitmapImageBuilder(argb).build())
        return result.embeddingResult().embeddings().firstOrNull()?.floatEmbedding() ?: FloatArray(0)
    }

    fun close() = embedder?.close()

    companion object {
        private const val TAG = "ImageEmbedder"
        private const val MODEL_ASSET = "mobilenet_v3_large.tflite"

        /** Bump when the model or cropping changes so stored vectors get recomputed. */
        const val VERSION = 2
        private const val CENTER_FRACTION = 0.6f

        fun centerCrop(bitmap: Bitmap, fraction: Float): Bitmap {
            val side = (minOf(bitmap.width, bitmap.height) * fraction).toInt().coerceAtLeast(1)
            return Bitmap.createBitmap(bitmap, (bitmap.width - side) / 2, (bitmap.height - side) / 2, side, side)
        }

        /** Best similarity over all crop pairs. */
        fun bestCosine(a: List<FloatArray>, b: List<FloatArray>): Float {
            var best = 0f
            for (x in a) for (y in b) best = maxOf(best, cosine(x, y))
            return best
        }

        fun cosine(a: FloatArray, b: FloatArray): Float {
            if (a.isEmpty() || a.size != b.size) return 0f
            var dot = 0f; var na = 0f; var nb = 0f
            for (i in a.indices) { dot += a[i] * b[i]; na += a[i] * a[i]; nb += b[i] * b[i] }
            return if (na == 0f || nb == 0f) 0f else dot / (sqrt(na) * sqrt(nb))
        }
    }
}
