package com.partsvision.app.ml

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.RectF
import android.util.Log
import java.nio.FloatBuffer
import kotlin.math.sqrt

/**
 * On-device image feature extractor: DINOv2-small (self-supervised ViT, int8 ONNX).
 *
 * DINOv2 features describe the object itself — shape, parts, material — rather than the
 * ImageNet category or the scene, so one reference photo still matches the same part on a
 * different background or under different light. On a synthetic "new environment" test built
 * from a real part photo, same-part vs other-object accuracy was 95% (MobileNetV3: 56%).
 * See tools/export_dinov2.py for how the model is produced.
 */
class ImageEmbedderHelper(context: Context) {
    private val env: OrtEnvironment? = runCatching { OrtEnvironment.getEnvironment() }.getOrNull()

    /** Why the model could not be loaded, for the on-screen message. */
    var loadError: String? = null
        private set

    private val session: OrtSession? = try {
        val bytes = context.assets.open(MODEL_ASSET).use { it.readBytes() }
        val options = OrtSession.SessionOptions().apply {
            setOptimizationLevel(OrtSession.SessionOptions.OptLevel.ALL_OPT)
            setIntraOpNumThreads(4)
        }
        env?.createSession(bytes, options)
    } catch (t: Throwable) {
        // Throwable, not Exception: a missing native library surfaces as an Error.
        Log.e(TAG, "Image embedder unavailable", t)
        loadError = t.message ?: t.javaClass.simpleName
        null
    }

    val isAvailable: Boolean get() = session != null

    private val input = FloatBuffer.allocate(3 * SIZE * SIZE)
    private val pixels = IntArray(SIZE * SIZE)
    private val square = Bitmap.createBitmap(SIZE, SIZE, Bitmap.Config.ARGB_8888)
    private val paint = Paint(Paint.FILTER_BITMAP_FLAG)

    /** Overall fingerprint plus region features of one image. */
    class Features(val embedding: FloatArray, val regions: Regions)

    /** What the library stores for one reference photo. */
    class PhotoFeatures(val embeddings: List<FloatArray>, val regions: List<Regions>)

    /**
     * Library-side features of a reference photo: the part cut out of its background when it
     * could be found ([cutouts]), otherwise the whole photo. The whole photo is deliberately not
     * kept alongside a cut-out — it is mostly table/tray and would then "match" background.
     * Region features are stored in four orientations, because patch features are not
     * rotation-invariant and a part can lie any way round.
     */
    fun embedPhoto(bitmap: Bitmap, cutouts: List<Bitmap>): PhotoFeatures {
        val views = cutouts.ifEmpty { listOf(bitmap) }
        val embeddings = views.map(::embed).filter { it.isNotEmpty() }
        val main = views.first()
        val regions = listOf(0f, 90f, 180f, 270f).mapNotNull { angle ->
            val rotated = if (angle == 0f) main else Bitmap.createBitmap(
                main, 0, 0, main.width, main.height, android.graphics.Matrix().apply { postRotate(angle) }, true,
            )
            features(rotated)?.regions
        }
        return PhotoFeatures(embeddings, regions)
    }

    /** Fingerprint and region features in one model run, or null if the model is unavailable. */
    @Synchronized
    fun features(bitmap: Bitmap): Features? {
        val (raw, patches) = run(bitmap) ?: return null
        // Regions first: they read this run's letterboxed pixels, which removeGrey's first call would overwrite.
        val regions = regionsOnPart(patches)
        return Features(removeGrey(raw), regions)
    }

    /**
     * Embedding of a plain grey image. Cut-outs are padded with this grey, and two mostly-grey
     * crops look alike to the model regardless of the part; removing this direction from every
     * embedding stops e.g. a piece of cardboard "matching" a fitting.
     */
    private val greyDirection: FloatArray? by lazy {
        run(Bitmap.createBitmap(SIZE, SIZE, Bitmap.Config.ARGB_8888).apply { eraseColor(PAD_COLOR) })?.first
    }

    /** Unit-length embedding (cosine == dot product), or empty if the model is unavailable. */
    @Synchronized
    fun embed(bitmap: Bitmap): FloatArray = run(bitmap)?.first?.let(::removeGrey) ?: FloatArray(0)

    private fun removeGrey(v: FloatArray): FloatArray {
        val g = greyDirection ?: return v
        var dot = 0f
        for (i in v.indices) dot += v[i] * g[i]
        for (i in v.indices) v[i] -= dot * g[i]
        var norm = 0f
        for (x in v) norm += x * x
        norm = sqrt(norm)
        if (norm > 0f) for (i in v.indices) v[i] /= norm
        return v
    }

    /**
     * Patch tokens of the 16x16 grid that lie on the part: a patch counts when at least 30% of
     * its pixels differ from the grey cut-out/letterbox background. At most [MAX_REGIONS] kept.
     */
    private fun regionsOnPart(patches: Array<FloatArray>): Regions {
        val grid = SIZE / PATCH
        val onPart = ArrayList<FloatArray>()
        for (py in 0 until grid) for (px in 0 until grid) {
            var fg = 0
            for (y in py * PATCH until (py + 1) * PATCH) for (x in px * PATCH until (px + 1) * PATCH) {
                val c = pixels[y * SIZE + x]
                val d = kotlin.math.abs(((c shr 16) and 0xFF) - 124) + kotlin.math.abs(((c shr 8) and 0xFF) - 116) + kotlin.math.abs((c and 0xFF) - 104)
                if (d > 24) fg++
            }
            if (fg > PATCH * PATCH * 0.3f) onPart += patches[py * grid + px]
        }
        val kept = if (onPart.size <= MAX_REGIONS) onPart
        else List(MAX_REGIONS) { i -> onPart[i * onPart.size / MAX_REGIONS] }
        return Regions.quantize(kept)
    }

    /** Runs the model: (unit-length embedding, patch tokens), or null if unavailable. */
    @Synchronized
    private fun run(bitmap: Bitmap): Pair<FloatArray, Array<FloatArray>>? {
        val s = session ?: return null
        letterbox(bitmap)
        square.getPixels(pixels, 0, SIZE, 0, 0, SIZE, SIZE)
        input.clear()
        val plane = SIZE * SIZE
        for (i in 0 until plane) {
            val c = pixels[i]
            input.put(i, ((c shr 16) and 0xFF) / 255f)
            input.put(plane + i, ((c shr 8) and 0xFF) / 255f)
            input.put(2 * plane + i, (c and 0xFF) / 255f)
        }
        OnnxTensor.createTensor(env, input, longArrayOf(1, 3, SIZE.toLong(), SIZE.toLong())).use { tensor ->
            s.run(mapOf(INPUT to tensor)).use { result ->
                @Suppress("UNCHECKED_CAST")
                val v = (result.get(0).value as Array<FloatArray>)[0]
                var norm = 0f
                for (x in v) norm += x * x
                norm = sqrt(norm)
                if (norm > 0f) for (i in v.indices) v[i] /= norm
                @Suppress("UNCHECKED_CAST")
                val patches = (result.get(1).value as Array<Array<FloatArray>>)[0]
                return v to patches
            }
        }
    }

    /** Fits [bitmap] inside a grey square without distorting it, as during model evaluation. */
    private fun letterbox(bitmap: Bitmap) {
        // Halve first so the final bilinear step averages pixels instead of skipping them (avoids aliasing).
        var src = bitmap
        while (maxOf(src.width, src.height) >= 2 * SIZE) {
            src = Bitmap.createScaledBitmap(src, src.width / 2, src.height / 2, true)
        }
        val canvas = Canvas(square)
        canvas.drawColor(PAD_COLOR)
        val scale = SIZE.toFloat() / maxOf(src.width, src.height)
        val w = src.width * scale
        val h = src.height * scale
        val left = (SIZE - w) / 2
        val top = (SIZE - h) / 2
        canvas.drawBitmap(src, null, RectF(left, top, left + w, top + h), paint)
    }

    fun close() {
        session?.close()
    }

    companion object {
        private const val TAG = "ImageEmbedder"
        private const val MODEL_ASSET = "dinov2_small_int8.onnx"
        private const val INPUT = "image"
        private const val SIZE = 224
        private const val PAD_COLOR = 0xFF7C7468.toInt() // ImageNet mean (124, 116, 104)

        /** Bump when the model or cropping changes so stored vectors get recomputed. */
        const val VERSION = 7
        private const val PATCH = 14
        private const val MAX_REGIONS = 64

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
