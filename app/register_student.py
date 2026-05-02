import cv2
import os
from datetime import datetime
from config import IMAGES_DIR
from train_model import main as train_main

def capture_single_student(cap, face_cascade, student_id, student_name, num_images=10):
    folder_name = f"{student_id}_{student_name}"
    student_dir = os.path.join(IMAGES_DIR, folder_name)
    os.makedirs(student_dir, exist_ok=True)
    count = 0
    print(f"\nStarting capture for {student_name} ({student_id})")
    print("Look at the camera.")
    print("Press 'c' to capture face images, 'q' to skip this student.")

    while count < num_images:
        ret, frame = cap.read()
        if not ret:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)

        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 255, 255), 2)

        cv2.putText(frame, f"Press 'c' to capture ({count + 1}/{num_images})", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.imshow("Register Student", frame)
        key = cv2.waitKey(1)

        if key == ord("c") and len(faces) > 0:
            x, y, w, h = faces[0]
            face_roi = gray[y:y + h, x:x + w]
            face_roi = cv2.resize(face_roi, (200, 200))
            filename = f"{student_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{count}.jpg"
            filepath = os.path.join(student_dir, filename)
            cv2.imwrite(filepath, face_roi)
            count += 1
            print(f"Captured {count}/{num_images}")
        elif key == ord("q"):
            print("Skipping this student early.")
            break

    if count > 0:
        print(f"Saved {count} images for {student_name} ({student_id}).")
        return True
    else:
        print(f"No images saved for {student_name} ({student_id}).")
        return False

def main():
    print("Opening camera...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Could not open webcam.")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    any_saved = False
    try:
        while True:
            student_id = input("\nEnter student ID (or press Enter to stop): ").strip()
            if not student_id:
                print("Stopping registration.")
                break
            student_name = input("Enter student name: ").strip()
            if not student_name:
                print("Name is required. Skipping.")
                continue
            saved = capture_single_student(cap, face_cascade, student_id, student_name, num_images=10)
            if saved:
                any_saved = True
            more = input("\nRegister another student? (y/n): ").strip().lower()
            if more != "y":
                print("Finished student registrations.")
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()

    if any_saved:
        print("\nTraining model on all registered faces...")
        train_main()
        print("Training complete.")
    else:
        print("No images captured. Skipping training.")

if __name__ == "__main__":
    main()
