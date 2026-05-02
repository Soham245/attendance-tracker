import os
import shutil
import pandas as pd
from config import IMAGES_DIR, ATTENDANCE_CSV
from train_model import main as retrain_model

def list_students():
    if not os.path.exists(IMAGES_DIR):
        print("No registered students found.")
        return []
    folders = [
        f for f in os.listdir(IMAGES_DIR)
        if os.path.isdir(os.path.join(IMAGES_DIR, f))
    ]
    if not folders:
        print("No registered students found.")
        return []
    print("\nRegistered Students:")
    for i, folder in enumerate(folders, start=1):
        print(f"{i}. {folder}")

    return folders

def delete_attendance_for_student(folder_name):
    if not os.path.exists(ATTENDANCE_CSV):
        print("Attendance file not found. Skipping attendance deletion.")
        return

    if "_" in folder_name:
        student_id = folder_name.split("_", 1)[0].strip()
    else:
        student_id = folder_name.strip()

    df = pd.read_csv(ATTENDANCE_CSV, dtype=str)
    if "student_id" not in df.columns:
        print("No 'student_id' column in attendance file. Skipping.")
        return

    df["student_id"] = df["student_id"].astype(str).str.strip()
    before = len(df)
    df_new = df[df["student_id"] != student_id]
    after = len(df_new)

    if before == after:
        print(f"No attendance records found for student ID {student_id}.")
    else:
        df_new.to_csv(ATTENDANCE_CSV, index=False)
        print(f"Deleted {before - after} attendance record(s) for student ID {student_id}.")

def main():
    students = list_students()
    if not students:
        return

    choice = input("\nEnter number of student to delete (or press Enter to cancel): ").strip()
    if not choice:
        print("Cancelled.")
        return

    if not choice.isdigit() or int(choice) < 1 or int(choice) > len(students):
        print("Invalid selection.")
        return

    folder_to_delete = students[int(choice) - 1]
    full_path = os.path.join(IMAGES_DIR, folder_to_delete)
    confirm = input(f"\nDelete face data for {folder_to_delete}? (y/n): ").strip().lower()
    if confirm != "y":
        print("Cancelled.")
        return

    if os.path.exists(full_path):
        shutil.rmtree(full_path)
        print(f"\nDeleted folder: {folder_to_delete}")
    else:
        print("Folder not found, nothing to delete.")

    print("\nRe-training model…")
    retrain_model()

    extra = input("\nAlso delete this student's attendance records from CSV? (y/n): ").strip().lower()
    if extra == "y":
        delete_attendance_for_student(folder_to_delete)
    else:
        print("Kept attendance records for this student.")

    print("\nDone.")

if __name__ == "__main__":
    main()
