from flask import *
from flask import Flask, render_template, session
from flask_socketio import SocketIO, emit
import cv2
import numpy as np
from ultralytics import YOLO
import cv2

camera = cv2.VideoCapture(0)
detecting = True


app = Flask(__name__)
app.secret_key = 'random string'
socketio = SocketIO(app)

model = YOLO("runs/detect/train10/weights/best.pt")
pre_name_list = []
while detecting:
    if camera is not None:
        success, frame = camera.read()
        # print(success, frame)
        name_list=[]
        res = model.predict(frame, save=False, imgsz=640, conf=0.7)
        id_list = res[0].boxes.cls.cpu().numpy()
        namesMap = res[0].names
        detectimg=res[0].plot()
        for i in id_list:
            name_list.append(namesMap[i])
        flag=len(name_list)!=0 and len(name_list)==len(pre_name_list)
        for i,j in zip(name_list,pre_name_list):
            if i==j:
                continue
            else:
                flag=False
                break
        pre_name_list=name_list
        if flag :
            detecting = False
        else:
            detecting = True

print(pre_name_list)
