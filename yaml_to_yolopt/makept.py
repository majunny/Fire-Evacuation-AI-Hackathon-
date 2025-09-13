from ultralytics import YOLO
import torch

print("MPS available:", torch.backends.mps.is_available())  # True면 Apple GPU 가속

model = YOLO('yolov8s.pt')  # 사전학습 가중치
model.train(
    data='/Users/parkminjun/Downloads/bald-egg.v4------last9-13.yolov8/data.yaml',  # 네 data.yaml
    epochs=80,          # 318장 기준 무난
    patience=15,        # 조기 종료
    imgsz=640,
    batch=8,           # 메모리 부족하면 8
    device='mps',       # 맥: Apple GPU 가속 (안 되면 'cpu')
)
