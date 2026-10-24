package com.partsvision.app.ui

import android.content.Intent
import android.graphics.Bitmap
import android.webkit.WebView
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Undo
import androidx.compose.material.icons.filled.DeleteSweep
import androidx.compose.material.icons.filled.Share
import androidx.compose.material3.Button
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.SegmentedButton
import androidx.compose.material3.SegmentedButtonDefaults
import androidx.compose.material3.SingleChoiceSegmentedButtonRow
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import com.partsvision.app.util.ImageUtils

private const val STROKE_PX = 5f

@Composable
fun SketchScreen(vm: AppViewModel) {
    val state by vm.sketch.collectAsState()
    val svg = state.svg
    if (svg != null) {
        DrawingResult(svg, onBack = vm::clearDrawing)
        return
    }

    var usePhoto by rememberSaveable { mutableStateOf(false) }
    var description by rememberSaveable { mutableStateOf("") }
    var partNumber by rememberSaveable { mutableStateOf("") }
    val strokes = remember { mutableStateListOf<List<Offset>>() }
    var current by remember { mutableStateOf<List<Offset>>(emptyList()) }
    var padSize by remember { mutableStateOf(IntSize.Zero) }
    var photo by remember { mutableStateOf<Bitmap?>(null) }
    val picker = rememberImagePicker(vm) { photo = it }

    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("手绘草图 → 规范零件图", style = MaterialTheme.typography.titleMedium)
        SingleChoiceSegmentedButtonRow(Modifier.fillMaxWidth()) {
            SegmentedButton(!usePhoto, { usePhoto = false }, SegmentedButtonDefaults.itemShape(0, 2)) { Text("手机上画") }
            SegmentedButton(usePhoto, { usePhoto = true }, SegmentedButtonDefaults.itemShape(1, 2)) { Text("拍纸面草图") }
        }

        if (!usePhoto) {
            Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                Text("用手指画出零件轮廓，可写上尺寸数字", Modifier.weight(1f).padding(top = 12.dp), style = MaterialTheme.typography.bodySmall)
                IconButton(onClick = { if (strokes.isNotEmpty()) strokes.removeAt(strokes.lastIndex) }) {
                    Icon(Icons.AutoMirrored.Filled.Undo, "撤销")
                }
                IconButton(onClick = { strokes.clear() }) { Icon(Icons.Default.DeleteSweep, "清空") }
            }
            Canvas(
                Modifier.fillMaxWidth().aspectRatio(1.3f)
                    .clip(RoundedCornerShape(8.dp))
                    .background(Color.White)
                    .border(1.dp, MaterialTheme.colorScheme.outline, RoundedCornerShape(8.dp))
                    .onSizeChanged { padSize = it }
                    .pointerInput(Unit) {
                        detectDragGestures(
                            onDragStart = { current = listOf(it) },
                            onDrag = { change, _ -> current = current + change.position },
                            onDragEnd = { strokes.add(current); current = emptyList() },
                            onDragCancel = { strokes.add(current); current = emptyList() },
                        )
                    },
            ) {
                (strokes + listOf(current)).forEach { pts ->
                    if (pts.size > 1) {
                        val path = Path().apply {
                            moveTo(pts[0].x, pts[0].y)
                            pts.drop(1).forEach { lineTo(it.x, it.y) }
                        }
                        drawPath(path, Color.Black, style = Stroke(STROKE_PX, cap = StrokeCap.Round, join = StrokeJoin.Round))
                    }
                }
            }
        } else {
            PickerButtons(picker, cameraLabel = "拍草图")
            photo?.let {
                Image(it.asImageBitmap(), null, Modifier.fillMaxWidth().height(260.dp).clip(RoundedCornerShape(8.dp)), contentScale = ContentScale.Fit)
            }
        }

        OutlinedTextField(
            description, { description = it }, Modifier.fillMaxWidth(),
            label = { Text("补充说明（可选）") },
            placeholder = { Text("例：法兰盘，外径 120，厚 15，4×⌀10 均布孔，材料 Q235") },
            minLines = 2,
        )
        OutlinedTextField(partNumber, { partNumber = it }, Modifier.fillMaxWidth(), label = { Text("零件号（可选，写入标题栏）") }, singleLine = true)

        state.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        if (state.generating) {
            LinearProgressIndicator(Modifier.fillMaxWidth())
            Text(
                if (state.progressChars == 0) "AI 正在理解草图…" else "正在绘制图纸…已生成 ${state.progressChars} 字符",
                style = MaterialTheme.typography.bodySmall,
            )
        }
        Button(
            onClick = {
                val input = if (usePhoto) photo else renderStrokes(strokes, padSize)
                if (input != null) vm.generateDrawing(input, usePhoto, description, partNumber)
            },
            enabled = !state.generating && (if (usePhoto) photo != null else strokes.isNotEmpty()),
            modifier = Modifier.fillMaxWidth(),
        ) { Text("生成零件图") }
    }
}

private fun renderStrokes(strokes: List<List<Offset>>, size: IntSize): Bitmap? {
    if (strokes.isEmpty() || size.width == 0 || size.height == 0) return null
    val bitmap = Bitmap.createBitmap(size.width, size.height, Bitmap.Config.ARGB_8888)
    val canvas = android.graphics.Canvas(bitmap)
    canvas.drawColor(android.graphics.Color.WHITE)
    val paint = android.graphics.Paint().apply {
        color = android.graphics.Color.BLACK
        strokeWidth = STROKE_PX
        style = android.graphics.Paint.Style.STROKE
        strokeCap = android.graphics.Paint.Cap.ROUND
        strokeJoin = android.graphics.Paint.Join.ROUND
        isAntiAlias = true
    }
    strokes.filter { it.size > 1 }.forEach { pts ->
        val path = android.graphics.Path().apply {
            moveTo(pts[0].x, pts[0].y)
            pts.drop(1).forEach { lineTo(it.x, it.y) }
        }
        canvas.drawPath(path, paint)
    }
    return bitmap
}

@Composable
private fun DrawingResult(svg: String, onBack: () -> Unit) {
    val context = LocalContext.current
    val html = remember(svg) {
        """<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=8">
        <style>html,body{margin:0;background:#fff}svg{width:100%;height:auto;display:block}</style></head>
        <body>$svg</body></html>"""
    }
    Column(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("生成的零件图（双指可缩放）", style = MaterialTheme.typography.titleMedium)
        AndroidView(
            factory = { ctx ->
                WebView(ctx).apply {
                    settings.builtInZoomControls = true
                    settings.displayZoomControls = false
                    settings.useWideViewPort = true
                    settings.loadWithOverviewMode = true
                }
            },
            update = { it.loadDataWithBaseURL(null, html, "text/html", "utf-8", null) },
            modifier = Modifier.fillMaxWidth().weight(1f).border(1.dp, MaterialTheme.colorScheme.outline),
        )
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            OutlinedButton(onClick = onBack, modifier = Modifier.weight(1f)) { Text("返回修改") }
            Button(
                onClick = {
                    val uri = ImageUtils.exportFile(context, "drawing_${System.currentTimeMillis()}.svg", svg.toByteArray())
                    val send = Intent(Intent.ACTION_SEND).apply {
                        type = "image/svg+xml"
                        putExtra(Intent.EXTRA_STREAM, uri)
                        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                    }
                    context.startActivity(Intent.createChooser(send, "分享 / 保存 SVG 图纸"))
                },
                modifier = Modifier.weight(1f),
            ) {
                Icon(Icons.Default.Share, null)
                Text("  分享 SVG")
            }
        }
    }
}
