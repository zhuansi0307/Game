package com.partsvision.app.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import com.partsvision.app.data.SettingsStore

@Composable
fun SettingsScreen(vm: AppViewModel) {
    val settings = vm.settings
    var apiKey by remember { mutableStateOf(settings.apiKey) }
    var model by remember { mutableStateOf(settings.model) }
    var cloudAssist by remember { mutableStateOf(settings.cloudAssist) }
    var saved by remember { mutableStateOf(false) }

    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("云端 AI（Claude）", style = MaterialTheme.typography.titleMedium)
        Text(
            "“草图生成零件图”和“AI 再确认”需要 Anthropic API Key（在 console.anthropic.com 创建）。" +
                "不填也能使用离线识别：钢印/标签文字识别 + 外观相似度比对。",
            style = MaterialTheme.typography.bodySmall,
        )
        OutlinedTextField(
            apiKey, { apiKey = it; saved = false }, Modifier.fillMaxWidth(),
            label = { Text("API Key") }, singleLine = true,
            visualTransformation = PasswordVisualTransformation(),
        )
        OutlinedTextField(
            model, { model = it; saved = false }, Modifier.fillMaxWidth(),
            label = { Text("模型") }, singleLine = true,
            supportingText = { Text("默认 ${SettingsStore.DEFAULT_MODEL}") },
        )
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text("识别时自动请 AI 确认", Modifier.weight(1f))
            Switch(cloudAssist, { cloudAssist = it; saved = false })
        }
        Button(
            onClick = {
                settings.apiKey = apiKey
                settings.model = model
                settings.cloudAssist = cloudAssist
                saved = true
            },
            modifier = Modifier.fillMaxWidth(),
        ) { Text(if (saved) "已保存" else "保存") }

        Text("使用提示", style = MaterialTheme.typography.titleMedium)
        Text(
            "1. 在“零件库”中录入零件号，每个零件拍 3~5 张不同角度的照片，最好包含钢印或标签特写。\n" +
                "2. 同一零件号再次录入会追加照片，照片越多，外观比对越准。\n" +
                "3. 识别时尽量让零件占满画面、背景简洁、光线均匀。\n" +
                "4. 草图上写清关键尺寸，生成的 SVG 图纸可用 CAD 软件（如 Inkscape、AutoCAD 导入）继续编辑。",
            style = MaterialTheme.typography.bodyMedium,
        )
    }
}
