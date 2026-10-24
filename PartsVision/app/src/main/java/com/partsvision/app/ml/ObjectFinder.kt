package com.partsvision.app.ml

import android.graphics.Bitmap
import android.graphics.Rect
import android.util.Log
import com.google.android.gms.tasks.Tasks
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.objects.ObjectDetection
import com.google.mlkit.vision.objects.ObjectDetector
import com.google.mlkit.vision.objects.defaults.ObjectDetectorOptions

/** A class-agnostic object box in bitmap pixel coordinates; [trackId] is stable across camera frames. */
data class FoundObject(val box: Rect, val trackId: Int?)

/**
 * Finds the individual objects in a frame (ML Kit, on-device, up to 5 at once) so each one can
 * be matched against the library separately — a YOLO-style "box + label" view where the label
 * comes from the user's own parts library rather than a fixed set of trained classes.
 */
class ObjectFinder {
    private val stream: ObjectDetector? = create(ObjectDetectorOptions.STREAM_MODE)
    private val single: ObjectDetector? = create(ObjectDetectorOptions.SINGLE_IMAGE_MODE)

    /** Objects in a live camera frame, with tracking ids. Blocking; call off the main thread. */
    fun detectInStream(bitmap: Bitmap): List<FoundObject> = detect(stream, bitmap)

    /** The most prominent object in a still photo, or null. Blocking; call off the main thread. */
    fun mainObject(bitmap: Bitmap): Rect? =
        detect(single, bitmap).maxByOrNull { it.box.width() * it.box.height() }?.box

    private fun detect(detector: ObjectDetector?, bitmap: Bitmap): List<FoundObject> {
        detector ?: return emptyList()
        val objects = Tasks.await(detector.process(InputImage.fromBitmap(bitmap, 0)))
        val frameArea = bitmap.width * bitmap.height
        return objects
            .map { FoundObject(Rect(it.boundingBox).apply { intersect(0, 0, bitmap.width, bitmap.height) }, it.trackingId) }
            // Ignore specks and boxes that are basically the whole frame (background).
            .filter { o ->
                val area = o.box.width() * o.box.height()
                area > frameArea * MIN_AREA && area < frameArea * MAX_AREA
            }
    }

    fun close() {
        stream?.close()
        single?.close()
    }

    companion object {
        private const val TAG = "ObjectFinder"
        private const val MIN_AREA = 0.01f
        private const val MAX_AREA = 0.9f

        private fun create(mode: Int): ObjectDetector? = try {
            ObjectDetection.getClient(
                ObjectDetectorOptions.Builder()
                    .setDetectorMode(mode)
                    .enableMultipleObjects()
                    .build()
            )
        } catch (t: Throwable) {
            Log.e(TAG, "Object detector unavailable", t)
            null
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
