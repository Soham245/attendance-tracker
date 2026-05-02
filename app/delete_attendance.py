import os
import pandas as pd
from datetime import date
from config import ATTENDANCE_CSV

def load_attendance():
    if not os.path.exists(ATTENDANCE_CSV):
        print("No attendance file found.")
        return None
    return pd.read_csv(ATTENDANCE_CSV)

def save_attendance(df):
    df.to_csv(ATTENDANCE_CSV, index=False)

def main():
    df = load_attendance()
    if df is None or df.empty:
        print("No attendance records available.")
        return

    user_input = input("Enter date to delete (YYYY-MM-DD) or press Enter for today: ").strip()
    if user_input:
        target_date = user_input
    else:
        target_date = date.today().isoformat()

    day_records = df[df["date"] == target_date]
    if day_records.empty:
        print(f"No records found for {target_date}.")
        return

    print(f"Records for {target_date}:")
    grouped = day_records.groupby(["student_id", "student_name"]).size().reset_index(name="entries")
    for _, row in grouped.iterrows():
        print(f"{row['student_id']} - {row['student_name']} (entries: {row['entries']})")

    confirm = input(f"\nDelete ALL records for {target_date}? (y/n): ").strip().lower()
    if confirm != "y":
        print("No changes made.")
        return

    df_new = df[df["date"] != target_date]
    save_attendance(df_new)
    print(f"All attendance records for {target_date} have been deleted.")

if __name__ == "__main__":
    main()
