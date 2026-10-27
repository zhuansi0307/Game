package com.partsvision.app.ml

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import ai.onnxruntime.providers.NNAPIFlags
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

/** What is needed to turn one model run's mask coefficients into a mask. */
class MaskBasis(
    internal val protos: FloatArray,
    internal val scale: Float,
    internal val dx: Float,
    internal val dy: Float,
    /** Model input side in pixels; the prototype grid is a quarter of it. */
    internal val inputSize: Int,
) {
    internal val protoSize: Int get() = inputSize / 4
}

/**
 * One candidate object: a box in bitmap pixels plus the mask coefficients of every segment it
 * was built from (more than one when neighbouring segments were merged into a single part),
 * each with the model run it came from.
 */
class Proposal(val box: Rect, val score: Float, val masks: List<Pair<FloatArray, MaskBasis>>) {
    val area: Int get() = box.width() * box.height()

    /** Merge with [other]: union box, union mask. */
    fun union(other: Proposal) = Proposal(
        Rect(box).apply { union(other.box) }, min(score, other.score), masks + other.masks,
    )
}

/** Proposals for one image. */
class ProposalSet(val proposals: List<Proposal>)

/** Model input sizes: small and fast for the live camera, larger for piles of small parts. */
const val LIVE_SIZE = 320
const val PILE_SIZE = 512

/**
 * One YOLOv8-seg-layout segmentation model run with ONNX Runtime (box, objectness, 32 mask
 * coefficients per candidate + mask prototypes); see [ObjectFinder] for how they are combined.
 */
internal class SegModel(context: Context, private val asset: String) {
    private val env: OrtEnvironment? = runCatching { OrtEnvironment.getEnvironment() }.getOrNull()
    private val modelBytes: ByteArray? = runCatching { context.assets.open(asset).use { it.readBytes() } }.getOrNull()

    /** CPU session (XNNPACK when available); accepts any input size. */
    private val cpuSession: OrtSession? = try {
        modelBytes?.let { env?.createSession(it, cpuOptions()) }
    } catch (t: Throwable) {
        Log.e(TAG, "$asset unavailable", t)
        null
    }

    val isAvailable: Boolean get() = cpuSession != null

    /** Per input size: the session that ran faster on this phone, and its name for the timing line. */
    private val chosen = HashMap<Int, Pair<OrtSession, String>>()

    /** "GPU/NPU" or "CPU" for the given input size, once chosen. */
    fun backend(size: Int): String = chosen[size]?.second ?: "CPU"

    /**
     * The first time a size is used, also try NNAPI (the phone's GPU / NPU / DSP), time both on
     * a few runs and keep the faster. NNAPI quality differs a lot between phone makers — on
     * some it is several times faster, on others slower than the CPU or missing — so measuring
     * on the device is the only reliable choice. NNAPI needs fixed input sizes, hence one
     * session per size.
     */
    private fun sessionFor(size: Int): OrtSession? {
        chosen[size]?.let { return it.first }
        val cpu = cpuSession ?: return null
        val nnapi = try {
            modelBytes?.let { env?.createSession(it, nnapiOptions(size)) }
        } catch (t: Throwable) {
            Log.w(TAG, "NNAPI unavailable", t)
            null
        }
        val pick = if (nnapi == null) cpu to "CPU" else {
            val cpuMs = timeRuns(cpu, size)
            val nnapiMs = timeRuns(nnapi, size)
            Log.i(TAG, "$asset size $size: CPU ${cpuMs}ms, NNAPI ${nnapiMs}ms")
            if (nnapiMs < cpuMs) nnapi to "GPU/NPU" else { nnapi.close(); cpu to "CPU" }
        }
        chosen[size] = pick
        return pick.first
    }

    private fun timeRuns(session: OrtSession, size: Int): Long = try {
        val zeros = FloatBuffer.allocate(3 * size * size)
        OnnxTensor.createTensor(env, zeros, longArrayOf(1, 3, size.toLong(), size.toLong())).use { t ->
            val input = mapOf(session.inputNames.first() to t)
            session.run(input).close() // warm-up (NNAPI compiles on first run)
            val start = System.nanoTime()
            repeat(3) { session.run(input).close() }
            (System.nanoTime() - start) / 3_000_000
        }
    } catch (t: Throwable) {
        Log.w(TAG, "Benchmark failed", t)
        Long.MAX_VALUE
    }

    /** Reusable input buffers per input size. */
    private class Buffers(size: Int) {
        val input: FloatBuffer = FloatBuffer.allocate(3 * size * size)
        val pixels = IntArray(size * size)
        val square: Bitmap = Bitmap.createBitmap(size, size, Bitmap.Config.ARGB_8888)
    }
    private val buffers = HashMap<Int, Buffers>()
    private val paint = Paint(Paint.FILTER_BITMAP_FLAG)

    /** Candidates above [minScore] with plausible size, before NMS. */
    @Synchronized
    fun candidates(bitmap: Bitmap, minScore: Float, minArea: Float, maxArea: Float, size: Int): List<Proposal> {
        val s = sessionFor(size) ?: return emptyList()
        val scale = size.toFloat() / max(bitmap.width, bitmap.height)
        val dx = (size - bitmap.width * scale) / 2
        val dy = (size - bitmap.height * scale) / 2
        val buf = buffers.getOrPut(size) { Buffers(size) }
        letterbox(bitmap, scale, dx, dy, size, buf)

        OnnxTensor.createTensor(env, buf.input, longArrayOf(1, 3, size.toLong(), size.toLong())).use { tensor ->
            s.run(mapOf(s.inputNames.first() to tensor)).use { result ->
                val out = (result.get(0) as OnnxTensor).floatBuffer
                val protosBuf = (result.get(1) as OnnxTensor).floatBuffer
                val basis = MaskBasis(FloatArray(protosBuf.remaining()).also { protosBuf.get(it) }, scale, dx, dy, size)
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
                    raw += Proposal(box, score, listOf(FloatArray(MASK_DIM) { k -> out.get((5 + k) * n + i) } to basis))
                }
                return raw
            }
        }
    }

    private fun letterbox(bitmap: Bitmap, scale: Float, dx: Float, dy: Float, size: Int, buf: Buffers) {
        var src = bitmap
        while (max(src.width, src.height) >= 2 * size) {
            src = Bitmap.createScaledBitmap(src, src.width / 2, src.height / 2, true)
        }
        val canvas = Canvas(buf.square)
        canvas.drawColor(PAD)
        canvas.drawBitmap(src, null, RectF(dx, dy, dx + bitmap.width * scale, dy + bitmap.height * scale), paint)
        buf.square.getPixels(buf.pixels, 0, size, 0, 0, size, size)
        val input = buf.input
        input.clear()
        val plane = size * size
        for (i in 0 until plane) {
            val c = buf.pixels[i]
            input.put(i, ((c shr 16) and 0xFF) / 255f)
            input.put(plane + i, ((c shr 8) and 0xFF) / 255f)
            input.put(2 * plane + i, (c and 0xFF) / 255f)
        }
    }

    fun close() {
        chosen.values.forEach { (s, _) -> if (s !== cpuSession) s.close() }
        cpuSession?.close()
    }

    private companion object {
        private const val TAG = "SegModel"
        private const val MASK_DIM = 32
        private const val CHANNELS = 5 + MASK_DIM
        private const val PAD = 0xFF727272.toInt()

        private fun nnapiOptions(size: Int) = OrtSession.SessionOptions().apply {
            setOptimizationLevel(OrtSession.SessionOptions.OptLevel.ALL_OPT)
            setSymbolicDimensionValue("batch", 1)
            setSymbolicDimensionValue("height", size.toLong())
            setSymbolicDimensionValue("width", size.toLong())
            // FP16 on the accelerator; anything it cannot run goes to ONNX Runtime's CPU kernels
            // rather than NNAPI's slow reference CPU implementation.
            addNnapi(java.util.EnumSet.of(NNAPIFlags.USE_FP16, NNAPIFlags.CPU_DISABLED))
            setIntraOpNumThreads(4)
        }

        private fun cpuOptions() = OrtSession.SessionOptions().apply {
            setOptimizationLevel(OrtSession.SessionOptions.OptLevel.ALL_OPT)
            // XNNPACK runs the convolutions much faster on ARM; fall back to the default CPU kernels if absent.
            val xnnpack = runCatching { addXnnpack(mapOf("intra_op_num_threads" to "4")) }.isSuccess
            setIntraOpNumThreads(if (xnnpack) 1 else 4)
        }

    }
}

/**
 * Finds the individual objects in an image with two open-source models, because each covers
 * the other's weakness on real part photos:
 *  - YOLOE-11s prompt-free (Ultralytics, trained on ~4.6k object categories) outlines *whole*
 *    objects — on two T fittings it gave exactly two boxes where FastSAM gave 22 pieces;
 *  - FastSAM-s ("segment anything") reaches small items YOLOE skips, e.g. a fitting's red cap
 *    seen from above, and more parts in dense trays.
 * Live view uses YOLOE alone (whole parts, fast); pile scans and library photos use both, and
 * the matcher keeps whichever box matches a library part best. Every candidate carries a mask,
 * so a part can be cut out of its surroundings before matching (the CNOS recipe).
 */
class ObjectFinder(context: Context) {
    private val yoloe = SegModel(context, "yoloe11s_pf.onnx")
    private val fastsam = SegModel(context, "fastsam_s.onnx")

    val isAvailable: Boolean get() = yoloe.isAvailable || fastsam.isAvailable

    /** "GPU/NPU" or "CPU" for the live model. */
    fun backend(size: Int): String = (if (yoloe.isAvailable) yoloe else fastsam).backend(size)

    /**
     * All objects in [bitmap]. Lower [minScore] and higher [nmsIou] keep more, overlapping,
     * multi-granularity candidates (whole part and its pieces), which is what pile analysis wants.
     * [live] uses only the whole-object model.
     */
    fun propose(
        bitmap: Bitmap, minScore: Float, nmsIou: Float, maxCount: Int,
        minArea: Float = 0.002f, maxArea: Float = 0.4f, size: Int = PILE_SIZE, live: Boolean = false,
    ): ProposalSet {
        val models = when {
            live && yoloe.isAvailable -> listOf(yoloe)
            else -> listOf(yoloe, fastsam).filter { it.isAvailable }
        }
        val all = models.flatMap { it.candidates(bitmap, minScore, minArea, maxArea, size) }
        return ProposalSet(nms(all, nmsIou).take(maxCount))
    }

    /** The most prominent object of a still photo (confident, large, near the centre), or null. */
    fun mainObject(bitmap: Bitmap): Pair<ProposalSet, Proposal>? {
        val set = propose(bitmap, minScore = 0.25f, nmsIou = 0.5f, maxCount = 20, minArea = 0.03f, maxArea = 0.95f)
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
    @Suppress("UNUSED_PARAMETER")
    fun maskedCrop(bitmap: Bitmap, set: ProposalSet?, p: Proposal): Bitmap {
        val box = p.box
        if (box.width() < 2 || box.height() < 2 || p.masks.isEmpty()) return crop(bitmap, box, 0f)
        val inside = BooleanArray(box.width() * box.height())
        for ((coef, basis) in p.masks) {
            // Mask on this run's prototype grid (a quarter of its input size), only under the box.
            val proto = basis.protoSize
            fun cell(letterboxCoord: Float) = (letterboxCoord / 4f).toInt().coerceIn(0, proto - 1)
            val gx0 = cell(box.left * basis.scale + basis.dx); val gx1 = cell(box.right * basis.scale + basis.dx)
            val gy0 = cell(box.top * basis.scale + basis.dy); val gy1 = cell(box.bottom * basis.scale + basis.dy)
            val gw = gx1 - gx0 + 1
            val grid = BooleanArray(gw * (gy1 - gy0 + 1))
            for (gy in gy0..gy1) for (gx in gx0..gx1) {
                val off = gy * proto + gx
                var dot = 0f
                for (k in coef.indices) dot += coef[k] * basis.protos[k * proto * proto + off]
                grid[(gy - gy0) * gw + gx - gx0] = dot > 0f // sigmoid(dot) > 0.5
            }
            for (y in 0 until box.height()) {
                val gy = cell((box.top + y) * basis.scale + basis.dy) - gy0
                for (x in 0 until box.width()) {
                    val gx = cell((box.left + x) * basis.scale + basis.dx) - gx0
                    if (grid[gy * gw + gx]) inside[y * box.width() + x] = true
                }
            }
        }
        val px = IntArray(box.width() * box.height())
        bitmap.getPixels(px, 0, box.width(), box.left, box.top, box.width(), box.height())
        for (i in px.indices) if (!inside[i]) px[i] = GREY
        return Bitmap.createBitmap(px, box.width(), box.height(), Bitmap.Config.ARGB_8888)
    }

    fun close() {
        yoloe.close()
        fastsam.close()
    }

    companion object {
        /** Same neutral grey the embedder pads with. */
        private const val GREY = 0xFF7C7468.toInt()

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
