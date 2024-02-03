from ultralytics import YOLO

model = YOLO('runs/detect/train10/weights/best.pt')

# results = model.train(data='data.yaml', epochs=200)
results = model.predict(source="0")