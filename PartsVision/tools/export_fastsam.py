"""Export FastSAM-s as an ONNX class-agnostic object proposer for the PartsVision app.

FastSAM ("segment anything", YOLOv8-seg architecture) proposes a box for every individual thing
in view, including touching items in a pile — unlike detectors trained on fixed categories,
which either ignore unfamiliar parts or merge a cluster into one box. The app only uses the
box branch; labels come from matching each box against the user's parts library.

Graph: input "images" float32 [1, 3, S, S] RGB 0..1 (letterboxed), S any multiple of 32 — the app
       runs ~320 for the live camera (fast) and 512 for pile scans (small parts).
       output0 float32 [1, 37, N]: cx, cy, w, h, objectness, 32 mask coefficients
       output1 float32 [1, 32, S/4, S/4]: mask prototypes
"""
import shutil

import onnxruntime as ort
from ultralytics import FastSAM

model = FastSAM("FastSAM-s.pt")
path = model.export(format="onnx", imgsz=512, opset=17, simplify=True, dynamic=True)
shutil.copy(path, "fastsam_s.onnx")
sess = ort.InferenceSession("fastsam_s.onnx")
print("inputs", [(i.name, i.shape) for i in sess.get_inputs()])
print("outputs", [(o.name, o.shape) for o in sess.get_outputs()])
