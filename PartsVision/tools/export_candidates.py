"""Export candidate open-source models for evaluation on real part photos (not used by the app
until they win the comparison).

Embedders (same graph contract as export_dinov2.py: "image" -> "embedding" [1,D], "patches" [1,256,C]):
  dinov2-base, dinov2-with-registers-small, dinov2-with-registers-base
Proposers (YOLOv8-seg output layout so the app's decoder can be reused):
  yoloe-11s-seg-pf / yoloe-11m-seg-pf  prompt-free YOLOE: whole-object boxes for ~4.6k categories;
                                       the class scores are reduced to one objectness channel in-graph
  yoloe-11s-seg-generic                YOLOE with generic text classes (parts, fittings, ...)
"""
import shutil, sys

import numpy as np
import onnx
import onnxruntime as ort
import torch
from onnx import helper, TensorProto
from onnxruntime.quantization import QuantType, quantize_dynamic
from transformers import AutoModel


class Embedder(torch.nn.Module):
    def __init__(self, model, registers):
        super().__init__()
        self.model, self.skip = model, 1 + registers
        self.register_buffer("mean", torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1))
        self.register_buffer("std", torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1))

    def forward(self, image):
        tokens = self.model(pixel_values=(image - self.mean) / self.std).last_hidden_state
        patches = tokens[:, self.skip:]
        cls = torch.nn.functional.normalize(tokens[:, 0], dim=-1)
        mean = torch.nn.functional.normalize(patches.mean(dim=1), dim=-1)
        return torch.cat([cls, mean], dim=-1) / (2 ** 0.5), patches


def export_embedder(hf_name, out):
    model = AutoModel.from_pretrained(hf_name).eval()
    regs = getattr(model.config, "num_register_tokens", 0) or 0
    with torch.no_grad():
        torch.onnx.export(Embedder(model, regs).eval(), torch.rand(1, 3, 224, 224), f"{out}_fp32.onnx",
                          input_names=["image"], output_names=["embedding", "patches"], opset_version=17, dynamo=False)
    quantize_dynamic(f"{out}_fp32.onnx", f"{out}_int8.onnx", weight_type=QuantType.QInt8, op_types_to_quantize=["MatMul"])
    print(out, [(o.name, o.shape) for o in ort.InferenceSession(f"{out}_int8.onnx").get_outputs()])


def reduce_classes(path, nc):
    """[1, 4+nc+32, N] -> [1, 4+1+32, N]: keep boxes, max over classes as objectness, mask coefs."""
    m = onnx.load(path)
    out = m.graph.output[0].name
    g = m.graph
    def const(name, vals):
        g.initializer.append(helper.make_tensor(name, TensorProto.INT64, [len(vals)], vals))
    const("rc_s0", [0]); const("rc_e0", [4]); const("rc_s1", [4]); const("rc_e1", [4 + nc])
    const("rc_s2", [4 + nc]); const("rc_e2", [4 + nc + 32]); const("rc_ax", [1])
    g.node.extend([
        helper.make_node("Slice", [out, "rc_s0", "rc_e0", "rc_ax"], ["rc_box"]),
        helper.make_node("Slice", [out, "rc_s1", "rc_e1", "rc_ax"], ["rc_cls"]),
        helper.make_node("ReduceMax", ["rc_cls"], ["rc_obj"], axes=[1], keepdims=1),
        helper.make_node("Slice", [out, "rc_s2", "rc_e2", "rc_ax"], ["rc_coef"]),
        helper.make_node("Concat", ["rc_box", "rc_obj", "rc_coef"], ["output0r"], axis=1),
    ])
    old = g.output[0]
    g.output.remove(old)
    g.output.insert(0, helper.make_tensor_value_info("output0r", TensorProto.FLOAT, None))
    onnx.save(m, path)


def export_yoloe(weights, out, classes=None):
    from ultralytics import YOLOE
    model = YOLOE(weights)
    if classes:
        model.set_classes(classes, model.get_text_pe(classes))
    nc = len(model.names)
    path = model.export(format="onnx", imgsz=512, opset=17, simplify=True, dynamic=True)
    shutil.copy(path, f"{out}.onnx")
    if nc > 1:
        reduce_classes(f"{out}.onnx", nc)
    s = ort.InferenceSession(f"{out}.onnx")
    outs = s.run(None, {s.get_inputs()[0].name: np.zeros((1, 3, 512, 512), np.float32)})
    print(out, "nc", nc, [o.shape for o in outs])


if __name__ == "__main__":
    which = sys.argv[1]
    if which == "embedders":
        export_embedder("facebook/dinov2-base", "dinov2_base")
        export_embedder("facebook/dinov2-with-registers-small", "dinov2reg_small")
        export_embedder("facebook/dinov2-with-registers-base", "dinov2reg_base")
    else:
        export_yoloe("yoloe-11s-seg-pf.pt", "yoloe11s_pf")
        export_yoloe("yoloe-11m-seg-pf.pt", "yoloe11m_pf")
        export_yoloe("yoloe-11s-seg.pt", "yoloe11s_generic",
                     ["pipe fitting", "pneumatic fitting", "hose connector", "valve", "bolt", "nut", "mechanical part", "tool"])
