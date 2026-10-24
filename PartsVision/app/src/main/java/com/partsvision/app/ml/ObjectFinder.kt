package com.partsvision.app.ml

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.Rect
import android.graphics.RectF
import android.util.Log
import java.nio.FloatBuffer
import kotlin.math.max
import kotlin.math.min

/**
 * One candidate object: a box in bitmap pixels plus the mask coefficients of every segment it
 * was built from (more than one when neighbouring segments were merged into a single part).
 */
class Proposal(val box: Rect, val score: Float, val coefs: List<FloatArray>) {
    val area: Int get() = box.width() * box.height()

    /** Merge with [other]: union box, union mask. */
    fun union(other: Proposal) = Proposal(
        Rect(box).apply { union(other.box) }, min(score, other.score), coefs + other.coefs,
    )
}

/** Proposals for one image plus what is needed to rebuild their masks. */
class ProposalSet(
    val proposals: List<Proposal>,
    internal val protos: FloatArray,
    internal val scale: Float,
    internal val dx: Float,
    internal val dy: Float,
)

/**
 * Class-agnostic object proposer: FastSAM-s ("segment anything", YOLOv8-seg architecture,
 * ONNX). Unlike detectors trained on fixed categories, it outlines every individual item —
 * including touching parts in a pile — and gives each a mask, so a part can be cut out of its
 * surroundings before matching (the CNOS recipe for one-shot detection of new objects).
 * See tools/export_fastsam.py.
 */
class ObjectFinder(context: Context) {
    private val env: OrtEnvironment? = runCatching { OrtEnvironment.getEnvironment() }.getOrNull()
    private val session: OrtSession? = try {
        val bytes = context.assets.open(MODEL_ASSET).use { it.readBytes() }
        env?.createSession(bytes, sessionOptions())
    } catch (t: Throwable) {
        Log.e(TAG, "Object proposer unavailable", t)
        null
    }

    val isAvailable: Boolean get() = session != null

    private val input = FloatBuffer.allocate(3 * SIZE * SIZE)
    private val pixels = IntArray(SIZE * SIZE)
    private val square = Bitmap.createBitmap(SIZE, SIZE, Bitmap.Config.ARGB_8888)
    private val paint = Paint(Paint.FILTER_BITMAP_FLAG)

    /**
     * All objects in [bitmap]. Lower [minScore] and higher [nmsIou] keep more, overlapping,
     * multi-granularity candidates (whole part and its pieces), which is what pile analysis wants.
     */
    @Synchronized
    fun propose(bitmap: Bitmap, minScore: Float, nmsIou: Float, maxCount: Int, minArea: Float = 0.002f, maxArea: Float = 0.4f): ProposalSet {
        val s = session ?: return ProposalSet(emptyList(), FloatArray(0), 1f, 0f, 0f)
        val scale = SIZE.toFloat() / max(bitmap.width, bitmap.height)
        val dx = (SIZE - bitmap.width * scale) / 2
        val dy = (SIZE - bitmap.height * scale) / 2
        letterbox(bitmap, scale, dx, dy)

        OnnxTensor.createTensor(env, input, longArrayOf(1, 3, SIZE.toLong(), SIZE.toLong())).use { tensor ->
            s.run(mapOf(s.inputNames.first() to tensor)).use { result ->
                val out = (result.get(0) as OnnxTensor).floatBuffer
                val protosBuf = (result.get(1) as OnnxTensor).floatBuffer
                val protos = FloatArray(protosBuf.remaining()).also { protosBuf.get(it) }
                val n = out.capacity() / CHANNELS

                val frameArea = bitmap.width.toFloat() * bitmap.height
                val raw = ArrayList<Proposal>()
                for (i in 0 until n) {
                    val score = out.get(4 * n + i)
                    if (score < minScore) continue
                    val cx = out.get(i); val cy = out.get(n + i); val w = out.get(2 * n + i); val h = out.get(3 * n + i)
                    val box = Rect(
                        ((cx - w / 2 - dx) / scale).toInt(), ((cy - h / 2 - dy) / scale).toInt(),
                        ((cx + w / 2 - dx) / scale).toInt(), ((cy + h / 2 - dy) / scale).toInt(),
                    )
                    if (!box.intersect(0, 0, bitmap.width, bitmap.height)) continue
                    val a = box.width().toFloat() * box.height() / frameArea
                    if (a < minArea || a > maxArea) continue
                    raw += Proposal(box, score, listOf(FloatArray(MASK_DIM) { k -> out.get((5 + k) * n + i) }))
                }
                return ProposalSet(nms(raw, nmsIou).take(maxCount), protos, scale, dx, dy)
            }
        }
    }

    /** The most prominent object of a still photo (confident, large, near the centre), or null. */
    fun mainObject(bitmap: Bitmap): Pair<ProposalSet, Proposal>? {
        val set = propose(bitmap, minScore = 0.3f, nmsIou = 0.5f, maxCount = 20, minArea = 0.03f, maxArea = 0.95f)
        val cx = bitmap.width / 2f
        val cy = bitmap.height / 2f
        val diag = kotlin.math.hypot(cx, cy)
        val best = set.proposals.maxByOrNull { p ->
            val d = kotlin.math.hypot(p.box.exactCenterX() - cx, p.box.exactCenterY() - cy) / diag
            p.score * (1f - 0.6f * d) * kotlin.math.sqrt(p.area.toFloat() / (bitmap.width * bitmap.height))
        } ?: return null
        return set to best
    }

    /**
     * [p]'s box cut out of [bitmap] with everything outside its mask replaced by neutral grey,
     * so the embedding describes the part and not what lies around or behind it.
     */
    fun maskedCrop(bitmap: Bitmap, set: ProposalSet, p: Proposal): Bitmap {
        val box = p.box
        if (box.width() < 2 || box.height() < 2 || set.protos.isEmpty()) return ObjectFinder.crop(bitmap, box, 0f)
        // Mask on the 128x128 prototype grid, only for cells under the box.
        val gx0 = cell(box.left * set.scale + set.dx); val gx1 = cell(box.right * set.scale + set.dx)
        val gy0 = cell(box.top * set.scale + set.dy); val gy1 = cell(box.bottom * set.scale + set.dy)
        val gw = gx1 - gx0 + 1
        val grid = BooleanArray(gw * (gy1 - gy0 + 1))
        for (gy in gy0..gy1) for (gx in gx0..gx1) {
            val off = gy * PROTO + gx
            grid[(gy - gy0) * gw + gx - gx0] = p.coefs.any { c ->
                var dot = 0f
                for (k in 0 until MASK_DIM) dot += c[k] * set.protos[k * PROTO * PROTO + off]
                dot > 0f // sigmoid(dot) > 0.5
            }
        }
        val px = IntArray(box.width() * box.height())
        bitmap.getPixels(px, 0, box.width(), box.left, box.top, box.width(), box.height())
        for (y in 0 until box.height()) {
            val gy = cell((box.top + y) * set.scale + set.dy) - gy0
            for (x in 0 until box.width()) {
                val gx = cell((box.left + x) * set.scale + set.dx) - gx0
                if (!grid[gy * gw + gx]) px[y * box.width() + x] = GREY
            }
        }
        return Bitmap.createBitmap(px, box.width(), box.height(), Bitmap.Config.ARGB_8888)
    }

    private fun cell(letterboxCoord: Float) = (letterboxCoord / (SIZE / PROTO)).toInt().coerceIn(0, PROTO - 1)

    private fun letterbox(bitmap: Bitmap, scale: Float, dx: Float, dy: Float) {
        var src = bitmap
        while (max(src.width, src.height) >= 2 * SIZE) {
            src = Bitmap.createScaledBitmap(src, src.width / 2, src.height / 2, true)
        }
        val canvas = Canvas(square)
        canvas.drawColor(PAD)
        canvas.drawBitmap(src, null, RectF(dx, dy, dx + bitmap.width * scale, dy + bitmap.height * scale), paint)
        square.getPixels(pixels, 0, SIZE, 0, 0, SIZE, SIZE)
        input.clear()
        val plane = SIZE * SIZE
        for (i in 0 until plane) {
            val c = pixels[i]
            input.put(i, ((c shr 16) and 0xFF) / 255f)
            input.put(plane + i, ((c shr 8) and 0xFF) / 255f)
            input.put(2 * plane + i, (c and 0xFF) / 255f)
        }
    }

    fun close() {
        session?.close()
    }

    companion object {
        private const val TAG = "ObjectFinder"
        private const val MODEL_ASSET = "fastsam_s_512.onnx"
        private const val SIZE = 512
        private const val PROTO = 128
        private const val MASK_DIM = 32
        private const val CHANNELS = 5 + MASK_DIM
        private const val PAD = 0xFF727272.toInt()
        /** Same neutral grey the embedder pads with. */
        private const val GREY = 0xFF7C7468.toInt()

        private fun sessionOptions() = OrtSession.SessionOptions().apply {
            setOptimizationLevel(OrtSession.SessionOptions.OptLevel.ALL_OPT)
            // XNNPACK runs the convolutions much faster on ARM; fall back to the default CPU kernels if absent.
            val xnnpack = runCatching { addXnnpack(mapOf("intra_op_num_threads" to "4")) }.isSuccess
            setIntraOpNumThreads(if (xnnpack) 1 else 4)
        }

        fun iou(a: Rect, b: Rect): Float {
            val inter = Rect()
            if (!inter.setIntersect(a, b)) return 0f
            val i = inter.width().toFloat() * inter.height()
            return i / (a.width().toFloat() * a.height() + b.width().toFloat() * b.height() - i)
        }

        /** Intersection over the smaller box: 1 when one box sits inside the other. */
        fun overlapMin(a: Rect, b: Rect): Float {
            val inter = Rect()
            if (!inter.setIntersect(a, b)) return 0f
            return inter.width().toFloat() * inter.height() / min(a.width() * a.height(), b.width() * b.height()).coerceAtLeast(1)
        }

        private fun nms(items: List<Proposal>, iouThreshold: Float): List<Proposal> {
            val kept = ArrayList<Proposal>()
            for (p in items.sortedByDescending { it.score }) {
                if (kept.none { iou(it.box, p.box) > iouThreshold }) kept += p
            }
            return kept
        }

        /** [box] grown by [pad] of its size on each side, clipped to the bitmap, then cropped. */
        fun crop(bitmap: Bitmap, box: Rect, pad: Float = 0.1f): Bitmap {
            val dx = (box.width() * pad).toInt()
            val dy = (box.height() * pad).toInt()
            val r = Rect(box.left - dx, box.top - dy, box.right + dx, box.bottom + dy)
            r.intersect(0, 0, bitmap.width, bitmap.height)
            if (r.width() < 2 || r.height() < 2) return bitmap
            return Bitmap.createBitmap(bitmap, r.left, r.top, r.width(), r.height())
        }
    }
}
