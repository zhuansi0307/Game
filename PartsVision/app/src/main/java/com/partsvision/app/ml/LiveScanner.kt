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
data class LiveCandidate(
    val match: MatchResult,
    val smoothedScore: Float,
    /** Region-by-region score, present when this part had a close look-alike in the library. */
    val regionScore: Float? = null,
) {
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
        if (t.match.isTextHit) return true
        val second = candidates.getOrNull(1)
        // Look-alike parts: overall similarity cannot separate them, the region comparison decides.
        if (t.regionScore != null && second?.regionScore != null) {
            return maxOf(t.smoothedScore, second.smoothedScore) >= Calibration.CONFIDENT &&
                t.regionScore - second.regionScore >= Calibration.REGION_MARGIN
        }
        return Calibration.isConfident(t.smoothedScore, second?.smoothedScore)
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
    /** Where the time went, shown under the results for tuning. */
    val timing: String = "",
)

/**
 * CameraX analyzer that works like a YOLO-style detector over the user's own parts library:
 * YOLOE proposes every individual whole object (so a pile is split into its parts), each object is
 * cut out with its mask and embedded with DINOv2, and the embedding is matched against the
 * library; OCR text inside a box counts towards that box. Objects are tracked across frames
 * and identified once, then only re-checked occasionally — at most [MAX_EMBEDS_PER_FRAME]
 * objects are embedded per frame — so moving the phone does not restart recognition.
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
    /** What was computed for a tracked object when it was (re)identified. */
    private class Identified(val embedding: FloatArray, val at: Long, val regionScores: Map<String, Float>)
    /** tracking key → identification */
    private val embeddings = HashMap<Int, Identified>()
    /** tracking key → last result, shown while the detector briefly loses the object */
    private val lastResults = HashMap<Int, DetectedPart>()

    override fun analyze(image: ImageProxy) {
        try {
            val start = SystemClock.elapsedRealtime()
            val frame = upright(image)
            lastFrame = frame
            frameNo++

            var t = SystemClock.elapsedRealtime()
            if (frameNo % OCR_EVERY == 1) lastLines = runCatching { ocr.readBoxedLinesBlocking(frame) }.getOrDefault(emptyList())
            val ocrMs = SystemClock.elapsedRealtime() - t

            t = SystemClock.elapsedRealtime()
            val set = if (finder.isAvailable) {
                finder.propose(frame, minScore = LIVE_MIN_SCORE, nmsIou = 0.5f, maxCount = MAX_OBJECTS, size = LIVE_SIZE, live = true)
            } else null
            val detectMs = SystemClock.elapsedRealtime() - t
            val proposals = set?.proposals ?: listOf(Proposal(centerBox(frame), 1f, emptyList()))
            val now = SystemClock.elapsedRealtime()
            val keys = tracker.assign(proposals.map { it.box }, now)

            val library = parts()
            t = SystemClock.elapsedRealtime()
            val embedded = refreshEmbeddings(frame, set, proposals, keys, now, library)
            val embedMs = SystemClock.elapsedRealtime() - t

            val seen = proposals.mapIndexed { i, p ->
                val key = keys[i]
                val texts = lastLines.filter { line -> line.box?.let { p.box.contains(it.centerX(), it.centerY()) } ?: false }
                    .map { it.text }
                val id = embeddings[key]
                val query = id?.embedding?.takeIf { it.isNotEmpty() }
                DetectedPart(
                    key = key,
                    box = p.box,
                    candidates = if (query == null && texts.isEmpty()) lastResults[key]?.candidates.orEmpty()
                    else smooth(key, PartMatcher.rank(library, listOfNotNull(query), texts, limit = MAX_CANDIDATES), id?.regionScores.orEmpty()),
                    readNumber = OcrHelper.partNumberCandidates(texts).maxByOrNull { it.length },
                    isFallback = set == null,
                ).also { lastResults[key] = it }
            }
            // FastSAM also outlines pieces of a part (cap, nut, thread). Drop a box that mostly lies
            // inside a bigger box recognized as a part at least as well — that is the whole part.
            // But a box around *several* parts (two or more separate recognized boxes inside it) is
            // a group, not a part: drop the group box instead.
            val groups = seen.filter { big -> containsSeveral(big, seen) }.toSet()
            val whole = seen.filter { o ->
                o !in groups && seen.none { big ->
                    big !== o && big !in groups && big.plausible &&
                        big.box.width() * big.box.height() > o.box.width() * o.box.height() &&
                        ObjectFinder.overlapMin(big.box, o.box) > 0.6f &&
                        (!o.plausible || big.top!!.smoothedScore >= o.top!!.smoothedScore - 0.02f)
                }
            }
            // Objects the detector missed this frame but saw moments ago keep their box and label,
            // so labels do not blink when the hand moves.
            val seenKeys = keys.toSet()
            val coasting = tracker.recentlyLost(now, COAST_MS).filter { it !in seenKeys }.mapNotNull { lastResults[it] }
            val alive = tracker.aliveIds()
            smoothed.keys.retainAll(alive)
            embeddings.keys.retainAll(alive)
            lastResults.keys.retainAll(alive)

            onResult(
                LiveFrame(
                    frame = frame,
                    objects = whole + coasting,
                    frameMs = SystemClock.elapsedRealtime() - start,
                    frameNo = frameNo,
                    problem = when {
                        !embedder.isAvailable -> "外观识别模型加载失败，只能识别零件上的文字（${embedder.loadError?.take(120)}）"
                        !finder.isAvailable -> "物体检测模型加载失败，只识别画面中心"
                        else -> null
                    },
                    timing = "检测(${finder.backend(LIVE_SIZE)}) ${detectMs}ms · 比对 ${embedded}个 ${embedMs}ms" + if (ocrMs > 5) " · 读字 ${ocrMs}ms" else "",
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

    /** True when [big] contains two or more recognized objects that do not overlap each other. */
    private fun containsSeveral(big: DetectedPart, all: List<DetectedPart>): Boolean {
        val inside = all.filter { it !== big && it.plausible && ObjectFinder.overlapMin(big.box, it.box) > 0.8f &&
            it.box.width() * it.box.height() < big.box.width() * big.box.height() * 0.8f }
        for (i in inside.indices) for (j in i + 1 until inside.size) {
            if (ObjectFinder.overlapMin(inside[i].box, inside[j].box) < 0.3f) return true
        }
        return false
    }

    /**
     * Objects are identified once, when they first appear, and afterwards only re-checked every
     * [REFRESH_MS]; new objects go first. Returns how many were embedded this frame.
     */
    private fun refreshEmbeddings(
        frame: Bitmap, set: ProposalSet?, proposals: List<Proposal>, keys: List<Int>, now: Long, library: List<Part>,
    ): Int {
        val due = proposals.indices
            .filter { i -> embeddings[keys[i]]?.let { now - it.at > REFRESH_MS } ?: true }
            .sortedWith(compareBy<Int> { i -> embeddings[keys[i]]?.at ?: Long.MIN_VALUE }.thenByDescending { proposals[it].area })
            .take(MAX_EMBEDS_PER_FRAME)
        due.forEach { i ->
            val crop = if (set != null) finder.maskedCrop(frame, set, proposals[i]) else ObjectFinder.crop(frame, proposals[i].box)
            val f = embedder.features(crop)
            val emb = f?.embedding ?: FloatArray(0)
            val ranked = if (emb.isEmpty()) emptyList() else PartMatcher.rank(library, listOf(emb), emptyList(), limit = MAX_CANDIDATES)
            embeddings[keys[i]] = Identified(emb, now, PartMatcher.regionScores(f?.regions, ranked))
        }
        return due.size
    }

    private fun smooth(key: Int, ranked: List<MatchResult>, regionScores: Map<String, Float>): List<LiveCandidate> {
        val scores = smoothed.getOrPut(key) { HashMap() }
        val seen = HashSet<String>()
        val result = ranked.map { m ->
            seen += m.part.id
            val prev = scores[m.part.id] ?: m.imageScore
            val s = prev + SMOOTHING * (m.imageScore - prev)
            scores[m.part.id] = s
            LiveCandidate(m, s, regionScores[m.part.id])
        }
        scores.keys.retainAll(seen)
        // Among look-alikes (those with a region score) the region comparison decides the order.
        return result.sortedWith(
            compareByDescending<LiveCandidate> { it.match.isTextHit }
                .thenByDescending { it.regionScore?.let { r -> 1f + r } ?: it.smoothedScore }
        )
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

    /**
     * Follows objects from frame to frame. A box continues a track when it overlaps it or its
     * centre is close (relative to the object's size) and its size is similar — overlap alone
     * fails when the hand moves between two slow frames. Tracks survive [KEEP_MS] unseen, so an
     * object that briefly disappears comes back with its identity (and label) intact.
     */
    private class BoxTracker {
        private class Track(val id: Int, var box: Rect, var lastSeen: Long)
        private val tracks = ArrayList<Track>()
        private var nextId = 1

        fun assign(boxes: List<Rect>, now: Long): List<Int> {
            val ids = IntArray(boxes.size) { -1 }
            val pairs = ArrayList<Triple<Int, Track, Float>>()
            for ((i, b) in boxes.withIndex()) for (t in tracks) {
                val score = matchScore(b, t.box)
                if (score > 0f) pairs += Triple(i, t, score)
            }
            val used = HashSet<Int>()
            for ((i, t, _) in pairs.sortedByDescending { it.third }) {
                if (ids[i] != -1 || t.id in used) continue
                ids[i] = t.id; used += t.id; t.box = boxes[i]; t.lastSeen = now
            }
            tracks.removeAll { now - it.lastSeen > KEEP_MS }
            for (i in boxes.indices) if (ids[i] == -1) {
                val t = Track(nextId++, boxes[i], now)
                tracks += t
                ids[i] = t.id
            }
            return ids.toList()
        }

        fun recentlyLost(now: Long, withinMs: Long): List<Int> =
            tracks.filter { it.lastSeen < now && now - it.lastSeen <= withinMs }.map { it.id }

        fun aliveIds(): Set<Int> = tracks.mapTo(HashSet()) { it.id }

        private fun matchScore(a: Rect, b: Rect): Float {
            val iou = ObjectFinder.iou(a, b)
            val sizeA = maxOf(a.width(), a.height()).toFloat()
            val sizeB = maxOf(b.width(), b.height()).toFloat()
            val ratio = sizeA / sizeB
            if (ratio < 0.6f || ratio > 1.67f) return iou.takeIf { it > 0.3f } ?: 0f
            val dist = kotlin.math.hypot(a.exactCenterX() - b.exactCenterX(), a.exactCenterY() - b.exactCenterY())
            val near = 1f - dist / (0.8f * maxOf(sizeA, sizeB))
            return maxOf(iou, near * 0.8f).takeIf { it > 0.15f } ?: 0f
        }
    }

    companion object {
        private const val TAG = "LiveScanner"
        private const val SMOOTHING = 0.5f
        /** YOLOE prompt-free scores are class probabilities, lower than FastSAM objectness. */
        private const val LIVE_MIN_SCORE = 0.2f
        private const val MAX_OBJECTS = 15
        private const val MAX_CANDIDATES = 4
        private const val MAX_EMBEDS_PER_FRAME = 2
        private const val REFRESH_MS = 3000L
        private const val OCR_EVERY = 4
        /** How long a lost object keeps its identity, and how long its label stays on screen. */
        private const val KEEP_MS = 1500L
        private const val COAST_MS = 600L
    }
}
