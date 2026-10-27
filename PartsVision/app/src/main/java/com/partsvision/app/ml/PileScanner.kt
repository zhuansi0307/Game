package com.partsvision.app.ml

import android.graphics.Bitmap
import android.graphics.Rect
import com.partsvision.app.data.Part

/** One part found in a pile. */
class PileDetection(
    val box: Rect, val part: Part, val score: Float, val confident: Boolean,
    /** The cloud model's own confidence (0–100) when it made the call. */
    val aiConfidence: Int? = null,
) {
    val confidence: Float get() = aiConfidence?.let { it / 100f } ?: Calibration.confidence(score)
}

class PileResult(
    val frame: Bitmap,
    val detections: List<PileDetection>,
    val proposalCount: Int,
    val millis: Long,
    /** Parts found but not in the library, with what they look like (cloud identification only). */
    val unknown: List<Pair<Rect, String>> = emptyList(),
    val summary: String? = null,
    val byAi: Boolean = false,
) {
    /** Part number → how many were found, most frequent first. */
    val counts: List<Pair<Part, Int>> get() =
        detections.groupBy { it.part.id }.map { (_, d) -> d.first().part to d.size }.sortedByDescending { it.second }
}

/**
 * Thorough one-shot detection for a still frame of many touching parts (the CNOS recipe):
 *  1. YOLOE + FastSAM propose many overlapping candidates at every granularity (whole part, cap, nut…);
 *  2. each is cut out with its mask and embedded with DINOv2, then scored against every
 *     library part;
 *  3. neighbouring candidates that each only partly match are also tried merged, because in a
 *     pile the detector often sees only the pieces of a complex fitting;
 *  4. the best-scoring candidates are kept greedily, skipping any that mostly overlap one
 *     already kept.
 * Takes roughly 5–15 seconds on a phone, so it runs on demand rather than on every camera frame.
 */
class PileScanner(private val embedder: ImageEmbedderHelper, private val finder: ObjectFinder) {

    private class Candidate(
        val proposal: Proposal, val part: Part?, val best: Float, val second: Float,
        /** Set when look-alike parts were separated region by region. */
        val regionLead: Float? = null,
    ) {
        val confident: Boolean get() = if (regionLead != null) best >= Calibration.CONFIDENT && regionLead >= Calibration.REGION_MARGIN
        else Calibration.isConfident(best, second)
    }

    fun scan(frame: Bitmap, library: List<Part>, onProgress: (Float) -> Unit): PileResult {
        val start = System.currentTimeMillis()
        val set = finder.propose(frame, minScore = 0.15f, nmsIou = 0.65f, maxCount = MAX_PROPOSALS, maxArea = 0.12f)
        val singles = set.proposals
        val total = singles.size + MAX_MERGES
        var done = 0

        fun score(p: Proposal): Candidate {
            val f = embedder.features(finder.maskedCrop(frame, set, p))
            onProgress((++done).toFloat() / total)
            val e = f?.embedding ?: FloatArray(0)
            val ranked = PartMatcher.rank(library, listOf(e), emptyList(), limit = 4).sortedByDescending { it.imageScore }
            val top = ranked.getOrNull(0) ?: return Candidate(p, null, 0f, 0f)
            val second = ranked.getOrNull(1)?.imageScore ?: 0f
            // Look-alikes: let the region-by-region comparison pick between them.
            val regions = PartMatcher.regionScores(f?.regions, ranked)
            if (regions.size >= 2) {
                val byRegion = regions.entries.sortedByDescending { it.value }
                val winner = ranked.first { it.part.id == byRegion[0].key }
                return Candidate(p, winner.part, winner.imageScore, second, byRegion[0].value - byRegion[1].value)
            }
            return Candidate(p, top.part, top.imageScore, second)
        }

        val scored = singles.map(::score).toMutableList()

        // Merge pass: pairs of touching candidates that are each only a partial match.
        val frameArea = frame.width.toFloat() * frame.height
        val merges = ArrayList<Pair<Proposal, Float>>()
        for (i in scored.indices) for (j in i + 1 until scored.size) {
            val a = scored[i]; val b = scored[j]
            if (a.best >= Calibration.CONFIDENT && b.best >= Calibration.CONFIDENT) continue
            if (!touching(a.proposal.box, b.proposal.box)) continue
            val u = a.proposal.union(b.proposal)
            if (u.area > 3 * maxOf(a.proposal.area, b.proposal.area) || u.area > frameArea * 0.12f) continue
            merges += u to (a.best + b.best)
        }
        merges.sortedByDescending { it.second }.take(MAX_MERGES).forEach { (u, _) -> scored += score(u) }
        onProgress(1f)

        val kept = ArrayList<Candidate>()
        for (c in scored.sortedByDescending { it.best }) {
            if (c.part == null || c.best < Calibration.MAYBE) break
            if (kept.none { ObjectFinder.overlapMin(it.proposal.box, c.proposal.box) > 0.5f }) kept += c
        }
        return PileResult(
            frame,
            kept.map { PileDetection(it.proposal.box, it.part!!, it.best, it.confident) },
            singles.size,
            System.currentTimeMillis() - start,
        )
    }

    /** Overlapping, or separated by a gap smaller than 10% of the smaller box. */
    private fun touching(a: Rect, b: Rect): Boolean {
        val gap = (minOf(minOf(a.width(), a.height()), minOf(b.width(), b.height())) * 0.1f).toInt()
        return Rect(a).apply { inset(-gap, -gap) }.intersect(b)
    }

    companion object {
        private const val MAX_PROPOSALS = 60
        private const val MAX_MERGES = 25
    }
}
