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
import androidx.compose.foundation.layout.heightIn
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
    val pile by vm.pile.collectAsState()
    when {
        pile.active -> PileView(pile, onOpenPart, onBack = vm::clearPile)
        state.photo != null -> ResultsView(vm, state, onOpenPart, onAddFromPhoto)
        else -> LiveScanView(vm, onOpenPart, onAddFromPhoto)
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
    val picker = rememberImagePicker(vm) { vm.scanPile(it) }

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
                else -> "实时识别画面中的零件 · 零件堆在一起时点“识别整堆”"
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
                onAdd = { number, obj, frame ->
                    vm.recognize(ObjectFinder.crop(frame, obj.box, pad = 0.15f))
                    onAddFromPhoto(number)
                },
            )
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                Button(
                    onClick = { scanner.lastFrame?.let(vm::aiScan) },
                    modifier = Modifier.weight(1f),
                ) {
                    Icon(Icons.Default.AutoAwesome, null, Modifier.size(18.dp))
                    Spacer(Modifier.width(6.dp))
                    Text("AI 精准识别")
                }
                FilledTonalButton(onClick = { scanner.lastFrame?.let(vm::scanPile) }) {
                    Text("本机识别")
                }
                FilledTonalIconButton(onClick = picker.pickFromGallery, modifier = Modifier.size(48.dp)) {
                    Icon(Icons.Default.PhotoLibrary, "相册")
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
            if (!obj.plausible && obj.readNumber == null && ai.verdicts[obj.key] == null) {
                // Unknown object: thin outline only, so a pile does not drown in labels.
                drawRect(
                    color.copy(alpha = 0.7f), Offset(obj.box.left * scale + dx, obj.box.top * scale + dy),
                    Size(obj.box.width() * scale, obj.box.height() * scale), style = Stroke(1.dp.toPx()),
                )
                return@forEach
            }
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

/** Live summary: how many of each part are in view, plus the unrecognized ones. */
@Composable
private fun DetectionList(
    live: LiveFrame?,
    ai: LiveAiState,
    onOpenPart: (String) -> Unit,
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

            val recognized = live.objects.filter { it.plausible && it.top != null }
            recognized.groupBy { it.top!!.match.part.id }.entries
                .sortedByDescending { it.value.size }
                .take(4)
                .forEach { (_, objs) ->
                    val part = objs.first().top!!.match.part
                    val best = objs.maxBy { it.top!!.confidence }
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(Modifier.size(10.dp).background(best.color(), RoundedCornerShape(2.dp)))
                        Spacer(Modifier.width(8.dp))
                        Column(Modifier.weight(1f)) {
                            Text("${part.partNumber}  ×${objs.size}", fontWeight = FontWeight.Bold)
                            Text(
                                listOfNotNull(part.name.takeIf { it.isNotBlank() }, scoreText(best.top!!)).joinToString(" · "),
                                style = MaterialTheme.typography.bodySmall,
                            )
                        }
                        TextButton(onClick = { onOpenPart(part.id) }) { Text("详情") }
                    }
                }

            val unknown = live.objects.filter { !it.plausible && !it.isFallback }
            val withHint = unknown.firstOrNull { it.readNumber != null || ai.verdicts[it.key]?.partNumber?.isNotBlank() == true }
            if (withHint != null) {
                val number = ai.verdicts[withHint.key]?.partNumber?.takeIf { it.isNotBlank() } ?: withHint.readNumber.orEmpty()
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        if (ai.verdicts[withHint.key] != null) "AI 认为是 $number（零件库中没有）" else "读到 $number（零件库中没有）",
                        Modifier.weight(1f), style = MaterialTheme.typography.bodyMedium,
                    )
                    TextButton(onClick = { onAdd(number, withHint, live.frame) }) { Text("入库") }
                }
            }
            if (recognized.isEmpty() && withHint == null) {
                Text(
                    if (live.objects.isEmpty()) "没有检测到物体" else "画面中的物体都不在零件库中",
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
            if (ai.loadingKey != null) Text("AI 正在确认一个没把握的零件…", style = MaterialTheme.typography.bodySmall)
            ai.error?.let { Text("AI：$it", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.error) }
            Text(
                "识别 ${recognized.size} 个 · 未知 ${unknown.size} 个 · ${live.frameMs} ms/帧（${live.timing}）",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

/** Result of "识别整堆": the frozen frame with every found part boxed, and counts per part number. */
@Composable
private fun PileView(state: PileState, onOpenPart: (String) -> Unit, onBack: () -> Unit) {
    val density = LocalDensity.current
    val textPaint = remember {
        android.graphics.Paint().apply {
            isAntiAlias = true
            color = android.graphics.Color.WHITE
            textSize = with(density) { 12.sp.toPx() }
            typeface = android.graphics.Typeface.DEFAULT_BOLD
        }
    }
    Column(Modifier.fillMaxSize().padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        FilledTonalButton(onClick = onBack, modifier = Modifier.fillMaxWidth()) {
            Icon(Icons.Default.CameraAlt, null, Modifier.size(18.dp))
            Spacer(Modifier.width(8.dp))
            Text("返回相机")
        }
        if (state.running) {
            if (state.ai) {
                Text("AI 正在对照零件库逐个识别（通常 5–20 秒）…", style = MaterialTheme.typography.titleSmall)
                LinearProgressIndicator(Modifier.fillMaxWidth())
            } else {
                Text("正在逐个识别零件堆里的每个零件…", style = MaterialTheme.typography.titleSmall)
                LinearProgressIndicator(progress = { state.progress }, modifier = Modifier.fillMaxWidth())
            }
        }
        state.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        val result = state.result ?: return@Column

        Box(Modifier.fillMaxWidth().weight(1f)) {
            Image(result.frame.asImageBitmap(), null, Modifier.fillMaxSize(), contentScale = ContentScale.Fit)
            Canvas(Modifier.fillMaxSize()) {
                val fw = result.frame.width.toFloat()
                val fh = result.frame.height.toFloat()
                val scale = minOf(size.width / fw, size.height / fh)
                val dx = (size.width - fw * scale) / 2
                val dy = (size.height - fh * scale) / 2
                val pad = 2.dp.toPx()
                result.unknown.forEach { (b, _) ->
                    drawRect(
                        UnknownColor, Offset(b.left * scale + dx, b.top * scale + dy),
                        Size(b.width() * scale, b.height() * scale), style = Stroke(2.dp.toPx()),
                    )
                }
                result.detections.forEach { d ->
                    val color = if (d.confident) ConfidentColor else MaybeColor
                    val left = d.box.left * scale + dx
                    val top = d.box.top * scale + dy
                    drawRect(color, Offset(left, top), Size(d.box.width() * scale, d.box.height() * scale), style = Stroke(2.dp.toPx()))
                    val text = d.part.partNumber
                    val tw = textPaint.measureText(text)
                    val th = textPaint.textSize
                    drawRect(color, Offset(left, (top - th - pad * 2).coerceAtLeast(0f)), Size(tw + pad * 2, th + pad * 2))
                    drawContext.canvas.nativeCanvas.drawText(text, left + pad, (top - th - pad * 2).coerceAtLeast(0f) + pad + th * 0.85f, textPaint)
                }
            }
        }

        Text(
            "${if (result.byAi) "AI " else ""}共找到 ${result.detections.size} 个零件库中的零件（用时 ${"%.1f".format(result.millis / 1000f)} 秒）",
            style = MaterialTheme.typography.titleSmall,
        )
        result.summary?.let { Text(it, style = MaterialTheme.typography.bodyMedium) }
        result.unknown.take(3).forEach { (_, why) ->
            Text("灰框（不在零件库）：$why", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        LazyColumn(Modifier.heightIn(max = 220.dp)) {
            items(result.counts, key = { it.first.id }) { (part, count) ->
                val ds = result.detections.filter { it.part.id == part.id }
                Row(Modifier.fillMaxWidth().clickable { onOpenPart(part.id) }.padding(vertical = 6.dp), verticalAlignment = Alignment.CenterVertically) {
                    Box(Modifier.size(10.dp).background(if (ds.any { it.confident }) ConfidentColor else MaybeColor, RoundedCornerShape(2.dp)))
                    Spacer(Modifier.width(8.dp))
                    Column(Modifier.weight(1f)) {
                        Text("${part.partNumber}  ×$count", fontWeight = FontWeight.Bold)
                        if (part.name.isNotBlank()) Text(part.name, style = MaterialTheme.typography.bodySmall)
                    }
                    Text("${(ds.maxOf { it.confidence } * 100).toInt()}%", style = MaterialTheme.typography.bodySmall)
                }
            }
        }
        if (!result.byAi) Text(
            "提示：本机识别在零件摊开、少叠压时最准；分不清或一个零件被拆成几个框时，用“AI 精准识别”。",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        if (result.detections.isEmpty()) {
            Text("没有找到零件库里的零件。确认零件已录入，录入时把零件单独放在桌面上拍，不要拿在手里。")
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
