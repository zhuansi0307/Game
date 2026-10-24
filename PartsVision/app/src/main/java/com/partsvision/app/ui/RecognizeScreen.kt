package com.partsvision.app.ui

import android.widget.Toast

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.FlashlightOff
import androidx.compose.material.icons.filled.FlashlightOn
import androidx.compose.material.icons.filled.PhotoLibrary
import androidx.compose.material.icons.filled.TextFields
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.FilledTonalIconButton
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.partsvision.app.data.Part
import com.partsvision.app.ml.LiveCandidate
import com.partsvision.app.ml.LiveResult
import com.partsvision.app.ml.MatchResult
import java.io.File

@Composable
fun RecognizeScreen(
    vm: AppViewModel,
    onOpenPart: (String) -> Unit,
    onAddFromPhoto: (prefillNumber: String) -> Unit,
) {
    val state by vm.recognize.collectAsState()
    if (state.photo == null) {
        LiveScanView(vm, onOpenPart, onAddFromPhoto)
    } else {
        ResultsView(vm, state, onOpenPart, onAddFromPhoto)
    }
}

/** Live camera: recognizes continuously and shows the part number over the preview. */
@Composable
private fun LiveScanView(
    vm: AppViewModel,
    onOpenPart: (String) -> Unit,
    onAddFromPhoto: (prefillNumber: String) -> Unit,
) {
    val parts by vm.parts.collectAsState()
    val live by vm.live.collectAsState()
    val liveAi by vm.liveAi.collectAsState()
    val reindexing by vm.reindexing.collectAsState()
    val context = LocalContext.current
    val permission = rememberCameraPermission()
    val scanner = remember { vm.newLiveScanner() }
    var torchOn by rememberSaveable { mutableStateOf(false) }
    val picker = rememberImagePicker(vm) { vm.recognize(it) }

    LaunchedEffect(Unit) {
        vm.clearLive()
        if (!permission.granted) permission.request()
    }

    if (!permission.granted) {
        Column(
            Modifier.fillMaxSize().padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp, Alignment.CenterVertically),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Text("需要相机权限才能实时识别零件")
            Button(onClick = permission.request) { Text("允许使用相机") }
            OutlinedPickFromGallery(picker)
        }
        return
    }

    Box(Modifier.fillMaxSize()) {
        CameraPreview(scanner, torchOn, Modifier.fillMaxSize())

        Text(
            if (parts.isEmpty()) "零件库为空：请先到“零件库”录入零件号和实拍图" else "把零件放在画面中间，结果实时显示在下方",
            Modifier.align(Alignment.TopCenter).padding(12.dp)
                .background(Color.Black.copy(alpha = 0.55f), RoundedCornerShape(16.dp))
                .padding(horizontal = 12.dp, vertical = 6.dp),
            color = Color.White,
            style = MaterialTheme.typography.bodySmall,
        )
        FilledTonalIconButton(
            onClick = { torchOn = !torchOn },
            modifier = Modifier.align(Alignment.TopEnd).padding(top = 48.dp, end = 12.dp),
        ) { Icon(if (torchOn) Icons.Default.FlashlightOn else Icons.Default.FlashlightOff, "补光灯") }

        Column(
            Modifier.align(Alignment.BottomCenter).fillMaxWidth().padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            LiveResultCard(
                live, liveAi, reindexing, onOpenPart,
                onConfirm = { part ->
                    vm.confirmLive(part)
                    Toast.makeText(context, "已把当前画面加入 ${part.partNumber} 的样本，之后识别更准", Toast.LENGTH_SHORT).show()
                },
                onAddFromPhoto = { number ->
                    scanner.lastFrame?.let(vm::recognize)
                    onAddFromPhoto(number)
                },
            )
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                Button(
                    onClick = { scanner.lastFrame?.let(vm::recognize) },
                    modifier = Modifier.weight(1f),
                ) {
                    Icon(Icons.Default.CameraAlt, null, Modifier.size(18.dp))
                    Spacer(Modifier.width(6.dp))
                    Text("定格 · 查看全部候选")
                }
                FilledTonalButton(onClick = picker.pickFromGallery) {
                    Icon(Icons.Default.PhotoLibrary, null, Modifier.size(18.dp))
                    Spacer(Modifier.width(6.dp))
                    Text("相册")
                }
            }
        }
    }
}

@Composable
private fun OutlinedPickFromGallery(picker: ImagePicker) {
    TextButton(onClick = picker.pickFromGallery) { Text("或者从相册选一张照片识别") }
}

@Composable
private fun LiveResultCard(
    live: LiveResult?,
    ai: LiveAiState,
    reindexing: Boolean,
    onOpenPart: (String) -> Unit,
    onConfirm: (Part) -> Unit,
    onAddFromPhoto: (String) -> Unit,
) {
    val top = live?.top
    val confident = live?.confident == true
    val plausible = live?.plausible == true
    val readNumber = live?.readNumber?.takeUnless { n -> top?.match?.isTextHit == true && top.match.matchedText == n }
    Card(
        Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = if (confident) MaterialTheme.colorScheme.primaryContainer
            else MaterialTheme.colorScheme.surface.copy(alpha = 0.92f),
        ),
    ) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            if (reindexing) Text("正在用新模型重建零件库索引，稍候识别会更准…", style = MaterialTheme.typography.bodySmall)
            live?.problem?.let { Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall) }

            when {
                live == null -> Row(verticalAlignment = Alignment.CenterVertically) {
                    CircularProgressIndicator(Modifier.size(16.dp), strokeWidth = 2.dp)
                    Spacer(Modifier.width(10.dp))
                    Text("正在启动相机…")
                }
                top != null && plausible -> {
                    Text(if (confident) "识别到零件号" else "可能是", style = MaterialTheme.typography.labelMedium)
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Column(Modifier.weight(1f)) {
                            Text(top.match.part.partNumber, style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
                            if (top.match.part.name.isNotBlank()) Text(top.match.part.name)
                            Text(scoreText(top), style = MaterialTheme.typography.bodySmall)
                        }
                        Column(horizontalAlignment = Alignment.End) {
                            FilledTonalButton(onClick = { onConfirm(top.match.part) }) {
                                Icon(Icons.Default.Check, null, Modifier.size(16.dp))
                                Spacer(Modifier.width(4.dp))
                                Text("正确")
                            }
                            TextButton(onClick = { onOpenPart(top.match.part.id) }) { Text("详情") }
                        }
                    }
                }
                top != null -> {
                    Text("零件库中没有把握的匹配", style = MaterialTheme.typography.titleSmall)
                    Text("最接近：${top.match.part.partNumber}（${scoreText(top)}）", style = MaterialTheme.typography.bodySmall)
                }
                else -> Text("零件库为空，先去“零件库”录入零件", style = MaterialTheme.typography.titleSmall)
            }

            val others = live?.candidates.orEmpty().drop(1)
            if (others.isNotEmpty() && plausible) {
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text("其他：", style = MaterialTheme.typography.bodySmall, modifier = Modifier.align(Alignment.CenterVertically))
                    others.forEach { c ->
                        AssistChip(
                            onClick = { onOpenPart(c.match.part.id) },
                            label = { Text("${c.match.part.partNumber} ${(c.smoothedScore * 100).toInt()}%") },
                        )
                    }
                }
            }

            if (readNumber != null) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text("读到文字：$readNumber", Modifier.weight(1f), style = MaterialTheme.typography.bodyMedium)
                    TextButton(onClick = { onAddFromPhoto(readNumber) }) { Text("按此入库") }
                }
            }

            if (ai.loading || ai.verdict != null || ai.error != null) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Default.AutoAwesome, null, Modifier.size(16.dp))
                    Spacer(Modifier.width(6.dp))
                    when {
                        ai.loading -> Text("AI 正在确认…", style = MaterialTheme.typography.bodySmall)
                        ai.verdict != null -> Text(
                            if (ai.verdict.partNumber.isBlank()) "AI：无法确定。${ai.verdict.reason}"
                            else "AI：${ai.verdict.partNumber}（${ai.verdict.confidence}%）${ai.verdict.reason}",
                            style = MaterialTheme.typography.bodySmall,
                        )
                        else -> Text("AI：${ai.error}", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.error)
                    }
                }
            }

            if (live != null && live.frameMs > 0) {
                Text("${live.frameMs} ms/帧", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}

private fun scoreText(c: LiveCandidate): String =
    if (c.match.isTextHit) "文字匹配 ${c.match.matchedText}" else "外观相似 ${(c.smoothedScore * 100).toInt()}%"

/** Detailed results for a captured frame or a gallery photo. */
@Composable
private fun ResultsView(
    vm: AppViewModel,
    state: RecognizeState,
    onOpenPart: (String) -> Unit,
    onAddFromPhoto: (prefillNumber: String) -> Unit,
) {
    val parts by vm.parts.collectAsState()

    LazyColumn(
        Modifier.fillMaxSize().padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Spacer(Modifier.height(8.dp))
            FilledTonalButton(onClick = vm::clearRecognition, modifier = Modifier.fillMaxWidth()) {
                Icon(Icons.Default.CameraAlt, null, Modifier.size(18.dp))
                Spacer(Modifier.width(8.dp))
                Text("返回相机继续识别")
            }
        }

        state.photo?.let { photo ->
            item {
                Image(
                    photo.asImageBitmap(), null,
                    Modifier.fillMaxWidth().height(240.dp).clip(RoundedCornerShape(12.dp)),
                    contentScale = ContentScale.Crop,
                )
            }
        }

        if (state.analyzing) item { LinearProgressIndicator(Modifier.fillMaxWidth()) }

        state.error?.let { err ->
            item { Text(err, color = MaterialTheme.colorScheme.error) }
        }

        if (state.aiLoading || state.ai != null) {
            item { AiCard(state, parts.map { it.partNumber }, onOpenPart = { number ->
                vm.repo.findByNumber(number)?.let { onOpenPart(it.id) } ?: onAddFromPhoto(number)
            }) }
        }

        if (state.ocrLines.isNotEmpty()) {
            item {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Default.TextFields, null, Modifier.size(16.dp))
                    Spacer(Modifier.width(6.dp))
                    Text("读到的文字：" + state.ocrLines.joinToString("  "), style = MaterialTheme.typography.bodySmall)
                }
            }
        }

        if (state.photo != null && !state.analyzing) {
            item {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text("候选零件", style = MaterialTheme.typography.titleSmall, modifier = Modifier.weight(1f))
                    if (vm.settings.hasApiKey && !state.aiLoading) TextButton(onClick = vm::retryAi) { Text("AI 再确认") }
                    TextButton(onClick = { onAddFromPhoto("") }) { Text("作为新零件入库") }
                }
            }
            if (state.matches.isEmpty()) {
                item {
                    Text(
                        if (parts.isEmpty()) "零件库为空，请先在“零件库”中录入零件号和实拍图。" else "没有找到相似零件。",
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
            items(state.matches, key = { it.part.id }) { m -> MatchRow(m) { onOpenPart(m.part.id) } }
        }
        item { Spacer(Modifier.height(24.dp)) }
    }
}

@Composable
private fun AiCard(state: RecognizeState, knownNumbers: List<String>, onOpenPart: (String) -> Unit) {
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.secondaryContainer)) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Default.AutoAwesome, null, Modifier.size(18.dp))
                Spacer(Modifier.width(8.dp))
                Text("AI 识别结果", fontWeight = FontWeight.Bold)
                if (state.aiLoading) {
                    Spacer(Modifier.width(12.dp))
                    CircularProgressIndicator(Modifier.size(16.dp), strokeWidth = 2.dp)
                }
            }
            state.ai?.let { ai ->
                if (ai.partNumber.isNotBlank()) {
                    Text(ai.partNumber, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
                    Text("置信度 ${ai.confidence}%", style = MaterialTheme.typography.bodySmall)
                } else {
                    Text("无法确定零件号", style = MaterialTheme.typography.titleMedium)
                }
                if (ai.textOnPart.isNotBlank()) Text("零件上的文字：${ai.textOnPart}", style = MaterialTheme.typography.bodySmall)
                if (ai.reason.isNotBlank()) Text(ai.reason, style = MaterialTheme.typography.bodyMedium)
                if (ai.partNumber.isNotBlank()) {
                    val inLibrary = knownNumbers.any { it.equals(ai.partNumber, ignoreCase = true) }
                    TextButton(onClick = { onOpenPart(ai.partNumber) }) {
                        Text(if (inLibrary) "查看该零件" else "按此零件号入库")
                    }
                }
            }
        }
    }
}

@Composable
private fun MatchRow(m: MatchResult, onClick: () -> Unit) {
    Card(Modifier.fillMaxWidth().clickable(onClick = onClick)) {
        Row(Modifier.padding(10.dp), verticalAlignment = Alignment.CenterVertically) {
            AsyncImage(
                model = m.part.photos.firstOrNull()?.let { File(it.path) }, contentDescription = null,
                modifier = Modifier.size(64.dp).clip(RoundedCornerShape(8.dp)),
                contentScale = ContentScale.Crop,
            )
            Spacer(Modifier.width(12.dp))
            Column(Modifier.weight(1f)) {
                Text(m.part.partNumber, fontWeight = FontWeight.Bold)
                if (m.part.name.isNotBlank()) Text(m.part.name, style = MaterialTheme.typography.bodySmall)
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    if (m.isTextHit) AssistChip(onClick = onClick, label = { Text("文字匹配 ${m.matchedText}") })
                    AssistChip(onClick = onClick, label = { Text("外观 ${(m.imageScore * 100).toInt()}%") })
                }
            }
            Text("${(m.score * 100).toInt()}%", style = MaterialTheme.typography.titleMedium)
        }
    }
}
