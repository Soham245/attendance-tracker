import os
import cv2
import numpy as np
import pickle
from config import IMAGES_DIR, MODEL_PATH, LABELS_PATH

def load_training_data():
    faces = []
    labels = []
    label_to_student = {}
    current_label = 0

    for dirname in sorted(os.listdir(IMAGES_DIR)):
        student_dir = os.path.join(IMAGES_DIR, dirname)
        if not os.path.isdir(student_dir):
            continue

        label = current_label
        label_to_student[label] = dirname
        current_label += 1

        for filename in os.listdir(student_dir):
            filepath = os.path.join(student_dir, filename)
            img = cv2.imread(filepath, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            faces.append(img)
            labels.append(label)

    return faces, labels, label_to_student

def main():
    faces, labels, label_to_student = load_training_data()
    if len(faces) == 0:
        print("No training images found. Register at least one student first.")
        return
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train(faces, np.array(labels))
    recognizer.write(MODEL_PATH)
    with open(LABELS_PATH, "wb") as f:
        pickle.dump(label_to_student, f)
    print("Training complete.")
    print(f"Model saved to: {MODEL_PATH}")
    print(f"Labels saved to: {LABELS_PATH}")

if __name__ == "__main__":
    main()
