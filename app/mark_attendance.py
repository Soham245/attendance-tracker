import cv2
import os
import numpy as np
import pandas as pd
import pickle
from datetime import datetime, date
from config import ATTENDANCE_CSV, MODEL_PATH, LABELS_PATH

def load_label_map():
    if not os.path.exists(LABELS_PATH):
        print("Label file not found. Run train_model.py first.")
        return None
    with open(LABELS_PATH, "rb") as f:
        return pickle.load(f)

def load_attendance():
    if not os.path.exists(ATTENDANCE_CSV):
        df = pd.DataFrame(columns=["date", "time", "student_id", "student_name"])
        df.to_csv(ATTENDANCE_CSV, index=False)
        return df
    return pd.read_csv(ATTENDANCE_CSV)

def save_attendance(df):
    df.to_csv(ATTENDANCE_CSV, index=False)

def already_marked(df, today_str, student_id):
    records = df[(df["date"] == today_str) & (df["student_id"] == student_id)]
    return not records.empty

def mark_attendance(student_id, student_name):
    df = load_attendance()
    today_str = date.today().isoformat()
    now_time = datetime.now().strftime("%H:%M:%S")
    if already_marked(df, today_str, student_id):
        return
    new_row = {"date": today_str, "time": now_time, "student_id": student_id, "student_name": student_name}
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    save_attendance(df)
    print(f"Attendance marked for {student_name} ({student_id}) at {now_time}")

def main():
    if not os.path.exists(MODEL_PATH):
        print("Model file not found. Run train_model.py or register_student.py first.")
        return

    label_to_student = load_label_map()
    if label_to_student is None:
        return

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(MODEL_PATH)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Could not open webcam.")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    marked_session = set()
    print("Camera started. Press 'q' to quit after taking attendance.")

    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces_rects = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)

        for (x, y, w, h) in faces_rects:
            face_roi = gray[y:y + h, x:x + w]
            face_roi = cv2.resize(face_roi, (200, 200))

            label, confidence = recognizer.predict(face_roi)

            if confidence < 80:
                student_folder = label_to_student.get(label, "")
                if "_" in student_folder:
                    student_id, student_name = student_folder.split("_", 1)
                else:
                    student_id = student_folder
                    student_name = student_folder

                name_to_display = f"{student_name} ({student_id})"

                if student_id not in marked_session:
                    mark_attendance(student_id, student_name)
                    marked_session.add(student_id)

                color = (0, 255, 0)
            else:
                name_to_display = "Unknown"
                color = (0, 0, 255)

            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            cv2.putText(frame, name_to_display, (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        cv2.imshow("Attendance", frame)
        key = cv2.waitKey(1)
        if key == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
