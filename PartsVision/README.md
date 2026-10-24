# PartsVision 零件识别（Android）

拍照识别零件号，以及把手绘草图整理成规范零件图的 Android 应用。

## 功能

| 模块 | 说明 | 是否联网 |
|---|---|---|
| 零件库 | 输入零件号 + 名称/备注 + 多张实拍图入库；同一零件号再次录入会追加照片 | 离线 |
| 实时识别 | 相机画面中同时框出最多 5 个物体（ML Kit 物体检测 + 跟踪），每个物体：<br>① DINOv2-small（int8 ONNX）提取外观特征，与库中照片比对，一张参考图即可跨环境识别<br>② ML Kit OCR 读取框内钢印/标签并模糊匹配零件号（容忍 0/O、1/I、5/S 等混淆）<br>③（可选）对没把握的物体请 Claude 确认 | ①② 离线，③ 联网 |
| 草图出图 | 手机上手绘或拍纸面草图，填写尺寸/材料说明，由 Claude 生成三视图 + 尺寸标注 + 标题栏的 SVG 工程图，可分享导出 | 联网 |

## 架构

```
app/src/main/java/com/partsvision/app/
├── MainActivity.kt          # Compose 导航：识别 / 零件库 / 草图出图 / 设置
├── data/PartRepository.kt   # 零件库（JSON 索引 + 私有目录 JPEG + 特征向量）
├── data/SettingsStore.kt    # API Key / 模型 / 开关
├── ml/ImageEmbedderHelper.kt# DINOv2 图像特征提取（ONNX Runtime）
├── ml/ObjectFinder.kt       # 多物体检测与跟踪
├── ml/LiveScanner.kt        # 实时逐帧识别
├── ml/OcrHelper.kt          # ML Kit 文字识别 + 零件号模糊匹配
├── ml/PartMatcher.kt        # 文字命中优先、外观相似度排序
├── ai/ClaudeService.kt      # Claude API：照片确认 / 草图 → SVG 图纸（流式）
└── ui/                      # 各页面
```

## 构建

- 需要 JDK 17 和 Android SDK（compileSdk 35），`minSdk 26`（Android 8.0+）。
- 首次构建会自动下载 `dinov2_small_int8.onnx`（约 24 MB）到 `app/src/main/assets/`。该模型由 `tools/export_dinov2.py` 经 GitHub Actions「PartsVision embedding model」导出并发布在 Releases。

```bash
cd PartsVision
./gradlew assembleDebug
# 输出：app/build/outputs/apk/debug/app-debug.apk
```

也可以直接在 GitHub Actions（`PartsVision Android build`）里下载每次提交自动构建的 APK。

## 使用

1. **设置**页填写 Anthropic API Key（只用于云端功能，保存在本机应用私有存储）。默认模型 `claude-opus-5-5`。
2. **零件库** → 录入零件：输入零件号，拍 3~5 张不同角度的照片（最好含钢印/标签特写）。
3. **识别** → 拍照：显示候选零件（文字匹配 / 外观相似度），开启 AI 确认时会给出最终零件号和理由。识别结果可一键“作为新零件入库”或追加到已有零件。
4. **草图出图** → 画图或拍草图 → 补充尺寸说明 → 生成零件图 → 分享 SVG（可导入 Inkscape / AutoCAD 等继续编辑）。

## 已知限制 / 后续方向

- 外观比对用 DINOv2 通用特征，外形非常相近的零件（如不同长度的同规格螺栓）仍主要依赖文字识别或 AI 确认。零件量大后可用自己的照片微调。
- API Key 存在应用私有 SharedPreferences 中；正式分发建议改为自建后端代理，不在客户端保存密钥。
- 草图生成的图纸尺寸以草图标注为准，未标注的尺寸会按比例估算并以 `*` 标出，交付加工前需人工校核。
