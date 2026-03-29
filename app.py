import os, csv, time, datetime, threading
import cv2, numpy as np, pandas as pd
import pyttsx3
from flask import Flask, render_template, Response, request, jsonify

app = Flask(__name__)

######################### BACKGROUND UTILITIES #########################
def assure_path_exists(path):
    dir = os.path.dirname(path)
    if not os.path.exists(dir):
        os.makedirs(dir)

assure_path_exists("StudentDetails/")
assure_path_exists("TrainingImage/")
assure_path_exists("TrainingImageLabel/")
assure_path_exists("Attendance/")

def speak(text):
    def run_speech():
        try:
            engine = pyttsx3.init()
            engine.setProperty('rate', 150)
            engine.say(text)
            engine.runAndWait()
        except:
            pass
    threading.Thread(target=run_speech, daemon=True).start()

######################### CAMERA ENGINE #########################
class VideoCamera(object):
    def __init__(self):
        self.video = cv2.VideoCapture(0)
        self.mode = None
        self.reg_id = ""
        self.reg_name = ""
        self.sampleNum = 0
        self.serial_for_registration = 0
        self.detector = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")
        
        self.recognizer_att = None
        self.df = None
        self.recognized_id = None
        self.recognized_name = None
        self.load_data()
        
    def __del__(self):
        self.video.release()
        
    def load_data(self):
        if os.path.isfile("StudentDetails\\StudentDetails.csv"):
            self.df = pd.read_csv("StudentDetails\\StudentDetails.csv")
        if os.path.isfile("TrainingImageLabel\\Trainner.yml"):
            self.recognizer_att = cv2.face_LBPHFaceRecognizer.create()
            self.recognizer_att.read("TrainingImageLabel\\Trainner.yml")

    def get_frame(self):
        success, im = self.video.read()
        if not success:
            return None
        
        gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
        faces = self.detector.detectMultiScale(gray, 1.3, 5)

        if self.mode == "attendance" and self.recognizer_att is not None and self.df is not None:
            self.recognized_name = "Unknown"
            self.recognized_id = None
            for (x, y, w, h) in faces:
                cv2.rectangle(im, (x, y), (x + w, y + h), (0, 200, 0), 2)
                serial, conf = self.recognizer_att.predict(gray[y:y + h, x:x + w])
                if conf < 50:
                    try:
                        aa = self.df.loc[self.df['SERIAL NO.'] == serial]['NAME'].values[0]
                        ID = self.df.loc[self.df['SERIAL NO.'] == serial]['ID'].values[0]
                        self.recognized_name = str(aa)
                        self.recognized_id = str(ID)
                    except Exception:
                        pass
                cv2.putText(im, self.recognized_name, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                
        elif self.mode == "register":
            for (x, y, w, h) in faces:
                cv2.rectangle(im, (x, y), (x + w, y + h), (0, 0, 255), 2)
                self.sampleNum += 1
                img_path = f"TrainingImage\\ {self.reg_name}.{self.serial_for_registration}.{self.reg_id}.{self.sampleNum}.jpg"
                try:
                    cv2.imwrite(img_path, gray[y:y + h, x:x + w])
                except Exception:
                    pass
                cv2.putText(im, f"Capturing: {self.sampleNum}/100", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            
            if self.sampleNum >= 100:
                row = [self.serial_for_registration, '', self.reg_id, '', self.reg_name]
                columns = ['SERIAL NO.', '', 'ID', '', 'NAME']
                exists = os.path.isfile("StudentDetails\\StudentDetails.csv")
                with open('StudentDetails\\StudentDetails.csv', 'a+', newline='') as csvFile:
                    writer = csv.writer(csvFile)
                    if not exists:
                        writer.writerow(columns)
                    writer.writerow(row)
                self.mode = "register_done"
                
        ret, jpeg = cv2.imencode('.jpg', im)
        return jpeg.tobytes()

camera = None

def get_camera():
    global camera
    if camera is None:
        camera = VideoCamera()
    elif not camera.video.isOpened():
        camera.video = cv2.VideoCapture(0)
    return camera

def gen(cam):
    while True:
        frame = cam.get_frame()
        if frame is not None:
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')
        else:
            time.sleep(0.1)

######################### FLASK ROUTES #########################

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(gen(get_camera()), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/set_mode', methods=['POST'])
def set_mode():
    data = request.json
    mode = data.get('mode')
    cam = get_camera()
    
    if mode == "register":
        cam.reg_id = data.get('id', '')
        cam.reg_name = data.get('name', '')
        if not cam.reg_id or not cam.reg_name:
            return jsonify({'status': 'error', 'message': 'Missing ID or Name'})
        
        # Calculate serial
        cam.serial_for_registration = 0
        if os.path.isfile("StudentDetails\\StudentDetails.csv"):
            with open("StudentDetails\\StudentDetails.csv", 'r') as csvFile1:
                res = sum(1 for _ in csvFile1)
            cam.serial_for_registration = res // 2
        else:
            cam.serial_for_registration = 1
            
        cam.sampleNum = 0
        cam.mode = 'register'
        return jsonify({'status': 'success', 'message': 'Started registration capture!'})
        
    elif mode == "attendance":
        cam.load_data()
        cam.mode = 'attendance'
        return jsonify({'status': 'success', 'message': 'Started attendance scanner!'})
        
    else:
        if cam is not None and cam.video.isOpened():
            cam.video.release()
        cam.mode = None
        return jsonify({'status': 'success'})

@app.route('/api/status', methods=['GET'])
def get_status():
    cam = get_camera()
    return jsonify({
        'mode': cam.mode,
        'sampleNum': cam.sampleNum,
        'recognized_name': cam.recognized_name
    })

@app.route('/api/mark_attendance', methods=['POST'])
def mark_attendance():
    cam = get_camera()
    
    if cam.mode != "attendance":
        return jsonify({'status': 'error', 'message': 'Scanner is not active.'})
    if cam.recognized_id is None or cam.recognized_name is None or cam.recognized_name == "Unknown":
        return jsonify({'status': 'error', 'message': 'Look at the camera clearly until your name appears.'})
        
    ts = time.time()
    date = datetime.datetime.fromtimestamp(ts).strftime('%d-%m-%Y')
    timeStamp = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
    csv_filename = "Attendance\\Attendance_" + date + ".csv"
    exists = os.path.isfile(csv_filename)
    col_names = ['Id', 'Name', 'Date', 'Time']
    
    with open(csv_filename, 'a+', newline='') as csvFile1:
        writer = csv.writer(csvFile1)
        if not exists:
            writer.writerow(col_names)
        attendance = [str(cam.recognized_id), str(cam.recognized_name), str(date), str(timeStamp)]
        writer.writerow(attendance)
        
    speak(f"Attendance verified for {cam.recognized_name}")
    return jsonify({'status': 'success', 'message': f'Attendance safely logged for {cam.recognized_name}!'})

@app.route('/api/get_attendance', methods=['GET'])
def get_attendance():
    ts = time.time()
    date = datetime.datetime.fromtimestamp(ts).strftime('%d-%m-%Y')
    csv_filename = "Attendance\\Attendance_" + date + ".csv"
    
    data = []
    if os.path.isfile(csv_filename):
        with open(csv_filename, 'r', newline='') as f:
            reader = csv.reader(f)
            headers = next(reader, None)
            for row in reader:
                if len(row) >= 4:
                    data.append({
                        'id': row[0],
                        'name': row[1],
                        'date': row[2],
                        'time': row[3]
                    })
    # Reverse so newest is on top
    data.reverse()
    return jsonify({'status': 'success', 'data': data})

@app.route('/api/train', methods=['POST'])
def train_model():
    password = request.json.get('password')
    # Use password logic if needed, skipping for brevity to always allow train:
    recognizer = cv2.face_LBPHFaceRecognizer.create()
    path = "TrainingImage"
    imagePaths = [os.path.join(path, f) for f in os.listdir(path)]
    faces = []
    Ids = []
    for imagePath in imagePaths:
        from PIL import Image
        pilImage = Image.open(imagePath).convert('L')
        imageNp = np.array(pilImage, 'uint8')
        ID = int(os.path.split(imagePath)[-1].split(".")[1])
        faces.append(imageNp)
        Ids.append(ID)
    try:
        recognizer.train(faces, np.array(Ids))
        recognizer.save("TrainingImageLabel\\Trainner.yml")
        get_camera().load_data()  # Reload active data into memory!
        speak("System training complete and saved.")
        return jsonify({'status': 'success', 'message': 'Profile trained and saved successfully!'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Failed: {str(e)}'})

@app.route('/api/export', methods=['GET'])
def export_excel():
    ts = time.time()
    date = datetime.datetime.fromtimestamp(ts).strftime('%d-%m-%Y')
    csv_filename = "Attendance\\Attendance_" + date + ".csv"
    
    if os.path.isfile(csv_filename):
        try:
            df_export = pd.read_csv(csv_filename)
            excel_filename = "Attendance\\Exported_Report_" + date + ".xlsx"
            df_export.to_excel(excel_filename, index=False)
            speak("Excel document successfully downloaded.")
            return jsonify({'status': 'success', 'message': f'Exported to {excel_filename}'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)})
    else:
        return jsonify({'status': 'error', 'message': 'No data for today found.'})


if __name__ == '__main__':
    # Start the robust Flask server
    app.run(host='127.0.0.1', port=5000, debug=False, threaded=True)
