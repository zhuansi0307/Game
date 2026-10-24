package com.partsvision.app.ml

import android.graphics.Bitmap
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.latin.TextRecognizerOptions
import com.google.android.gms.tasks.Tasks
import com.google.mlkit.vision.text.Text
import kotlinx.coroutines.tasks.await

/** Reads printed/stamped text from a part photo (ML Kit, fully on-device). */
class OcrHelper {
    private val recognizer = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS)

    /** Returns every text line found, top-to-bottom. */
    suspend fun readLines(bitmap: Bitmap): List<String> {
        return lines(recognizer.process(InputImage.fromBitmap(bitmap, 0)).await())
    }

    /** Blocking variant for camera analyzer threads; never call on the main thread. */
    fun readLinesBlocking(bitmap: Bitmap): List<String> =
        lines(Tasks.await(recognizer.process(InputImage.fromBitmap(bitmap, 0))))

    private fun lines(result: Text): List<String> =
        result.textBlocks.flatMap { block -> block.lines.map { it.text.trim() } }.filter { it.isNotEmpty() }

    fun close() = recognizer.close()

    companion object {
        /** Tokens that look like part numbers: ≥4 chars, contain a digit, letters/digits/-./ only. */
        fun partNumberCandidates(lines: List<String>): List<String> =
            lines.flatMap { it.split(Regex("\\s+")) }
                .map { it.trim(',', ';', ':', '(', ')', '[', ']') }
                .filter { it.length >= 4 && it.any(Char::isDigit) && it.all { c -> c.isLetterOrDigit() || c in "-./_" } }
                .distinct()

        /** Uppercase, drop separators and fold OCR look-alikes (O→0, I/L→1, S→5, B→8, Z→2). */
        fun normalize(s: String): String = buildString {
            for (c in s.uppercase()) {
                when (c) {
                    '-', '.', '/', '_', ' ' -> Unit
                    'O', 'Q', 'D' -> append('0')
                    'I', 'L' -> append('1')
                    'S' -> append('5')
                    'B' -> append('8')
                    'Z' -> append('2')
                    else -> append(c)
                }
            }
        }

        /** Similarity in 0..1 from Levenshtein distance on normalized strings. */
        fun similarity(a: String, b: String): Float {
            val x = normalize(a); val y = normalize(b)
            if (x.isEmpty() || y.isEmpty()) return 0f
            if (x == y) return 1f
            val prev = IntArray(y.length + 1) { it }
            val cur = IntArray(y.length + 1)
            for (i in 1..x.length) {
                cur[0] = i
                for (j in 1..y.length) {
                    val cost = if (x[i - 1] == y[j - 1]) 0 else 1
                    cur[j] = minOf(cur[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
                }
                cur.copyInto(prev)
            }
            return 1f - prev[y.length].toFloat() / maxOf(x.length, y.length)
        }
    }
}
