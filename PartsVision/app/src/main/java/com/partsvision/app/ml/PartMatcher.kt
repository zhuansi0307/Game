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
 * Thresholds on DINOv2 cosine similarity and a mapping to an intuitive confidence.
 *
 * Measured on a real pile photo with masked crops: the same part scores ~0.55–0.95, similar-looking
 * but different fittings and dark background patches ~0.40–0.48, unrelated objects < 0.3. Because similar parts sit close, a match
 * is only called confident when it also beats the next library part by [MARGIN].
 */
object Calibration {
    const val MAYBE = 0.46f
    const val CONFIDENT = 0.53f
    const val MARGIN = 0.05f
    private const val MIDPOINT = 0.46f
    private const val SLOPE = 0.05f

    fun confidence(cosine: Float): Float = 1f / (1f + kotlin.math.exp(-(cosine - MIDPOINT) / SLOPE))

    fun isConfident(best: Float, secondBest: Float?): Boolean =
        best >= CONFIDENT && best - (secondBest ?: 0f) >= MARGIN
}

object PartMatcher {

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
