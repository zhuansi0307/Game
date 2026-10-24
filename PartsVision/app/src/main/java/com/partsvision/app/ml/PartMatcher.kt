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
    /** A confident text hit outranks appearance alone; otherwise rank by appearance. */
    val score: Float get() = if (textScore >= TEXT_HIT) maxOf(textScore, imageScore) else imageScore

    val isTextHit: Boolean get() = textScore >= TEXT_HIT

    companion object {
        const val TEXT_HIT = 0.8f
    }
}

object PartMatcher {

    fun rank(
        parts: List<Part>,
        queryEmbedding: FloatArray,
        ocrLines: List<String>,
        limit: Int = 8,
    ): List<MatchResult> {
        val tokens = OcrHelper.partNumberCandidates(ocrLines)
        return parts.map { part ->
            val image = part.photos.maxOfOrNull { ImageEmbedderHelper.cosine(queryEmbedding, it.embedding) } ?: 0f
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
