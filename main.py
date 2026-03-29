############################################# IMPORTING ################################################
import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox as mess
import tkinter.simpledialog as tsd
import cv2, os, csv, numpy as np, pandas as pd
import datetime, time, threading
import pyttsx3
from PIL import Image, ImageTk

# Clean, professional bright UI
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

############################################# GLOBAL STATE ################################################

cam = None
current_mode = None  # None, 'register', 'attendance'
recognized_id = None
recognized_name = None
sampleNum = 0
serial_for_registration = 0
harcascadePath = "haarcascade_frontalface_default.xml"
detector = cv2.CascadeClassifier(harcascadePath)
df = None
recognizer_att = None

############################################# FUNCTIONS ################################################

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

def export_excel():
    ts = time.time()
    date = datetime.datetime.fromtimestamp(ts).strftime('%d-%m-%Y')
    csv_filename = "Attendance\\Attendance_" + date + ".csv"
    
    if os.path.isfile(csv_filename):
        try:
            df_export = pd.read_csv(csv_filename)
            excel_filename = "Attendance\\Exported_Report_" + date + ".xlsx"
            df_export.to_excel(excel_filename, index=False)
            mess._show(title="Export Successful", message=f"Excel file created successfully at:\n{excel_filename}")
        except Exception as e:
            mess._show(title="Export Failed", message=f"Could not convert to Excel: {e}")
    else:
        mess._show(title="No Data", message="No attendance data found for today to export.")

def assure_path_exists(path):
    dir = os.path.dirname(path)
    if not os.path.exists(dir):
        os.makedirs(dir)

def tick():
    time_string = time.strftime('%H:%M:%S')
    clock.configure(text=time_string)
    clock.after(1000, tick)

def contact():
    mess._show(title='Contact us', message="Please contact us on : 'xxxxxxxxxxxxx@gmail.com' ")

def check_haarcascadefile():
    exists = os.path.isfile("haarcascade_frontalface_default.xml")
    if not exists:
        mess._show(title='File missing', message='haarcascade_frontalface_default.xml is missing!')

def go_home():
    global current_mode, cam
    current_mode = None
    if cam is not None and cam.isOpened():
        cam.release()
    # Reset placeholder images
    reg_cam_label.configure(image=dummy_imgtk)
    att_cam_label.configure(image=dummy_imgtk)
    
    # Hide all frames, show home
    home_frame.tkraise()

def go_registration():
    reg_frame.tkraise()

def go_attendance():
    StartAttendanceScanner()
    if current_mode == 'attendance':  # Only go to frame if scanner successfully started
        att_frame.tkraise()


def psw():
    assure_path_exists("TrainingImageLabel/")
    exists1 = os.path.isfile("TrainingImageLabel\\psd.txt")
    if exists1:
        with open("TrainingImageLabel\\psd.txt", "r") as tf:
            key = tf.read()
    else:
        new_pas = tsd.askstring('Old Password not found', 'Please enter a new password below', show='*')
        if new_pas == None:
            mess._show(title='No Password Entered', message='Password not set!! Please try again')
            return
        else:
            with open("TrainingImageLabel\\psd.txt", "w") as tf:
                tf.write(new_pas)
            mess._show(title='Password Registered', message='New password was registered successfully!!')
            return
            
    password = tsd.askstring('Password', 'Enter Administrator Password', show='*')
    if (password == key):
        TrainImages()
    elif (password == None):
        pass
    else:
        mess._show(title='Wrong Password', message='You have entered wrong password')


def start_camera():
    global cam
    if cam is None or not cam.isOpened():
        check_haarcascadefile()
        cam = cv2.VideoCapture(0)
    
    # Fire up the loop
    update_camera_feed()

def StartRegistration():
    global current_mode, sampleNum, serial_for_registration
    assure_path_exists("StudentDetails/")
    assure_path_exists("TrainingImage/")
    
    Id = txt.get()
    name = txt2.get()
    if not Id or not name:
        mess._show(title="Input Error", message="Please enter ID and Name")
        return
    if not name.replace(' ', '').isalpha():
        mess._show(title="Input Error", message="Enter Correct Name")
        return

    # Determine serial
    serial_for_registration = 0
    exists = os.path.isfile("StudentDetails\\StudentDetails.csv")
    columns = ['SERIAL NO.', '', 'ID', '', 'NAME']
    if exists:
        with open("StudentDetails\\StudentDetails.csv", 'r') as csvFile1:
            reader1 = csv.reader(csvFile1)
            for _ in reader1:
                serial_for_registration += 1
        serial_for_registration = (serial_for_registration // 2)
    else:
        with open("StudentDetails\\StudentDetails.csv", 'a+', newline='') as csvFile1:
            writer = csv.writer(csvFile1)
            writer.writerow(columns)
        serial_for_registration = 1

    sampleNum = 0
    current_mode = "register"
    message1.configure(text="Images Taking... Please look at camera")
    start_camera()

def TrainImages():
    check_haarcascadefile()
    assure_path_exists("TrainingImageLabel/")
    recognizer = cv2.face_LBPHFaceRecognizer.create()
    
    path = "TrainingImage"
    imagePaths = [os.path.join(path, f) for f in os.listdir(path)]
    faces = []
    Ids = []
    for imagePath in imagePaths:
        pilImage = Image.open(imagePath).convert('L')
        imageNp = np.array(pilImage, 'uint8')
        ID = int(os.path.split(imagePath)[-1].split(".")[1])
        faces.append(imageNp)
        Ids.append(ID)
        
    try:
        recognizer.train(faces, np.array(Ids))
    except:
        mess._show(title='No Registrations', message='Please Register someone first!!!')
        return
    recognizer.save("TrainingImageLabel\\Trainner.yml")
    message1.configure(text="Profile Saved Successfully")


def StartAttendanceScanner():
    global current_mode, df, recognizer_att
    check_haarcascadefile()
    assure_path_exists("Attendance/")
    assure_path_exists("StudentDetails/")
    
    exists3 = os.path.isfile("TrainingImageLabel\\Trainner.yml")
    if not exists3:
        mess._show(title='Data Missing', message='Please Train / Save Profile first!')
        return
        
    exists1 = os.path.isfile("StudentDetails\\StudentDetails.csv")
    if exists1:
        df = pd.read_csv("StudentDetails\\StudentDetails.csv")
    else:
        mess._show(title='Details Missing', message='No student data found! Please Register first.')
        return

    recognizer_att = cv2.face_LBPHFaceRecognizer.create()
    recognizer_att.read("TrainingImageLabel\\Trainner.yml")
    
    current_mode = "attendance"
    start_camera()

def MarkAttendanceManually():
    global recognized_id, recognized_name
    
    if recognized_id is None or recognized_name is None or recognized_name == "Unknown":
        mess._show(title='Recognition Failed', message='Look directly at the camera. Wait until your name appears on your face, then click the button!')
        return
        
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
        attendance = [str(recognized_id), str(recognized_name), str(date), str(timeStamp)]
        writer.writerow(attendance)
        
    speak(f"Attendance verified for {recognized_name}")
    mess._show(title="Success", message=f"Attendance confidently logged for {recognized_name}!")
    
    # Reload Treeview
    for k in tv.get_children():
        tv.delete(k)
        
    with open(csv_filename, 'r', newline='') as csvFile1:
        reader1 = csv.reader(csvFile1)
        next(reader1, None)
        for lines in reader1:
            if len(lines) >= 4:
                tv.insert('', 0, text=lines[0], values=(lines[1], lines[2], lines[3]))


def update_camera_feed():
    global cam, current_mode, sampleNum, recognized_id, recognized_name
    
    if current_mode is None or cam is None or not cam.isOpened():
        # If camera mode was turned off, safely exit the async loop!
        return

    ret, im = cam.read()
    if not ret:
        window.after(15, update_camera_feed)
        return

    gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    faces = detector.detectMultiScale(gray, 1.3, 5)

    if current_mode == "attendance":
        recognized_name = "Unknown"
        recognized_id = None
        for (x, y, w, h) in faces:
            cv2.rectangle(im, (x, y), (x + w, y + h), (0, 200, 0), 2)
            serial, conf = recognizer_att.predict(gray[y:y + h, x:x + w])
            if (conf < 50):
                try:
                    aa = df.loc[df['SERIAL NO.'] == serial]['NAME'].values[0]
                    ID = df.loc[df['SERIAL NO.'] == serial]['ID'].values[0]
                    recognized_name = str(aa)
                    recognized_id = str(ID)
                except:
                    pass
            cv2.putText(im, recognized_name, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    elif current_mode == "register":
        for (x, y, w, h) in faces:
            cv2.rectangle(im, (x, y), (x + w, y + h), (0, 0, 255), 2)
            sampleNum += 1
            Id = txt.get()
            name = txt2.get()
            cv2.imwrite("TrainingImage\\ " + name + "." + str(serial_for_registration) + "." + Id + '.' + str(sampleNum) + ".jpg", gray[y:y + h, x:x + w])
            cv2.putText(im, f"Capturing: {sampleNum}/100", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            
        if sampleNum >= 100:
            message1.configure(text=f"Images Taken for ID : {txt.get()}")
            row = [serial_for_registration, '', txt.get(), '', txt2.get()]
            with open('StudentDetails\\StudentDetails.csv', 'a+', newline='') as csvFile:
                writer = csv.writer(csvFile)
                writer.writerow(row)
            txt.delete(0, 'end')
            txt2.delete(0, 'end')
            # Turn off camera directly
            cam.release()
            current_mode = None
            reg_cam_label.configure(image=dummy_imgtk)
            return

    # Process and route the image to the correct screen's label
    cv2image = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
    img_pil = Image.fromarray(cv2image)
    img_pil = img_pil.resize((480, 360))
    imgtk = ImageTk.PhotoImage(image=img_pil)
    
    if current_mode == "attendance":
        att_cam_label.imgtk = imgtk
        att_cam_label.configure(image=imgtk)
    elif current_mode == "register":
        reg_cam_label.imgtk = imgtk
        reg_cam_label.configure(image=imgtk)
    
    # re-trigger loop to keep streaming
    if current_mode is not None:
        window.after(15, update_camera_feed)

def load_initial_attendance():
    ts = time.time()
    date = datetime.datetime.fromtimestamp(ts).strftime('%d-%m-%Y')
    csv_filename = "Attendance\\Attendance_" + date + ".csv"
    if os.path.isfile(csv_filename):
        with open(csv_filename, 'r', newline='') as csvFile1:
            reader1 = csv.reader(csvFile1)
            next(reader1, None)
            for lines in reader1:
                if len(lines) >= 4:
                    tv.insert('', 0, text=lines[0], values=(lines[1], lines[2], lines[3]))


def on_closing():
    if cam is not None and cam.isOpened():
        cam.release()
    window.destroy()

######################################## GUI FRONT-END BUILDER ###########################################

window = ctk.CTk()
window.geometry("1100x700")
window.resizable(True, True)
window.title("Smart Attendance System V3")
window.protocol("WM_DELETE_WINDOW", on_closing)

# Dummy Image for cameras when off (to preserve sizing perfectly)
dummy_img = Image.new('RGB', (480, 360), color = 'black')
dummy_imgtk = ImageTk.PhotoImage(dummy_img)

################## HEADER ##################
header_frame = ctk.CTkFrame(window, fg_color="transparent")
header_frame.pack(fill="x", pady=10)

message3 = ctk.CTkLabel(header_frame, text="Smart Attendance System", font=('Arial', 32, 'bold'), text_color="#1f6aa5")
message3.pack()

clock = ctk.CTkLabel(header_frame, font=('Arial', 18, 'bold'), text_color="#555")
clock.pack()
tick()

################## MULTI-PAGE CONTAINER ##################
# By letting the frames overlap on row 0 column 0, we can use `tkraise()` to swap screens instantly.
main_container = ctk.CTkFrame(window, fg_color="transparent")
main_container.pack(fill="both", expand=True, padx=20, pady=10)
main_container.grid_rowconfigure(0, weight=1)
main_container.grid_columnconfigure(0, weight=1)

# Initialize Pages
home_frame = ctk.CTkFrame(main_container, fg_color="transparent")
reg_frame = ctk.CTkFrame(main_container, fg_color="transparent")
att_frame = ctk.CTkFrame(main_container, fg_color="transparent")

for frame in (home_frame, reg_frame, att_frame):
    frame.grid(row=0, column=0, sticky="nsew")

################## PAGE 1: HOME DASHBOARD ##################
welcome_lbl = ctk.CTkLabel(home_frame, text="Select Your Operation", font=('Arial', 28, 'bold'), text_color="#333")
welcome_lbl.pack(pady=(50, 40))

btn_go_reg = ctk.CTkButton(home_frame, text="1. Register New Student", font=('Arial', 24, 'bold'), width=450, height=80, fg_color="#1f6aa5", hover_color="#144870", command=go_registration)
btn_go_reg.pack(pady=15)

btn_go_att = ctk.CTkButton(home_frame, text="2. Mark Attendance (Existing)", font=('Arial', 24, 'bold'), width=450, height=80, fg_color="#3ece48", hover_color="#2b9a34", text_color="black", command=go_attendance)
btn_go_att.pack(pady=15)


################## PAGE 2: NEW REGISTRATION ##################
btn_back_reg = ctk.CTkButton(reg_frame, text="← Back to Home", font=('Arial', 14, 'bold'), width=150, fg_color="#ea2a2a", hover_color="#c21c1c", command=go_home)
btn_back_reg.pack(anchor="nw", pady=(0, 20))

reg_content = ctk.CTkFrame(reg_frame, fg_color="transparent")
reg_content.pack(fill="both", expand=True)

# Registration Details (Left)
reg_details = ctk.CTkFrame(reg_content, corner_radius=15, fg_color="#fff")
reg_details.pack(side="left", fill="both", expand=True, padx=10)

ctk.CTkLabel(reg_details, text="Student Details", font=('Arial', 22, 'bold'), text_color="#3ece48").pack(pady=20)

input_frame = ctk.CTkFrame(reg_details, fg_color="transparent")
input_frame.pack(pady=20)

ctk.CTkLabel(input_frame, text="Enter ID:", font=('Arial', 16, 'bold')).grid(row=0, column=0, padx=10, pady=10, sticky="e")
txt = ctk.CTkEntry(input_frame, width=200, font=('Arial', 14))
txt.grid(row=0, column=1, pady=10)

ctk.CTkLabel(input_frame, text="Enter Name:", font=('Arial', 16, 'bold')).grid(row=1, column=0, padx=10, pady=10, sticky="e")
txt2 = ctk.CTkEntry(input_frame, width=200, font=('Arial', 14))
txt2.grid(row=1, column=1, pady=10)

btn_take_img = ctk.CTkButton(reg_details, text="1. Take Images (Start Camera)", command=StartRegistration, font=('Arial', 18, 'bold'), width=300, height=50)
btn_take_img.pack(pady=10)

btn_train = ctk.CTkButton(reg_details, text="2. Save Profile & Train System", command=psw, font=('Arial', 18, 'bold'), width=300, height=50, fg_color="#e6b800", hover_color="#cc9f00", text_color="black")
btn_train.pack(pady=10)

message1 = ctk.CTkLabel(reg_details, text="Status: Ready", font=('Arial', 18, 'bold'), text_color="#ea2a2a")
message1.pack(pady=20)

# Registration Camera (Right)
reg_cam_label = tk.Label(reg_content, bg="black", image=dummy_imgtk)
reg_cam_label.pack(side="right", padx=10, pady=10)


################## PAGE 3: ATTENDANCE SCANNER ##################
btn_back_att = ctk.CTkButton(att_frame, text="← Back to Home", font=('Arial', 14, 'bold'), width=150, fg_color="#ea2a2a", hover_color="#c21c1c", command=go_home)
btn_back_att.pack(anchor="nw", pady=(0, 20))

att_content = ctk.CTkFrame(att_frame, fg_color="transparent")
att_content.pack(fill="both", expand=True)

# Attendance Camera (Left)
att_left = ctk.CTkFrame(att_content, fg_color="transparent")
att_left.pack(side="left", fill="y", padx=10)

att_cam_label = tk.Label(att_left, bg="black", image=dummy_imgtk)
att_cam_label.pack(pady=10)

btn_mark = ctk.CTkButton(att_left, text="MARK ATTENDANCE ✔", font=('Arial', 24, 'bold'), fg_color="#3ece48", hover_color="#2b9a34", text_color="black", height=70, width=480, command=MarkAttendanceManually)
btn_mark.pack(pady=20)

# Attendance Table (Right)
att_right = ctk.CTkFrame(att_content, fg_color="#fff", corner_radius=15)
att_right.pack(side="right", fill="both", expand=True, padx=10)

ctk.CTkLabel(att_right, text="Today's Attendance", font=('Arial', 22, 'bold'), text_color="#1f6aa5").pack(pady=10)

style = ttk.Style()
style.theme_use("default")
style.configure("Treeview", background="#f4f4f4", foreground="black", rowheight=30, fieldbackground="#f4f4f4", borderwidth=0, font=('Arial', 12))
style.map('Treeview', background=[('selected', '#1f6aa5')])
style.configure("Treeview.Heading", background="#1f6aa5", foreground="white", relief="flat", font=('Arial', 14, 'bold'))
style.map("Treeview.Heading", background=[('active', '#144870')])

tv = ttk.Treeview(att_right, columns=('name','date','time'))
tv.column('#0', width=60, anchor='center')
tv.column('name', width=150, anchor='center')
tv.column('date', width=100, anchor='center')
tv.column('time', width=100, anchor='center')
tv.pack(padx=20, pady=10, fill="both", expand=True)

tv.heading('#0', text='ID')
tv.heading('name', text='NAME')
tv.heading('date', text='DATE')
tv.heading('time', text='TIME')

btn_export = ctk.CTkButton(att_right, text="📊 Download Excel Report", font=('Arial', 18, 'bold'), fg_color="#1f6aa5", hover_color="#144870", height=45, command=export_excel)
btn_export.pack(pady=15)

load_initial_attendance()

# Start on the Home Page
home_frame.tkraise()

if __name__ == "__main__":
    window.mainloop()
