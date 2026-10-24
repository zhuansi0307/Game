"""Export DINOv2-small as an ONNX image embedder for the PartsVision app.

DINOv2 is a self-supervised ViT whose features are strong at instance-level matching
("is this the same object?") across backgrounds and lighting, which is what one-shot part
lookup needs; ImageNet classifiers such as MobileNet mostly encode category and scene.

Graph:  input  "image"     float32 [1, 3, 224, 224], RGB in 0..1 (ImageNet normalization is in-graph)
        output "embedding" float32 [1, 768] = concat(L2(CLS token), L2(mean of patch tokens)) / sqrt(2)
                           so the result is itself unit length and cosine == dot product.
"""
import argparse

import torch
from transformers import AutoModel


class Embedder(torch.nn.Module):
    def __init__(self, model):
        super().__init__()
        self.model = model
        self.register_buffer("mean", torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1))
        self.register_buffer("std", torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1))

    def forward(self, image):
        x = (image - self.mean) / self.std
        tokens = self.model(pixel_values=x).last_hidden_state  # [1, 1 + patches, 384], layer-normed
        cls = torch.nn.functional.normalize(tokens[:, 0], dim=-1)
        patches = torch.nn.functional.normalize(tokens[:, 1:].mean(dim=1), dim=-1)
        return torch.cat([cls, patches], dim=-1) / (2 ** 0.5)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--fp32", default="dinov2_small_fp32.onnx")
    p.add_argument("--int8", default="dinov2_small_int8.onnx")
    args = p.parse_args()

    model = AutoModel.from_pretrained("facebook/dinov2-small").eval()
    wrapper = Embedder(model).eval()
    dummy = torch.rand(1, 3, 224, 224)
    with torch.no_grad():
        torch.onnx.export(
            wrapper, dummy, args.fp32,
            input_names=["image"], output_names=["embedding"],
            opset_version=17, do_constant_folding=True, dynamo=False,
        )

    from onnxruntime.quantization import QuantType, quantize_dynamic
    # MatMul only: ONNX Runtime 1.20 (the app's version) has no ConvInteger kernel for int8
    # weights, so a quantized patch-embedding Conv makes the model fail to load on the phone.
    quantize_dynamic(args.fp32, args.int8, weight_type=QuantType.QInt8, op_types_to_quantize=["MatMul"])

    # Sanity check: ONNX (fp32 and int8) agrees with PyTorch.
    import numpy as np
    import onnxruntime as ort
    with torch.no_grad():
        ref = wrapper(dummy).numpy()
    for path in (args.fp32, args.int8):
        out = ort.InferenceSession(path).run(None, {"image": dummy.numpy()})[0]
        cos = float((out * ref).sum() / (np.linalg.norm(out) * np.linalg.norm(ref)))
        print(f"{path}: cosine vs torch = {cos:.4f}, norm = {np.linalg.norm(out):.4f}")


if __name__ == "__main__":
    main()
