import time

from flask import *
import sqlite3, hashlib, os
from flask import Flask, render_template, session
from flask_socketio import SocketIO, emit


# 摄像头参数
camera = None
detecting = False
from werkzeug.utils import secure_filename
import cv2
from PIL import Image
import numpy as np
app = Flask(__name__)
app.secret_key = 'random string'
socketio = SocketIO(app)
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = set(['jpeg', 'jpg', 'png', 'gif'])
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# import detect
# model=detect.InitModel()
# model.model_init()
from ultralytics import YOLO
import cv2
model = YOLO("runs/detect/train10/weights/best.pt")
from decimal import Decimal,ROUND_HALF_UP
def round_dec(n, d):
    s = '0.' + '0' * d
    return Decimal(n).quantize(Decimal(s), ROUND_HALF_UP)


def getLoginDetails():
    with sqlite3.connect('database.db') as conn:
        cur = conn.cursor()
        if 'email' not in session:
            loggedIn = False
            firstName = ''
            noOfItems = 0
        else:
            loggedIn = True
            cur.execute("SELECT userId, firstName FROM users WHERE email = ?", (session['email'], ))
            userId, firstName = cur.fetchone()
            cur.execute("SELECT count(productId) FROM kart WHERE userId = ?", (userId, ))
            noOfItems = cur.fetchone()[0]
    conn.close()
    return (loggedIn, firstName, noOfItems)

@app.route("/")
def root():
    loggedIn, firstName, noOfItems = getLoginDetails()
    with sqlite3.connect('database.db') as conn:
        cur = conn.cursor()
        cur.execute('SELECT productId, name,chineseName, price, description, image, stock FROM products')
        itemData = cur.fetchall()
        cur.execute('SELECT categoryId, name FROM categories')
        categoryData = cur.fetchall()
    itemData = parse(itemData)   
    return render_template('home.html', itemData=itemData, loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems, categoryData=categoryData)

@app.route("/add")
def admin():
    with sqlite3.connect('database.db') as conn:
        cur = conn.cursor()
        cur.execute("SELECT categoryId, name FROM categories")
        categories = cur.fetchall()
    conn.close()
    return render_template('add.html', categories=categories)

@app.route("/addItem", methods=["GET", "POST"])
def addItem():
    if request.method == "POST":
        name = request.form['name']
        price = float(request.form['price'])
        description = request.form['description']
        stock = int(request.form['stock'])
        categoryId = int(request.form['category'])

        #Uploading image procedure
        image = request.files['image']
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        imagename = filename
        with sqlite3.connect('database.db') as conn:
            try:
                cur = conn.cursor()
                cur.execute('''INSERT INTO products (name, price, description, image, stock, categoryId) VALUES (?, ?, ?, ?, ?, ?)''', (name, price, description, imagename, stock, categoryId))
                conn.commit()
                msg="added successfully"
            except:
                msg="error occured"
                conn.rollback()
        conn.close()
        print(msg)
        return redirect(url_for('root'))

@app.route("/remove")
def remove():
    with sqlite3.connect('database.db') as conn:
        cur = conn.cursor()
        cur.execute('SELECT productId, name, price, description, image, stock FROM products')
        data = cur.fetchall()
    conn.close()
    return render_template('remove.html', data=data)

@app.route("/removeItem")
def removeItem():
    productId = request.args.get('productId')
    with sqlite3.connect('database.db') as conn:
        try:
            cur = conn.cursor()
            cur.execute('DELETE FROM products WHERE productID = ?', (productId, ))
            conn.commit()
            msg = "Deleted successsfully"
        except:
            conn.rollback()
            msg = "Error occured"
    conn.close()
    print(msg)
    return redirect(url_for('root'))

@app.route("/displayCategory")
def displayCategory():
        loggedIn, firstName, noOfItems = getLoginDetails()
        categoryId = request.args.get("categoryId")
        with sqlite3.connect('database.db') as conn:
            cur = conn.cursor()
            cur.execute("SELECT products.productId, products.name,products.chineseName, products.price, products.image, categories.name FROM products, categories WHERE products.categoryId = categories.categoryId AND categories.categoryId = ?", (categoryId, ))
            data = cur.fetchall()
        conn.close()
        categoryName = data[0][5]
        data = parse(data)
        return render_template('displayCategory.html', data=data, loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems, categoryName=categoryName)

@app.route("/account/profile")
def profileHome():
    if 'email' not in session:
        return redirect(url_for('root'))
    loggedIn, firstName, noOfItems = getLoginDetails()
    return render_template("profileHome.html", loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems)

@app.route("/account/profile/edit")
def editProfile():
    if 'email' not in session:
        return redirect(url_for('root'))
    loggedIn, firstName, noOfItems = getLoginDetails()
    with sqlite3.connect('database.db') as conn:
        cur = conn.cursor()
        cur.execute("SELECT userId, email, firstName, lastName, address1, address2, zipcode, city, state, country, phone FROM users WHERE email = ?", (session['email'], ))
        profileData = cur.fetchone()
    conn.close()
    return render_template("editProfile.html", profileData=profileData, loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems)

@app.route("/account/profile/changePassword", methods=["GET", "POST"])
def changePassword():
    if 'email' not in session:
        return redirect(url_for('loginForm'))
    if request.method == "POST":
        oldPassword = request.form['oldpassword']
        oldPassword = hashlib.md5(oldPassword.encode()).hexdigest()
        newPassword = request.form['newpassword']
        newPassword = hashlib.md5(newPassword.encode()).hexdigest()
        with sqlite3.connect('database.db') as conn:
            cur = conn.cursor()
            cur.execute("SELECT userId, password FROM users WHERE email = ?", (session['email'], ))
            userId, password = cur.fetchone()
            if (password == oldPassword):
                try:
                    cur.execute("UPDATE users SET password = ? WHERE userId = ?", (newPassword, userId))
                    conn.commit()
                    msg="Changed successfully"
                except:
                    conn.rollback()
                    msg = "Failed"
                return render_template("changePassword.html", msg=msg)
            else:
                msg = "Wrong password"
        conn.close()
        return render_template("changePassword.html", msg=msg)
    else:
        return render_template("changePassword.html")

@app.route("/updateProfile", methods=["GET", "POST"])
def updateProfile():
    if request.method == 'POST':
        email = request.form['email']
        firstName = request.form['firstName']
        lastName = request.form['lastName']
        address1 = request.form['address1']
        address2 = request.form['address2']
        zipcode = request.form['zipcode']
        city = request.form['city']
        state = request.form['state']
        country = request.form['country']
        phone = request.form['phone']
        with sqlite3.connect('database.db') as con:
                try:
                    cur = con.cursor()
                    cur.execute('UPDATE users SET firstName = ?, lastName = ?, address1 = ?, address2 = ?, zipcode = ?, city = ?, state = ?, country = ?, phone = ? WHERE email = ?', (firstName, lastName, address1, address2, zipcode, city, state, country, phone, email))

                    con.commit()
                    msg = "Saved Successfully"
                except:
                    con.rollback()
                    msg = "Error occured"
        con.close()
        return redirect(url_for('editProfile'))

@app.route("/loginForm")
def loginForm():
    if 'email' in session:
        return redirect(url_for('root'))
    else:
        return render_template('login.html', error='')

@app.route("/login", methods = ['POST', 'GET'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if is_valid(email, password):
            session['email'] = email
            return redirect(url_for('root'))
        else:
            error = 'Invalid UserId / Password'
            return render_template('login.html', error=error)

@app.route("/productDescription")
def productDescription():
    loggedIn, firstName, noOfItems = getLoginDetails()
    productId = request.args.get('productId')
    with sqlite3.connect('database.db') as conn:
        cur = conn.cursor()
        cur.execute('SELECT productId, name, price, description, image, stock FROM products WHERE productId = ?', (productId, ))
        productData = cur.fetchone()
    conn.close()
    return render_template("productDescription.html", data=productData, loggedIn = loggedIn, firstName = firstName, noOfItems = noOfItems)

@app.route("/addToCart")
def addToCart():
    if 'email' not in session:
        return redirect(url_for('loginForm'))
    else:
        productId = int(request.args.get('productId'))
        with sqlite3.connect('database.db') as conn:
            cur = conn.cursor()
            cur.execute("SELECT userId FROM users WHERE email = ?", (session['email'], ))
            userId = cur.fetchone()[0]
            try:
                cur.execute("INSERT INTO kart (userId, productId) VALUES (?, ?)", (userId, productId))
                conn.commit()
                msg = "Added successfully"
            except:
                conn.rollback()
                msg = "Error occured"
        conn.close()
        return redirect(url_for('root'))

@app.route("/yoloPic", methods=['POST'])
def yoloPic():
    if 'email' not in session:
        return redirect(url_for('loginForm'))
    else:
        if 'image' not in request.files:
            return 'No file uploaded', 400

        image_file = request.files['image']
        if image_file.filename == '':
            return 'No file selected', 400
        name_list = []
        image = Image.open(image_file)
        np_array = np.array(image)

        # 将NumPy数组转换为OpenCV图像
        img = cv2.cvtColor(np_array, cv2.COLOR_RGB2BGR)
        # img = cv2.imread(image_file)
        # name_list = model.detect(name_list, img)

        res=model.predict(img, save=False, imgsz=640, conf=0.5)
        id_list = res[0].boxes.cls.cpu().numpy()
        namesMap = res[0].names
        for i in id_list:
            name_list.append(namesMap[i])
        # print(name_list)

        with sqlite3.connect('database.db') as conn:
            cur = conn.cursor()
            cur.execute("SELECT userId FROM users WHERE email = ?", (session['email'], ))
            userId = cur.fetchone()[0]
            product_id_name = {}
            cur.execute("SELECT productId,name FROM products ")
            res = cur.fetchall()
            for productId, name in res:
                product_id_name.update({name: productId})
            productIds = []
            for name in name_list:
                productIds.append(product_id_name[name])
            try:
                for productId in productIds:
                    cur.execute("INSERT INTO kart (userId, productId) VALUES (?, ?)", (userId, productId))
                    conn.commit()
                    msg = "Added successfully"
            except:
                conn.rollback()
                msg = "Error occured"
        conn.close()
        return redirect(url_for('cart'))
# # 检测函数
# # 摄像头参数
# camera = None
# detecting = False
# def detect(email):
#     global camera, detecting
#
#     while detecting:
#         if camera is not None:
#             success, frame = camera.read()  # 读取摄像头帧
#             # 在这里添加你的检测逻辑
#             # 如果检测到满足条件的商品，则跳出循环
#             name_list=[]
#             res = model.predict(frame, save=False, imgsz=640, conf=0.5)
#             id_list = res[0].boxes.cls.cpu().numpy()
#             namesMap = res[0].names
#             for i in id_list:
#                 name_list.append(namesMap[i])
#             print(name_list)
#             if len(name_list)!=0:
#                 with sqlite3.connect('database.db') as conn:
#                     cur = conn.cursor()
#                     cur.execute("SELECT userId FROM users WHERE email = ?", (email,))
#                     userId = cur.fetchone()[0]
#                     product_id_name = {}
#                     cur.execute("SELECT productId,name FROM products ")
#                     res = cur.fetchall()
#                     for productId, name in res:
#                         product_id_name.update({name: productId})
#                     productIds = []
#                     for name in name_list:
#                         productIds.append(product_id_name[name])
#                     try:
#                         for productId in productIds:
#                             cur.execute("INSERT INTO kart (userId, productId) VALUES (?, ?)", (userId, productId))
#                             conn.commit()
#                             msg = "Added successfully"
#                     except:
#                         conn.rollback()
#                         msg = "Error occured"
#                 conn.close()
#                 detecting = False
#                 return
#             # 将检测结果显示在Web界面上
#             ret, buffer = cv2.imencode('.jpg', frame)
#             frame = buffer.tobytes()
#             yield (b'--frame\r\n'
#                    b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
#
#
# @app.route('/start_detection')
# def start_detection():
#     global camera, detecting
#
#     if not detecting:
#         # 初始化摄像头
#         camera = cv2.VideoCapture(0)  # 这里的0表示默认摄像头设备
#         detecting = True
#
#     return '', 200
#
# @app.route('/video_feed')
# def video_feed():
#     global camera, detecting
#     email=session['email']
#     if detecting:
#         return Response(detect(email), mimetype='multipart/x-mixed-replace; boundary=frame')
#     else:
#         return redirect(url_for('cart'))
def detect(email):
    global camera, detecting
    pre_name_list = []
    while detecting:
        socketio.sleep(0.01)
        if camera is not None:
            success, frame = camera.read()  # 读取摄像头帧
            # 如果检测到满足条件的商品，则跳出循环
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
            print(pre_name_list, name_list)
            pre_name_list=name_list
            if flag :
                with sqlite3.connect('database.db') as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT userId FROM users WHERE email = ?", (email,))
                    userId = cur.fetchone()[0]
                    product_id_name = {}
                    cur.execute("SELECT productId,name FROM products ")
                    res = cur.fetchall()
                    for productId, name in res:
                        product_id_name.update({name: productId})
                    productIds = []
                    for name in name_list:
                        productIds.append(product_id_name[name])
                    try:
                        for productId in productIds:
                            cur.execute("INSERT INTO kart (userId, productId) VALUES (?, ?)", (userId, productId))
                            conn.commit()
                            msg = "Added successfully"
                    except:
                        conn.rollback()
                        msg = "Error occured"
                conn.close()
                detection_successful=True
            else:
                detection_successful = False
            # 将检测结果发送到客户端
            # print("detectimg",detectimg)
            # print("frame",frame)
            ret, buffer = cv2.imencode('.jpg', detectimg )
            frame_bytes = buffer.tobytes()
            socketio.emit('video_frame', frame_bytes)
            # time.sleep(1)
            if detection_successful:
                socketio.sleep(2)
                detecting = False
                socketio.emit('detection_result', 'success')  # 发送检测结果
@socketio.on('start_detection')
def start_detection():
    global camera, detecting

    if not detecting:
        # 初始化摄像头
        email=session['email']
        camera = cv2.VideoCapture(0)  # 这里的0表示默认摄像头设备
        detecting = True

        # 启动检测
        socketio.start_background_task(target=detect,email=email)

@socketio.on('disconnect')
def disconnect():
    global camera, detecting

    if detecting:
        # 停止检测
        detecting = False
        camera.release()

@app.route("/cart")
def cart():
    if 'email' not in session:
        return redirect(url_for('loginForm'))
    loggedIn, firstName, noOfItems = getLoginDetails()
    email = session['email']
    with sqlite3.connect('database.db') as conn:
        cur = conn.cursor()
        cur.execute("SELECT userId FROM users WHERE email = ?", (email, ))
        userId = cur.fetchone()[0]
        cur.execute("SELECT kart.id, products.chineseName, products.price, products.image FROM products, kart WHERE products.productId = kart.productId AND kart.userId = ?", (userId, ))
        products = cur.fetchall()
    totalPrice = Decimal(0)
    for row in products:
        totalPrice += Decimal(row[2])
    totalPrice=round_dec(totalPrice,2)
    return render_template("cart.html", products = products, totalPrice=totalPrice, loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems)
@app.route("/checkout")
def checkout():
    email = session['email']
    with sqlite3.connect('database.db') as con:
        cur = con.cursor()
        cur.execute("SELECT userId FROM users WHERE email = ?", (email, ))
        userId = cur.fetchone()[0]
        try:
            cur.execute("delete   FROM   kart WHERE userId = ?", (userId,))
            con.commit()
            msg = "Delete Successfully"
        except:
            con.rollback()
            msg = "Error occured"
    con.close()
    return redirect(url_for('root'))
@app.route("/removeFromCart")
def removeFromCart():
    if 'email' not in session:
        return redirect(url_for('loginForm'))
    email = session['email']
    id = int(request.args.get('id'))
    with sqlite3.connect('database.db') as conn:
        cur = conn.cursor()
        cur.execute("SELECT userId FROM users WHERE email = ?", (email, ))
        userId = cur.fetchone()[0]
        try:
            cur.execute("DELETE FROM kart WHERE id= ?", (id,))
            conn.commit()
            msg = "removed successfully"
        except:
            conn.rollback()
            msg = "error occured"
    conn.close()
    return redirect(url_for('cart'))

@app.route("/logout")
def logout():
    session.pop('email', None)
    return redirect(url_for('root'))

def is_valid(email, password):
    con = sqlite3.connect('database.db')
    cur = con.cursor()
    cur.execute('SELECT email, password FROM users')
    data = cur.fetchall()
    for row in data:
        if row[0] == email and row[1] == hashlib.md5(password.encode()).hexdigest():
            return True
    return False

@app.route("/register", methods = ['GET', 'POST'])
def register():
    if request.method == 'POST':
        #Parse form data    
        password = request.form['password']
        email = request.form['email']
        firstName = request.form['firstName']
        lastName = request.form['lastName']
        address1 = request.form['address1']
        address2 = request.form['address2']
        zipcode = request.form['zipcode']
        city = request.form['city']
        state = request.form['state']
        country = request.form['country']
        phone = request.form['phone']

        with sqlite3.connect('database.db') as con:
            try:
                cur = con.cursor()
                cur.execute('INSERT INTO users (password, email, firstName, lastName, address1, address2, zipcode, city, state, country, phone) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (hashlib.md5(password.encode()).hexdigest(), email, firstName, lastName, address1, address2, zipcode, city, state, country, phone))

                con.commit()

                msg = "Registered Successfully"
            except:
                con.rollback()
                msg = "Error occured"
        con.close()
        return render_template("login.html", error=msg)

@app.route("/registerationForm")
def registrationForm():
    return render_template("register.html")

def allowed_file(filename):
    return '.' in filename and \
            filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

def parse(data):
    ans = []
    i = 0
    while i < len(data):
        curr = []
        for j in range(7):
            if i >= len(data):
                break
            curr.append(data[i])
            i += 1
        ans.append(curr)
    return ans

if __name__ == '__main__':
    socketio.run(app, debug=True)
    # app.run(debug=True)

