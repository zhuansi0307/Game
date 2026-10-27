package com.partsvision.app.ai

import com.anthropic.client.AnthropicClient
import com.anthropic.client.okhttp.AnthropicOkHttpClient
import com.anthropic.core.JsonValue
import com.anthropic.core.http.StreamResponse
import com.anthropic.errors.AnthropicServiceException
import com.anthropic.errors.AnthropicIoException
import com.anthropic.errors.RateLimitException
import com.anthropic.errors.UnauthorizedException
import com.anthropic.models.messages.Base64ImageSource
import com.anthropic.models.messages.ContentBlockParam
import com.anthropic.models.messages.ImageBlockParam
import com.anthropic.models.messages.MessageCreateParams
import com.anthropic.models.messages.OutputConfig
import com.anthropic.models.messages.RawMessageStreamEvent
import com.anthropic.models.messages.StopReason
import com.anthropic.models.messages.TextBlockParam

class ClaudeException(message: String, cause: Throwable? = null) : Exception(message, cause)

/** A library entry offered to the model as a possible match, with one reference photo. */
class ReferencePart(val partNumber: String, val name: String, val photoJpegBase64: String?)

/**
 * Cloud features backed by the Claude API: confirming which library part a photo shows,
 * and turning a hand sketch into a clean engineering drawing (SVG).
 * All calls block; run them on Dispatchers.IO.
 */
class ClaudeService(apiKey: String, private val model: String) {

    private val client: AnthropicClient = AnthropicOkHttpClient.builder().apiKey(apiKey).build()

    /**
     * Returns the model's answer as raw JSON text:
     * {"part_number": "...", "confidence": 0-100, "text_on_part": "...", "reason": "..."}
     */
    fun identifyPart(photoJpegBase64: String, ocrLines: List<String>, candidates: List<ReferencePart>): String {
        val blocks = mutableListOf<ContentBlockParam>()
        blocks += text("待识别零件的实拍照片：")
        blocks += jpeg(photoJpegBase64)
        candidates.forEachIndexed { i, c ->
            blocks += text("候选 ${i + 1}：零件号 ${c.partNumber}${if (c.name.isNotBlank()) "（${c.name}）" else ""}")
            c.photoJpegBase64?.let { blocks += jpeg(it) }
        }
        blocks += text(buildString {
            appendLine("设备端 OCR 在照片上读到的文字：${ocrLines.joinToString(" | ").ifBlank { "（无）" }}")
            appendLine()
            appendLine("请判断实拍照片中的零件对应哪个零件号。")
            appendLine("1. 若照片上能看到印刷/钢印/激光刻印的零件号，以它为准（注意 0/O、1/I、5/S、8/B 等易混字符）。")
            appendLine("2. 否则比较外形、孔位、材质、颜色与候选参考照片，选最接近的候选。")
            appendLine("3. 都无法确定时 part_number 填空字符串，并在 reason 中说明还需要拍哪个角度。")
            appendLine("只输出一个 JSON 对象，不要输出其它内容：")
            append("{\"part_number\": \"…\", \"confidence\": 0到100的整数, \"text_on_part\": \"照片上读到的文字\", \"reason\": \"简短中文理由\"}")
        })

        val params = baseParams(maxTokens = 4000L, effort = OutputConfig.Effort.MEDIUM)
            .system("你是一名经验丰富的机械零件识别专家，帮助仓库和维修人员根据实拍照片确认零件号。")
            .addUserMessageOfBlockParams(blocks)
            .build()
        return collect(params, onProgress = null)
    }

    /**
     * Identifies every part in a scene against the library ("set-of-marks" prompting): the phone
     * outlines candidate regions and numbers them in [markedJpegBase64]; the model decides which
     * numbered regions form one physical part (a part is often split into cap / body / nut
     * regions) and which reference it is. [cleanJpegBase64] is the same frame without marks, so
     * small details are not hidden under the labels.
     *
     * Returns raw JSON text:
     * {"items":[{"marks":[3,7],"part_number":"…","confidence":0-100,"reason":"…"}],"summary":"…"}
     */
    fun identifyScene(
        cleanJpegBase64: String,
        markedJpegBase64: String,
        markCount: Int,
        references: List<ReferencePart>,
    ): String {
        val blocks = mutableListOf<ContentBlockParam>()
        blocks += text("零件库参考照片（每种零件一张，零件号写在照片前）：")
        references.forEach { r ->
            blocks += text("零件号 ${r.partNumber}${if (r.name.isNotBlank()) "（${r.name}）" else ""}")
            r.photoJpegBase64?.let { blocks += jpeg(it) }
        }
        blocks += text("待识别的现场画面（原图）：")
        blocks += jpeg(cleanJpegBase64)
        blocks += text("同一画面，候选区域已用编号框标出（编号 1–$markCount）：")
        blocks += jpeg(markedJpegBase64)
        blocks += text(buildString {
            appendLine("请找出画面中每一个实际的零件，并判断它是零件库里的哪个零件号。")
            appendLine("1. 一个零件可能被拆成几个编号框（例如帽、本体、螺母、螺纹分别一个框），请把属于同一个零件的编号合并成一项；一个编号框也可能同时框住了几个零件，这时用最能代表该零件的编号。")
            appendLine("2. 对照参考照片的细节区分外形相近的零件：每个端口是快插口还是螺纹、帽的颜色、螺纹粗细长短、接头形状（直通/弯头/三通/Y 型）。不要只凭整体相似就判断。")
            appendLine("3. 零件库里没有的零件 part_number 填空字符串，并在 reason 里写出它像什么；托盘、地面、包装等不是零件的区域不要输出。")
            appendLine("4. confidence 是你对零件号判断的把握（0–100）。")
            appendLine("只输出一个 JSON 对象，不要输出其它内容：")
            append("{\"items\": [{\"marks\": [编号, …], \"part_number\": \"…\", \"confidence\": 整数, \"reason\": \"简短中文理由\"}], \"summary\": \"一句话总结各零件号的数量\"}")
        })
        val params = baseParams(maxTokens = 16000L, effort = OutputConfig.Effort.HIGH)
            .system("你是一名经验丰富的气动/液压接头和机械零件识别专家，擅长对照参考照片分辨外形相近的零件型号。")
            .addUserMessageOfBlockParams(blocks)
            .build()
        return collect(params, onProgress = null)
    }

    /**
     * Converts a hand-drawn sketch into an SVG engineering drawing.
     * [onProgress] receives the number of characters generated so far.
     */
    fun sketchToDrawing(
        sketchPngBase64: String,
        isPhoto: Boolean,
        description: String,
        partNumber: String,
        onProgress: ((Int) -> Unit)? = null,
    ): String {
        val prompt = buildString {
            appendLine("这是一张${if (isPhoto) "拍摄的纸面" else "在手机上绘制的"}零件手绘草图。请把它整理成规范的机械零件工程图，以单个 SVG 输出。")
            if (description.isNotBlank()) appendLine("补充说明 / 尺寸 / 材料：$description")
            if (partNumber.isNotBlank()) appendLine("零件号：$partNumber")
            appendLine()
            appendLine("要求：")
            appendLine("- 按第一角投影（GB/T 国标）布置主视图、俯视图、左视图；只有简单回转体时可用主视图 + 必要的剖视/断面。")
            appendLine("- 粗实线画可见轮廓，细虚线画不可见轮廓，细点画线画中心线和对称线。")
            appendLine("- 标注草图中给出的全部尺寸（单位 mm）；草图未给出的尺寸按比例合理估算，并在尺寸数字后加 \"*\" 表示估算。")
            appendLine("- 孔、倒角、圆角、螺纹按国标简化画法与标注（如 ⌀10、4×⌀6 均布、M8、C1、R2）。")
            appendLine("- 右下角画标题栏：零件名称、零件号、材料、比例、单位 mm、日期留空。")
            appendLine("- SVG 使用 viewBox=\"0 0 1189 841\"（A0 横向比例），白色背景，黑色线条，文字用 sans-serif 字体。")
            appendLine("- 只输出 SVG 代码本身，从 <svg 开始到 </svg> 结束，不要任何解释或 Markdown 代码块。")
        }
        val params = baseParams(maxTokens = 64000L, effort = OutputConfig.Effort.HIGH)
            .system("你是一名资深机械制图工程师，熟悉 GB/T 4458、GB/T 4459 等机械制图国家标准，擅长把草图整理成可交付加工的工程图。")
            .addUserMessageOfBlockParams(
                listOf(
                    ContentBlockParam.ofImage(
                        ImageBlockParam.builder().source(
                            Base64ImageSource.builder()
                                .mediaType(Base64ImageSource.MediaType.IMAGE_PNG)
                                .data(sketchPngBase64)
                                .build()
                        ).build()
                    ),
                    text(prompt),
                )
            )
            .build()
        return extractSvg(collect(params, onProgress))
    }

    private fun baseParams(maxTokens: Long, effort: OutputConfig.Effort): MessageCreateParams.Builder {
        val builder = MessageCreateParams.builder()
            .model(model)
            .maxTokens(maxTokens)
            .outputConfig(OutputConfig.builder().effort(effort).build())
        if (model in SERVER_FALLBACK_MODELS) {
            // If a safety classifier declines the request, the API retries it on a suitable fallback model.
            builder.putAdditionalHeader("anthropic-beta", "server-side-fallback-2026-07-01")
            builder.putAdditionalBodyProperty("fallbacks", JsonValue.from("default"))
        }
        return builder
    }

    /** Streams the response (avoids HTTP timeouts on long outputs) and returns the concatenated text. */
    private fun collect(params: MessageCreateParams, onProgress: ((Int) -> Unit)?): String {
        val out = StringBuilder()
        var stopReason: StopReason? = null
        try {
            client.messages().createStreaming(params).use { stream: StreamResponse<RawMessageStreamEvent> ->
                stream.stream().forEach { event ->
                    event.contentBlockDelta().flatMap { it.delta().text() }.ifPresent {
                        out.append(it.text())
                        onProgress?.invoke(out.length)
                    }
                    event.messageDelta().flatMap { it.delta().stopReason() }.ifPresent { stopReason = it }
                }
            }
        } catch (e: UnauthorizedException) {
            throw ClaudeException("API Key 无效，请在“设置”中检查。", e)
        } catch (e: RateLimitException) {
            throw ClaudeException("请求过于频繁，请稍后再试。", e)
        } catch (e: AnthropicServiceException) {
            throw ClaudeException("云端服务错误（${e.statusCode()}）：${e.message}", e)
        } catch (e: AnthropicIoException) {
            throw ClaudeException("网络连接失败，请检查网络后重试。", e)
        }
        when (stopReason) {
            StopReason.REFUSAL -> throw ClaudeException("模型拒绝了此请求，请换一张图片或修改说明。")
            StopReason.MAX_TOKENS -> if (out.isEmpty()) throw ClaudeException("输出被截断，请简化草图后重试。")
            else -> Unit
        }
        return out.toString()
    }

    private fun text(s: String) = ContentBlockParam.ofText(TextBlockParam.builder().text(s).build())

    private fun jpeg(base64: String) = ContentBlockParam.ofImage(
        ImageBlockParam.builder().source(
            Base64ImageSource.builder()
                .mediaType(Base64ImageSource.MediaType.IMAGE_JPEG)
                .data(base64)
                .build()
        ).build()
    )

    companion object {
        private val SERVER_FALLBACK_MODELS = setOf("claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5", "claude-fable-5-1")

        fun extractSvg(text: String): String {
            val start = text.indexOf("<svg")
            val end = text.lastIndexOf("</svg>")
            if (start < 0 || end < start) throw ClaudeException("未能从模型输出中解析出 SVG 图纸，请重试。")
            return text.substring(start, end + "</svg>".length)
        }
    }
}
