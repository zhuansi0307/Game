package com.partsvision.app.data

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.UUID

data class PartPhoto(
    val id: String,
    val path: String,
    /** L2-normalized embeddings of several crops (full frame, centre); empty if the embedder was unavailable. */
    val embeddings: List<FloatArray>,
)

data class Part(
    val id: String,
    val partNumber: String,
    val name: String,
    val note: String,
    val photos: List<PartPhoto>,
    val createdAt: Long,
)

/**
 * Parts library persisted as a single JSON index plus JPEG files in app-private storage.
 * Sized for a workshop catalogue (hundreds to a few thousand photos), which keeps
 * brute-force similarity search fast without a database.
 */
class PartRepository(context: Context) {
    private val root = File(context.filesDir, "parts").apply { mkdirs() }
    private val photoDir = File(root, "photos").apply { mkdirs() }
    private val indexFile = File(root, "index.json")
    private val mutex = Mutex()

    /** Embedding model version the stored vectors were computed with. */
    var embeddingVersion = 0
        private set

    private val _parts = MutableStateFlow<List<Part>>(emptyList())
    val parts: StateFlow<List<Part>> = _parts.asStateFlow()

    suspend fun load() = withContext(Dispatchers.IO) {
        mutex.withLock {
            _parts.value = if (indexFile.exists()) parse(indexFile.readText()) else emptyList()
        }
    }

    fun get(id: String): Part? = _parts.value.firstOrNull { it.id == id }

    fun findByNumber(partNumber: String): Part? =
        _parts.value.firstOrNull { it.partNumber.equals(partNumber.trim(), ignoreCase = true) }

    /** Adds photos to the part with this number, creating the part if it does not exist yet. */
    suspend fun upsert(
        partNumber: String,
        name: String,
        note: String,
        photos: List<Pair<Bitmap, List<FloatArray>>>,
    ): Part = withContext(Dispatchers.IO) {
        mutex.withLock {
            val number = partNumber.trim()
            val saved = photos.map { (bitmap, embeddings) ->
                val id = UUID.randomUUID().toString()
                val file = File(photoDir, "$id.jpg")
                file.outputStream().use { bitmap.compress(Bitmap.CompressFormat.JPEG, 90, it) }
                PartPhoto(id, file.absolutePath, embeddings)
            }
            val current = _parts.value
            val existing = current.firstOrNull { it.partNumber.equals(number, ignoreCase = true) }
            val updated = if (existing != null) {
                existing.copy(
                    name = name.ifBlank { existing.name },
                    note = note.ifBlank { existing.note },
                    photos = existing.photos + saved,
                )
            } else {
                Part(UUID.randomUUID().toString(), number, name, note, saved, System.currentTimeMillis())
            }
            val list = if (existing != null) current.map { if (it.id == existing.id) updated else it }
            else current + updated
            persist(list)
            updated
        }
    }

    suspend fun delete(partId: String) = withContext(Dispatchers.IO) {
        mutex.withLock {
            val part = _parts.value.firstOrNull { it.id == partId } ?: return@withLock
            part.photos.forEach { File(it.path).delete() }
            persist(_parts.value.filterNot { it.id == partId })
        }
    }

    suspend fun deletePhoto(partId: String, photoId: String) = withContext(Dispatchers.IO) {
        mutex.withLock {
            val list = _parts.value.map { part ->
                if (part.id != partId) part
                else part.copy(photos = part.photos.filterNot { photo ->
                    (photo.id == photoId).also { if (it) File(photo.path).delete() }
                })
            }
            persist(list)
        }
    }

    /** Recomputes every photo's embeddings, e.g. after the embedding model changes. */
    suspend fun reembed(version: Int, embed: (Bitmap) -> List<FloatArray>) = withContext(Dispatchers.Default) {
        val updated = _parts.value.map { part ->
            part.copy(photos = part.photos.map { photo ->
                val bitmap = BitmapFactory.decodeFile(photo.path)
                photo.copy(embeddings = bitmap?.let(embed) ?: emptyList())
            })
        }
        mutex.withLock {
            // Keep photos added or removed while re-embedding ran.
            val byId = updated.flatMap { it.photos }.associateBy { it.id }
            val merged = _parts.value.map { part ->
                part.copy(photos = part.photos.map { byId[it.id] ?: it })
            }
            embeddingVersion = version
            withContext(Dispatchers.IO) { persist(merged) }
        }
    }

    private fun persist(list: List<Part>) {
        val tmp = File(root, "index.json.tmp")
        tmp.writeText(serialize(list))
        tmp.renameTo(indexFile)
        _parts.value = list
    }

    private fun serialize(list: List<Part>): String = JSONObject().apply {
        put("embeddingVersion", embeddingVersion)
        put("parts", serializeParts(list))
    }.toString()

    private fun serializeParts(list: List<Part>): JSONArray = JSONArray().apply {
        list.forEach { part ->
            put(JSONObject().apply {
                put("id", part.id)
                put("partNumber", part.partNumber)
                put("name", part.name)
                put("note", part.note)
                put("createdAt", part.createdAt)
                put("photos", JSONArray().apply {
                    part.photos.forEach { photo ->
                        put(JSONObject().apply {
                            put("id", photo.id)
                            put("path", photo.path)
                            put("embeddings", JSONArray().apply {
                                photo.embeddings.forEach { e -> put(JSONArray().apply { e.forEach { put(it.toDouble()) } }) }
                            })
                        })
                    }
                })
            })
        }
    }

    private fun parse(text: String): List<Part> {
        // Version 0 files were a bare array with one embedding per photo.
        val array = if (text.trimStart().startsWith("[")) JSONArray(text).also { embeddingVersion = 0 }
        else JSONObject(text).let { embeddingVersion = it.optInt("embeddingVersion"); it.getJSONArray("parts") }
        return (0 until array.length()).map { i ->
            val o = array.getJSONObject(i)
            val photos = o.getJSONArray("photos")
            Part(
                id = o.getString("id"),
                partNumber = o.getString("partNumber"),
                name = o.optString("name"),
                note = o.optString("note"),
                createdAt = o.optLong("createdAt"),
                photos = (0 until photos.length()).map { j ->
                    val p = photos.getJSONObject(j)
                    val list = p.optJSONArray("embeddings")
                    PartPhoto(
                        id = p.getString("id"),
                        path = p.getString("path"),
                        embeddings = if (list == null) emptyList() else (0 until list.length()).map { k ->
                            val e = list.getJSONArray(k)
                            FloatArray(e.length()) { n -> e.getDouble(n).toFloat() }
                        },
                    )
                },
            )
        }
    }
}
