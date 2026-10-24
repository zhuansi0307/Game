package com.partsvision.app.ui

import android.widget.Toast

import android.graphics.Bitmap
import androidx.compose.foundation.Canvas
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
import androidx.compose.material3.IconButton
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
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.partsvision.app.data.Part
import com.partsvision.app.ml.LiveCandidate
import com.partsvision.app.ml.DetectedPart
import com.partsvision.app.ml.LiveFrame
import com.partsvision.app.ml.ObjectFinder
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

/** Live camera: finds every object in view and labels each with its part number, YOLO-style. */
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
            TextButton(onClick = picker.pickFromGallery) { Text("或者从相册选一张照片识别") }
        }
        return
    }

    Box(Modifier.fillMaxSize()) {
        CameraPreview(scanner, torchOn, Modifier.fillMaxSize())
        DetectionOverlay(live, liveAi, Modifier.fillMaxSize())

        Text(
            when {
                parts.isEmpty() -> "零件库为空：请先到“零件库”录入零件号和实拍图"
                reindexing -> "正在用新模型重建零件库索引…"
                else -> "可同时识别画面中的多个零件"
            },
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
            DetectionList(
                live, liveAi, onOpenPart,
                onConfirm = { part, obj, frame ->
                    vm.confirmLive(part, obj, frame)
                    Toast.makeText(context, "已加入 ${part.partNumber} 的样本，之后识别更准", Toast.LENGTH_SHORT).show()
                },
                onAdd = { number, obj, frame ->
                    vm.recognize(ObjectFinder.crop(frame, obj.box, pad = 0.15f))
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
                    Text("定格整张图")
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

private val ConfidentColor = Color(0xFF2E7D32)
private val MaybeColor = Color(0xFFF9A825)
private val UnknownColor = Color(0xFF9E9E9E)

private fun DetectedPart.color(): Color = when {
    confident -> ConfidentColor
    plausible -> MaybeColor
    else -> UnknownColor
}

/** Short label drawn on the box. */
private fun DetectedPart.label(ai: AiVerdict?): String {
    val t = top
    val local = when {
        t != null && confident -> "${t.match.part.partNumber} ${percent(t)}"
        t != null && plausible -> "${t.match.part.partNumber}? ${percent(t)}"
        readNumber != null -> "读到 $readNumber"
        else -> "未知"
    }
    return if (ai != null && ai.partNumber.isNotBlank() && !confident) "$local · AI:${ai.partNumber}" else local
}

private fun percent(c: LiveCandidate) = if (c.match.isTextHit) "文字" else "${(c.confidence * 100).toInt()}%"

/** Boxes and labels over the preview; maps frame pixels onto the FILL_CENTER-scaled preview. */
@Composable
private fun DetectionOverlay(live: LiveFrame?, ai: LiveAiState, modifier: Modifier) {
    val density = LocalDensity.current
    val textPaint = remember {
        android.graphics.Paint().apply {
            isAntiAlias = true
            color = android.graphics.Color.WHITE
            textSize = with(density) { 15.sp.toPx() }
            typeface = android.graphics.Typeface.DEFAULT_BOLD
        }
    }
    Canvas(modifier) {
        val f = live ?: return@Canvas
        val fw = f.frame.width.toFloat()
        val fh = f.frame.height.toFloat()
        val scale = maxOf(size.width / fw, size.height / fh)
        val dx = (size.width - fw * scale) / 2
        val dy = (size.height - fh * scale) / 2
        val stroke = 3.dp.toPx()
        val pad = 4.dp.toPx()

        f.objects.forEach { obj ->
            val color = obj.color()
            val left = obj.box.left * scale + dx
            val top = obj.box.top * scale + dy
            val w = obj.box.width() * scale
            val h = obj.box.height() * scale
            drawRect(
                color, Offset(left, top), Size(w, h),
                style = Stroke(stroke, pathEffect = if (obj.isFallback) PathEffect.dashPathEffect(floatArrayOf(18f, 12f)) else null),
            )
            val text = obj.label(ai.verdicts[obj.key]) + if (ai.loadingKey == obj.key) " · AI…" else ""
            val tw = textPaint.measureText(text)
            val th = textPaint.textSize
            val labelTop = (top - th - pad * 2).coerceAtLeast(0f)
            drawRect(color, Offset(left - stroke / 2, labelTop), Size(tw + pad * 2, th + pad * 2))
            drawContext.canvas.nativeCanvas.drawText(text, left + pad - stroke / 2, labelTop + pad + th * 0.85f, textPaint)
        }
    }
}

/** One row per detected object, with quick actions. */
@Composable
private fun DetectionList(
    live: LiveFrame?,
    ai: LiveAiState,
    onOpenPart: (String) -> Unit,
    onConfirm: (Part, DetectedPart, Bitmap) -> Unit,
    onAdd: (String, DetectedPart, Bitmap) -> Unit,
) {
    Card(
        Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.92f)),
    ) {
        Column(Modifier.padding(horizontal = 12.dp, vertical = 8.dp), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            if (live == null) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    CircularProgressIndicator(Modifier.size(16.dp), strokeWidth = 2.dp)
                    Spacer(Modifier.width(10.dp))
                    Text("正在启动相机…")
                }
                return@Column
            }
            live.problem?.let { Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall) }

            live.objects.forEach { obj ->
                val top = obj.top
                val verdict = ai.verdicts[obj.key]
                val suggested = verdict?.partNumber?.takeIf { it.isNotBlank() } ?: obj.readNumber
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(Modifier.size(10.dp).background(obj.color(), RoundedCornerShape(2.dp)))
                    Spacer(Modifier.width(8.dp))
                    Column(Modifier.weight(1f)) {
                        Text(
                            when {
                                top != null && (obj.confident || obj.plausible) -> top.match.part.partNumber + if (obj.confident) "" else "（可能）"
                                else -> "未在零件库中"
                            },
                            fontWeight = FontWeight.Bold,
                        )
                        val detail = buildList {
                            if (top != null) add(if (obj.confident || obj.plausible) scoreText(top) else "最接近 ${top.match.part.partNumber} ${percent(top)}")
                            if (top?.match?.part?.name?.isNotBlank() == true && (obj.confident || obj.plausible)) add(top.match.part.name)
                            if (verdict != null) add(if (verdict.partNumber.isBlank()) "AI 无法确定" else "AI：${verdict.partNumber} ${verdict.confidence}%")
                        }.joinToString(" · ")
                        if (detail.isNotEmpty()) Text(detail, style = MaterialTheme.typography.bodySmall)
                    }
                    if (top != null && (obj.confident || obj.plausible)) {
                        IconButton(onClick = { onConfirm(top.match.part, obj, live.frame) }) { Icon(Icons.Default.Check, "正确，加入样本") }
                        TextButton(onClick = { onOpenPart(top.match.part.id) }) { Text("详情") }
                    } else {
                        TextButton(onClick = { onAdd(suggested.orEmpty(), obj, live.frame) }) { Text("入库") }
                    }
                }
            }
            ai.error?.let { Text("AI：$it", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.error) }
            Text(
                "检测到 ${live.objects.count { !it.isFallback }} 个物体 · ${live.frameMs} ms/帧 · 第 ${live.frameNo} 帧",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

private fun scoreText(c: LiveCandidate): String =
    if (c.match.isTextHit) "文字匹配 ${c.match.matchedText}" else "外观匹配 ${(c.confidence * 100).toInt()}%"

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
                    AssistChip(onClick = onClick, label = { Text("外观 ${(m.imageConfidence * 100).toInt()}%") })
                }
            }
            Text("${(m.score * 100).toInt()}%", style = MaterialTheme.typography.titleMedium)
        }
    }
}
