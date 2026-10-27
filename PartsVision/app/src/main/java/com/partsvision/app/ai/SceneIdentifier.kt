package com.partsvision.app.ai

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Rect
import com.partsvision.app.data.Part
import com.partsvision.app.ml.ImageEmbedderHelper
import com.partsvision.app.ml.ObjectFinder
import com.partsvision.app.ml.OcrHelper
import com.partsvision.app.ml.PILE_SIZE
import com.partsvision.app.ml.PartMatcher
import com.partsvision.app.ml.PileDetection
import com.partsvision.app.ml.PileResult
import com.partsvision.app.util.ImageUtils
import org.json.JSONObject

/**
 * The strong path for hard scenes: on-device FastSAM numbers the candidate regions, and Claude —
 * which can compare details like "threaded stud vs push-in port" against the reference photos —
 * groups regions into whole parts and names each one (set-of-marks prompting). This fixes both
 * on-device weaknesses at once: one part split into several boxes, and look-alike parts.
 * Takes a few seconds and needs network access to the Claude API.
 */
class SceneIdentifier(private val embedder: ImageEmbedderHelper, private val finder: ObjectFinder) {

    fun identify(frame: Bitmap, library: List<Part>, claude: ClaudeService): PileResult {
        val start = System.currentTimeMillis()
        val image = ImageUtils.scaleDown(frame, MAX_SIDE)
        val set = finder.propose(image, minScore = 0.3f, nmsIou = 0.5f, maxCount = MAX_MARKS, maxArea = 0.6f, size = PILE_SIZE)
        val marks = set.proposals.map { it.box }

        val references = shortlist(image, set.proposals.map { finder.maskedCrop(image, set, it) }, library).map { part ->
            val photo = part.photos.firstOrNull()?.let { BitmapFactory.decodeFile(it.path) }
            ReferencePart(part.partNumber, part.name, photo?.let { ImageUtils.toBase64Jpeg(ImageUtils.scaleDown(it, 448), 85) })
        }

        val raw = claude.identifyScene(
            ImageUtils.toBase64Jpeg(image, 90),
            ImageUtils.toBase64Jpeg(drawMarks(image, marks), 90),
            marks.size,
            references,
        )
        val json = JSONObject(raw.substring(raw.indexOf('{'), raw.lastIndexOf('}') + 1))

        val detections = ArrayList<PileDetection>()
        val unknown = ArrayList<Pair<Rect, String>>()
        val items = json.optJSONArray("items")
        for (i in 0 until (items?.length() ?: 0)) {
            val item = items!!.getJSONObject(i)
            val ids = item.optJSONArray("marks") ?: continue
            val box = Rect()
            for (k in 0 until ids.length()) marks.getOrNull(ids.optInt(k) - 1)?.let { box.union(it) }
            if (box.isEmpty) continue
            val number = item.optString("part_number").trim()
            val confidence = item.optInt("confidence")
            val part = library.firstOrNull { OcrHelper.normalize(it.partNumber) == OcrHelper.normalize(number) && number.isNotEmpty() }
            if (part != null) {
                detections += PileDetection(box, part, 0f, confidence >= CONFIDENT, aiConfidence = confidence)
            } else {
                unknown += box to item.optString("reason").ifBlank { "不在零件库中" }
            }
        }
        // Boxes refer to the scaled image; map back to the frame.
        val s = frame.width.toFloat() / image.width
        fun Rect.toFrame() = Rect((left * s).toInt(), (top * s).toInt(), (right * s).toInt(), (bottom * s).toInt())
        return PileResult(
            frame,
            detections.map { PileDetection(it.box.toFrame(), it.part, it.score, it.confident, it.aiConfidence) },
            marks.size,
            System.currentTimeMillis() - start,
            unknown = unknown.map { (b, why) -> b.toFrame() to why },
            summary = json.optString("summary").ifBlank { null },
            byAi = true,
        )
    }

    /** With a big library, send only parts that look like something in the scene. */
    private fun shortlist(image: Bitmap, crops: List<Bitmap>, library: List<Part>): List<Part> {
        if (library.size <= MAX_REFERENCES) return library
        val votes = HashMap<String, Float>()
        crops.take(20).forEach { crop ->
            val e = embedder.embed(crop)
            if (e.isEmpty()) return@forEach
            PartMatcher.rank(library, listOf(e), emptyList(), limit = 3).forEach { m ->
                votes[m.part.id] = maxOf(votes[m.part.id] ?: 0f, m.imageScore)
            }
        }
        val whole = embedder.embed(image)
        if (whole.isNotEmpty()) PartMatcher.rank(library, listOf(whole), emptyList(), limit = 5).forEach { m ->
            votes[m.part.id] = maxOf(votes[m.part.id] ?: 0f, m.imageScore)
        }
        val ids = votes.entries.sortedByDescending { it.value }.take(MAX_REFERENCES).map { it.key }.toSet()
        return library.filter { it.id in ids }
    }

    /** Thin outlines plus a numbered tag in each box's top-left corner. */
    private fun drawMarks(image: Bitmap, marks: List<Rect>): Bitmap {
        val out = image.copy(Bitmap.Config.ARGB_8888, true)
        val canvas = Canvas(out)
        val scale = image.width / 720f
        val line = Paint().apply { style = Paint.Style.STROKE; strokeWidth = 2f * scale; isAntiAlias = true }
        val tag = Paint().apply { style = Paint.Style.FILL }
        val text = Paint().apply { color = Color.WHITE; textSize = 18f * scale; isAntiAlias = true; isFakeBoldText = true }
        marks.forEachIndexed { i, r ->
            val c = COLORS[i % COLORS.size]
            line.color = c; tag.color = c
            canvas.drawRect(r, line)
            val label = "${i + 1}"
            val w = text.measureText(label) + 6f * scale
            val h = text.textSize + 4f * scale
            canvas.drawRect(r.left.toFloat(), r.top.toFloat(), r.left + w, r.top + h, tag)
            canvas.drawText(label, r.left + 3f * scale, r.top + text.textSize, text)
        }
        return out
    }

    companion object {
        private const val MAX_SIDE = 1280
        private const val MAX_MARKS = 30
        private const val MAX_REFERENCES = 15
        private const val CONFIDENT = 70
        private val COLORS = intArrayOf(
            0xFFE53935.toInt(), 0xFF1E88E5.toInt(), 0xFF43A047.toInt(), 0xFFFB8C00.toInt(),
            0xFF8E24AA.toInt(), 0xFF00ACC1.toInt(), 0xFFFDD835.toInt(), 0xFF6D4C41.toInt(),
        )
    }
}
