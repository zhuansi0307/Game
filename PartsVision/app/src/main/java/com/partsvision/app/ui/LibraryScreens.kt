package com.partsvision.app.ui

import android.graphics.Bitmap
import androidx.compose.foundation.Image
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.ExtendedFloatingActionButton
import androidx.compose.material3.FilledTonalIconButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import kotlinx.coroutines.launch
import java.io.File

@Composable
fun LibraryScreen(vm: AppViewModel, onOpenPart: (String) -> Unit, onAdd: () -> Unit) {
    val parts by vm.parts.collectAsState()
    var query by rememberSaveable { mutableStateOf("") }
    val filtered = remember(parts, query) {
        val q = query.trim()
        if (q.isEmpty()) parts.sortedByDescending { it.createdAt }
        else parts.filter {
            it.partNumber.contains(q, true) || it.name.contains(q, true) || it.note.contains(q, true)
        }
    }

    Box(Modifier.fillMaxSize()) {
        LazyColumn(
            Modifier.fillMaxSize().padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            item {
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(
                    value = query, onValueChange = { query = it },
                    modifier = Modifier.fillMaxWidth(),
                    leadingIcon = { Icon(Icons.Default.Search, null) },
                    placeholder = { Text("搜索零件号 / 名称 / 备注") },
                    singleLine = true,
                )
            }
            if (filtered.isEmpty()) {
                item {
                    Text(
                        if (parts.isEmpty()) "还没有零件。点右下角“录入零件”，输入零件号并拍几张不同角度的实拍图。"
                        else "没有匹配的零件。",
                        Modifier.padding(top = 24.dp),
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
            items(filtered, key = { it.id }) { part ->
                Card(Modifier.fillMaxWidth().clickable { onOpenPart(part.id) }) {
                    Row(Modifier.padding(10.dp), verticalAlignment = Alignment.CenterVertically) {
                        AsyncImage(
                            model = part.photos.firstOrNull()?.let { File(it.path) }, contentDescription = null,
                            modifier = Modifier.size(56.dp).clip(RoundedCornerShape(8.dp)),
                            contentScale = ContentScale.Crop,
                        )
                        Spacer(Modifier.width(12.dp))
                        Column(Modifier.weight(1f)) {
                            Text(part.partNumber, fontWeight = FontWeight.Bold)
                            if (part.name.isNotBlank()) Text(part.name, style = MaterialTheme.typography.bodySmall)
                        }
                        Text("${part.photos.size} 张图", style = MaterialTheme.typography.bodySmall)
                    }
                }
            }
            item { Spacer(Modifier.height(88.dp)) }
        }
        ExtendedFloatingActionButton(
            onClick = onAdd,
            icon = { Icon(Icons.Default.Add, null) },
            text = { Text("录入零件") },
            modifier = Modifier.align(Alignment.BottomEnd).padding(16.dp),
        )
    }
}

/**
 * Enter a part number and its photos. Re-using an existing number adds the photos to that
 * part, which is how users teach the matcher more angles of the same part.
 */
@Composable
fun PartEditScreen(
    vm: AppViewModel,
    initialNumber: String,
    initialPhoto: Bitmap?,
    onDone: (partId: String) -> Unit,
) {
    val existing = remember(initialNumber) { vm.repo.findByNumber(initialNumber) }
    var number by rememberSaveable { mutableStateOf(initialNumber) }
    var name by rememberSaveable { mutableStateOf(existing?.name.orEmpty()) }
    var note by rememberSaveable { mutableStateOf(existing?.note.orEmpty()) }
    val photos = remember { mutableStateListOf<Bitmap>().apply { initialPhoto?.let(::add) } }
    var saving by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    val scope = rememberCoroutineScope()
    val picker = rememberImagePicker(vm, multiple = true) { photos.add(it) }
    val match = vm.repo.findByNumber(number)

    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        OutlinedTextField(
            number, { number = it }, Modifier.fillMaxWidth(),
            label = { Text("零件号 *") }, singleLine = true,
            supportingText = { if (match != null) Text("已存在该零件号，照片将追加到“${match.name.ifBlank { match.partNumber }}”") },
        )
        OutlinedTextField(name, { name = it }, Modifier.fillMaxWidth(), label = { Text("名称（可选）") }, singleLine = true)
        OutlinedTextField(note, { note = it }, Modifier.fillMaxWidth(), label = { Text("备注：规格、材料、存放位置…") })

        Text("实拍图（建议 3~5 张不同角度，含钢印/标签特写）", style = MaterialTheme.typography.titleSmall)
        PickerButtons(picker)
        if (photos.isNotEmpty()) {
            LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                itemsIndexed(photos) { index, bmp ->
                    Box {
                        Image(
                            bmp.asImageBitmap(), null,
                            Modifier.size(96.dp).clip(RoundedCornerShape(8.dp)),
                            contentScale = ContentScale.Crop,
                        )
                        FilledTonalIconButton(
                            onClick = { photos.removeAt(index) },
                            modifier = Modifier.align(Alignment.TopEnd).size(28.dp),
                        ) { Icon(Icons.Default.Close, "移除", Modifier.size(16.dp)) }
                    }
                }
            }
        }
        error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        if (saving) LinearProgressIndicator(Modifier.fillMaxWidth())
        Button(
            onClick = {
                when {
                    number.isBlank() -> error = "请输入零件号"
                    photos.isEmpty() && match == null -> error = "请至少添加一张实拍图"
                    else -> {
                        saving = true
                        scope.launch {
                            try {
                                onDone(vm.savePart(number, name, note, photos.toList()))
                            } catch (e: Exception) {
                                error = e.message ?: "保存失败"
                            } finally {
                                saving = false
                            }
                        }
                    }
                }
            },
            enabled = !saving,
            modifier = Modifier.fillMaxWidth(),
        ) { Text("保存") }
    }
}

@Composable
fun PartDetailScreen(vm: AppViewModel, partId: String, onAddPhotos: (String) -> Unit, onDeleted: () -> Unit) {
    val parts by vm.parts.collectAsState()
    val part = parts.firstOrNull { it.id == partId } ?: return
    var confirmDelete by remember { mutableStateOf(false) }

    Column(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(part.partNumber, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
        if (part.name.isNotBlank()) Text(part.name, style = MaterialTheme.typography.titleMedium)
        if (part.note.isNotBlank()) Text(part.note, style = MaterialTheme.typography.bodyMedium)
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Button(onClick = { onAddPhotos(part.partNumber) }) { Text("添加照片") }
            OutlinedButton(onClick = { confirmDelete = true }) { Text("删除零件") }
        }
        LazyVerticalGrid(
            GridCells.Fixed(3),
            horizontalArrangement = Arrangement.spacedBy(6.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            items(part.photos, key = { it.id }) { photo ->
                Box {
                    AsyncImage(
                        model = File(photo.path), contentDescription = null,
                        modifier = Modifier.fillMaxWidth().aspectRatio(1f).clip(RoundedCornerShape(8.dp)),
                        contentScale = ContentScale.Crop,
                    )
                    IconButton(onClick = { vm.deletePhoto(part.id, photo.id) }, Modifier.align(Alignment.TopEnd)) {
                        Icon(Icons.Default.Delete, "删除照片", tint = MaterialTheme.colorScheme.error)
                    }
                }
            }
        }
    }

    if (confirmDelete) {
        AlertDialog(
            onDismissRequest = { confirmDelete = false },
            title = { Text("删除 ${part.partNumber}？") },
            text = { Text("零件及其 ${part.photos.size} 张照片将被删除，无法恢复。") },
            confirmButton = {
                TextButton(onClick = { confirmDelete = false; vm.deletePart(part.id); onDeleted() }) { Text("删除") }
            },
            dismissButton = { TextButton(onClick = { confirmDelete = false }) { Text("取消") } },
        )
    }
}
