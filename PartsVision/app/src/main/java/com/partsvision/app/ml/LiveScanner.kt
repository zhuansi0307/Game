package com.partsvision.app.ml

import android.graphics.Bitmap
import android.graphics.Matrix
import android.graphics.Rect
import android.os.SystemClock
import android.util.Log
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import com.partsvision.app.data.Part

/** A library part with its appearance similarity (raw cosine) smoothed over recent frames. */
data class LiveCandidate(val match: MatchResult, val smoothedScore: Float) {
    /** 0..1 for display: text hits count fully, appearance goes through [Calibration]. */
    val confidence: Float get() =
        if (match.isTextHit) maxOf(match.textScore, Calibration.confidence(smoothedScore)) else Calibration.confidence(smoothedScore)
}

/** One object found in the frame and what it most likely is. */
data class DetectedPart(
    /** Stable across frames while the object stays in view (tracking id). */
    val key: Int,
    /** Position in [LiveFrame.frame] pixels. */
    val box: Rect,
    /** Best candidates first; empty only when the library is empty or not yet embedded. */
    val candidates: List<LiveCandidate>,
    /** Part-number-like text read inside the box. */
    val readNumber: String?,
    /** No object proposer available, so this is just the centre of the frame. */
    val isFallback: Boolean,
) {
    val top: LiveCandidate? get() = candidates.firstOrNull()

    /** Top candidate is a text hit, or clearly ahead of the runner-up on appearance. */
    val confident: Boolean get() {
        val t = top ?: return false
        return t.match.isTextHit || Calibration.isConfident(t.smoothedScore, candidates.getOrNull(1)?.smoothedScore)
    }

    /** Worth labelling as "maybe" even when not confident. */
    val plausible: Boolean get() = top?.let { it.match.isTextHit || it.smoothedScore >= Calibration.MAYBE } == true
}

/** Result of analyzing one camera frame. */
class LiveFrame(
    /** The upright frame the boxes refer to. */
    val frame: Bitmap,
    val objects: List<DetectedPart>,
    val frameMs: Long,
    val frameNo: Int,
    /** Set when frames cannot be analyzed (e.g. a model failed to load). */
    val problem: String? = null,
)

/**
 * CameraX analyzer that works like a YOLO-style detector over the user's own parts library:
 * FastSAM proposes every individual object (so a pile is split into its parts), each object is
 * cut out with its mask and embedded with DINOv2, and the embedding is matched against the
 * library; OCR text inside a box counts towards that box. Boxes are tracked across frames so
 * scores can be smoothed and embeddings reused — at most [MAX_EMBEDS_PER_FRAME] objects are
 * (re)embedded per frame, which keeps the frame rate up when many parts are in view.
 */
class LiveScanner(
    private val embedder: ImageEmbedderHelper,
    private val ocr: OcrHelper,
    private val finder: ObjectFinder,
    private val parts: () -> List<Part>,
    private val onResult: (LiveFrame) -> Unit,
) : ImageAnalysis.Analyzer {

    @Volatile var lastFrame: Bitmap? = null
        private set

    private var frameNo = 0
    private var lastLines: List<OcrLine> = emptyList()
    private val tracker = BoxTracker()
    /** tracking key → (part id → smoothed score) */
    private val smoothed = HashMap<Int, HashMap<String, Float>>()
    /** tracking key → (embedding, when it was computed) */
    private val embeddings = HashMap<Int, Pair<FloatArray, Long>>()

    override fun analyze(image: ImageProxy) {
        try {
            val start = SystemClock.elapsedRealtime()
            val frame = upright(image)
            lastFrame = frame
            frameNo++

            if (frameNo % 3 == 1) lastLines = runCatching { ocr.readBoxedLinesBlocking(frame) }.getOrDefault(emptyList())

            val set = if (finder.isAvailable) {
                finder.propose(frame, minScore = LIVE_MIN_SCORE, nmsIou = 0.5f, maxCount = MAX_OBJECTS)
            } else null
            val proposals = set?.proposals ?: listOf(Proposal(centerBox(frame), 1f, emptyList()))
            val keys = tracker.assign(proposals.map { it.box })
            refreshEmbeddings(frame, set, proposals, keys, start)

            val library = parts()
            val objects = proposals.mapIndexed { i, p ->
                val key = keys[i]
                val texts = lastLines.filter { line -> line.box?.let { p.box.contains(it.centerX(), it.centerY()) } ?: false }
                    .map { it.text }
                val query = embeddings[key]?.first?.takeIf { it.isNotEmpty() }
                val ranked = PartMatcher.rank(library, listOfNotNull(query), texts, limit = MAX_CANDIDATES)
                DetectedPart(
                    key = key,
                    box = p.box,
                    candidates = smooth(key, ranked),
                    readNumber = OcrHelper.partNumberCandidates(texts).maxByOrNull { it.length },
                    isFallback = set == null,
                )
            }
            smoothed.keys.retainAll(keys.toSet())
            embeddings.keys.retainAll(keys.toSet())

            onResult(
                LiveFrame(
                    frame = frame,
                    objects = objects,
                    frameMs = SystemClock.elapsedRealtime() - start,
                    frameNo = frameNo,
                    problem = when {
                        !embedder.isAvailable -> "外观识别模型加载失败，只能识别零件上的文字"
                        !finder.isAvailable -> "物体检测模型加载失败，只识别画面中心"
                        else -> null
                    },
                )
            )
        } catch (t: Throwable) {
            // Throwable so that native-library errors show up on screen instead of silently stopping analysis.
            Log.w(TAG, "Frame analysis failed", t)
            lastFrame?.let { onResult(LiveFrame(it, emptyList(), 0, frameNo, "识别出错：${t.message ?: t.javaClass.simpleName}")) }
        } finally {
            image.close()
        }
    }

    /** New objects first, then the stalest; at most [MAX_EMBEDS_PER_FRAME] model runs per frame. */
    private fun refreshEmbeddings(frame: Bitmap, set: ProposalSet?, proposals: List<Proposal>, keys: List<Int>, now: Long) {
        proposals.indices
            .filter { i -> embeddings[keys[i]]?.let { now - it.second > REFRESH_MS } ?: true }
            .sortedBy { i -> embeddings[keys[i]]?.second ?: Long.MIN_VALUE }
            .take(MAX_EMBEDS_PER_FRAME)
            .forEach { i ->
                val crop = if (set != null) finder.maskedCrop(frame, set, proposals[i]) else ObjectFinder.crop(frame, proposals[i].box)
                embeddings[keys[i]] = embedder.embed(crop) to now
            }
    }

    private fun smooth(key: Int, ranked: List<MatchResult>): List<LiveCandidate> {
        val scores = smoothed.getOrPut(key) { HashMap() }
        val seen = HashSet<String>()
        val result = ranked.map { m ->
            seen += m.part.id
            val prev = scores[m.part.id] ?: m.imageScore
            val s = prev + SMOOTHING * (m.imageScore - prev)
            scores[m.part.id] = s
            LiveCandidate(m, s)
        }
        scores.keys.retainAll(seen)
        return result.sortedWith(compareByDescending<LiveCandidate> { it.match.isTextHit }.thenByDescending { it.smoothedScore })
    }

    private fun upright(image: ImageProxy): Bitmap {
        val bitmap = image.toBitmap()
        val rotation = image.imageInfo.rotationDegrees
        if (rotation == 0) return bitmap
        val m = Matrix().apply { postRotate(rotation.toFloat()) }
        return Bitmap.createBitmap(bitmap, 0, 0, bitmap.width, bitmap.height, m, true)
    }

    private fun centerBox(frame: Bitmap): Rect {
        val side = (minOf(frame.width, frame.height) * 0.6f).toInt()
        val l = (frame.width - side) / 2
        val t = (frame.height - side) / 2
        return Rect(l, t, l + side, t + side)
    }

    /** Greedy IoU matching of this frame's boxes to the previous frames' tracks. */
    private class BoxTracker {
        private class Track(val id: Int, var box: Rect, var missed: Int)
        private val tracks = ArrayList<Track>()
        private var nextId = 1

        fun assign(boxes: List<Rect>): List<Int> {
            val ids = IntArray(boxes.size) { -1 }
            val pairs = ArrayList<Triple<Int, Track, Float>>()
            for ((i, b) in boxes.withIndex()) for (t in tracks) {
                val iou = ObjectFinder.iou(b, t.box)
                if (iou > 0.3f) pairs += Triple(i, t, iou)
            }
            val used = HashSet<Int>()
            for ((i, t, _) in pairs.sortedByDescending { it.third }) {
                if (ids[i] != -1 || t.id in used) continue
                ids[i] = t.id; used += t.id; t.box = boxes[i]; t.missed = 0
            }
            tracks.filter { it.id !in used }.forEach { it.missed++ }
            tracks.removeAll { it.missed > 3 }
            for (i in boxes.indices) if (ids[i] == -1) {
                val t = Track(nextId++, boxes[i], 0)
                tracks += t
                ids[i] = t.id
            }
            return ids.toList()
        }
    }

    companion object {
        private const val TAG = "LiveScanner"
        private const val SMOOTHING = 0.5f
        private const val LIVE_MIN_SCORE = 0.35f
        private const val MAX_OBJECTS = 15
        private const val MAX_CANDIDATES = 4
        private const val MAX_EMBEDS_PER_FRAME = 3
        private const val REFRESH_MS = 1000L
    }
}
