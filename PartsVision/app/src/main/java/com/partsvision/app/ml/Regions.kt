package com.partsvision.app.ml

import java.io.DataInputStream
import java.io.DataOutputStream

/**
 * DINOv2 patch features of the part itself (patches over the grey cut-out background are
 * dropped), one unit vector per 14x14-pixel region, quantized to int8 to keep a library of
 * many photos × 4 orientations small.
 *
 * Used to tell near-identical parts apart: a global embedding averages over the whole part,
 * so a difference confined to one end (a threaded stud instead of a push-in port) is diluted.
 * Comparing region by region and scoring by the *worst-matched* regions makes such a
 * difference count. On two NITTA 12x9 tees differing only in one end, this widened the
 * right-vs-wrong gap from 0.075 to ~0.15 on average and from 0.003 to ~0.04–0.08 in the worst case.
 */
class Regions(val count: Int, val data: ByteArray) {

    fun write(out: DataOutputStream) {
        out.writeInt(count)
        out.write(data)
    }

    companion object {
        const val DIM = 384
        private const val WORST_FRACTION = 0.15f

        fun quantize(vectors: List<FloatArray>): Regions {
            val data = ByteArray(vectors.size * DIM)
            vectors.forEachIndexed { i, v ->
                var norm = 0f
                for (x in v) norm += x * x
                norm = kotlin.math.sqrt(norm).coerceAtLeast(1e-6f)
                for (k in 0 until DIM) data[i * DIM + k] = (v[k] / norm * 127f).toInt().coerceIn(-127, 127).toByte()
            }
            return Regions(vectors.size, data)
        }

        fun read(input: DataInputStream): Regions {
            val n = input.readInt()
            val data = ByteArray(n * DIM)
            input.readFully(data)
            return Regions(n, data)
        }

        /**
         * How well [query] and [ref] cover each other: every region's best match in the other
         * set, then the mean of the worst [WORST_FRACTION] in each direction. A region present
         * in one part but not the other (an extra stud, a missing cap) pulls the score down.
         * Taken over [refs] (the reference photo in several orientations).
         */
        fun score(query: Regions, refs: List<Regions>): Float {
            if (query.count == 0) return 0f
            var best = 0f
            for (ref in refs) {
                if (ref.count == 0) continue
                val rowMax = FloatArray(query.count) { -1f }
                val colMax = FloatArray(ref.count) { -1f }
                for (i in 0 until query.count) {
                    val qi = i * DIM
                    for (j in 0 until ref.count) {
                        val rj = j * DIM
                        var dot = 0
                        for (k in 0 until DIM) dot += query.data[qi + k] * ref.data[rj + k]
                        val s = dot / (127f * 127f)
                        if (s > rowMax[i]) rowMax[i] = s
                        if (s > colMax[j]) colMax[j] = s
                    }
                }
                best = maxOf(best, 0.5f * (worstMean(rowMax) + worstMean(colMax)))
            }
            return best
        }

        private fun worstMean(v: FloatArray): Float {
            v.sort()
            val k = (v.size * WORST_FRACTION).toInt().coerceAtLeast(1)
            var sum = 0f
            for (i in 0 until k) sum += v[i]
            return sum / k
        }
    }
}
