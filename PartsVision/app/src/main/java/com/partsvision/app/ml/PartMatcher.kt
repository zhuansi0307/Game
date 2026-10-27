package com.partsvision.app.ml

import com.partsvision.app.data.Part

data class MatchResult(
    val part: Part,
    /** Best cosine similarity between the query photo and any of the part's photos. */
    val imageScore: Float,
    /** Best fuzzy match between text read on the photo and the part number. */
    val textScore: Float,
    val matchedText: String?,
) {
    /** Appearance similarity mapped to a 0..1 "how sure" value, see [Calibration]. */
    val imageConfidence: Float get() = Calibration.confidence(imageScore)

    /** A confident text hit outranks appearance alone; otherwise rank by appearance. */
    val score: Float get() = if (textScore >= TEXT_HIT) maxOf(textScore, imageConfidence) else imageConfidence

    val isTextHit: Boolean get() = textScore >= TEXT_HIT

    companion object {
        const val TEXT_HIT = 0.8f
    }
}

/**
 * Thresholds on DINOv2 cosine similarity (cut-outs, grey direction removed) and a mapping to a
 * displayed confidence.
 *
 * Measured across three real photos: a different fitting family (elbow vs tee) scores
 * 0.62–0.68; the same model photographed elsewhere ~0.87; but two *different* tee models that
 * differ only in one end score 0.90 — overall similarity cannot separate those. So:
 *  - below [MAYBE] nothing is claimed (an elbow is not called a tee — it reached 0.72 against
 *    a tee reference in a real scene);
 *  - look-alike models are only told apart when both are in the library and one wins by
 *    [MARGIN] (or by region comparison, see PartMatcher.regionScores);
 *  - the displayed percentage reaches ~90% only around 0.80, not at 0.65 as before.
 */
object Calibration {
    const val MAYBE = 0.75f
    const val CONFIDENT = 0.80f
    const val MARGIN = 0.04f
    private const val MIDPOINT = 0.76f
    private const val SLOPE = 0.035f

    fun confidence(cosine: Float): Float = 1f / (1f + kotlin.math.exp(-(cosine - MIDPOINT) / SLOPE))

    fun isConfident(best: Float, secondBest: Float?): Boolean =
        best >= CONFIDENT && best - (secondBest ?: 0f) >= MARGIN

    /** Library parts within this overall-similarity window of the best are compared region by region. */
    const val RERANK_WINDOW = 0.10f
    /** Region-score lead needed to call one of two look-alike parts confidently. */
    const val REGION_MARGIN = 0.03f
}

object PartMatcher {

    /**
     * For library parts that are about as similar overall as the best one, how well they match
     * region by region (see [Regions]); empty when there is no close contender, since then the
     * overall similarity already decides.
     */
    fun regionScores(query: Regions?, ranked: List<MatchResult>): Map<String, Float> {
        if (query == null || query.count == 0) return emptyMap()
        val best = ranked.maxOfOrNull { it.imageScore } ?: return emptyMap()
        val close = ranked
            .filter { best - it.imageScore <= Calibration.RERANK_WINDOW && it.imageScore >= Calibration.MAYBE - 0.08f }
            .sortedByDescending { it.imageScore }
            .take(4)
        if (close.size < 2) return emptyMap()
        return close.associate { m -> m.part.id to (m.part.photos.maxOfOrNull { Regions.score(query, it.regions) } ?: 0f) }
    }

    fun rank(
        parts: List<Part>,
        queryEmbeddings: List<FloatArray>,
        ocrLines: List<String>,
        limit: Int = 8,
    ): List<MatchResult> {
        val tokens = OcrHelper.partNumberCandidates(ocrLines)
        return parts.map { part ->
            val image = part.photos.maxOfOrNull { ImageEmbedderHelper.bestCosine(queryEmbeddings, it.embeddings) } ?: 0f
            var bestText = 0f
            var bestToken: String? = null
            for (token in tokens) {
                val s = OcrHelper.similarity(token, part.partNumber)
                if (s > bestText) { bestText = s; bestToken = token }
            }
            MatchResult(part, image.coerceAtLeast(0f), bestText, bestToken)
        }
            .filter { it.score > 0f }
            .sortedByDescending { it.score }
            .take(limit)
    }
}
