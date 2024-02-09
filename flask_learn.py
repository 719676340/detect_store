from flask import Flask


from ultralytics import YOLO
import cv2
app = Flask(__name__)

model = YOLO("runs/detect/train10/weights/best.pt")

# 测试
@app.route("/")
def hello_world():
    camera = cv2.VideoCapture(0)
    detecting = True
    pre_name_list = []
    while detecting:
        if camera is not None:
            success, frame = camera.read()
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

    return pre_name_list




if __name__ == '__main__':
    # socketio.run(app, debug=True)
    app.run(debug=True)
