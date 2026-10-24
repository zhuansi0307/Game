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
 * Maps DINOv2 cosine similarity to an intuitive confidence. Raw cosine for the same part in a
 * new environment is typically 0.4–0.7 and for unrelated objects below ~0.3, so showing it
 * directly makes a correct match look like "56%". Midpoint and slope come from the synthetic
 * environment-change test (best same/other split at ~0.34).
 */
object Calibration {
    private const val MIDPOINT = 0.34f
    private const val SLOPE = 0.04f

    fun confidence(cosine: Float): Float = 1f / (1f + kotlin.math.exp(-(cosine - MIDPOINT) / SLOPE))
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
