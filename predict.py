from ultralytics import YOLO
import cv2
model = YOLO("runs/detect/train10/weights/best.pt")
res=model("D:/数据挖掘/动手学深度学习/code/yolov8/datasets/train/images/WIN_20240115_22_58_32_Pro_25.jpg")
res_plotted = res[0].plot()
cv2.imshow("result", res_plotted)
cv2.waitKey(-1)
