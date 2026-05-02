import os
import pandas as pd
from datetime import date
from config import ATTENDANCE_CSV

def load_attendance():
    if not os.path.exists(ATTENDANCE_CSV):
        print("No attendance file found.")
        return None
    return pd.read_csv(ATTENDANCE_CSV)

def main():
    df = load_attendance()
    if df is None or df.empty:
        print("No attendance records available.")
        return
    user_input = input("Enter date (YYYY-MM-DD) or press Enter for today: ").strip()
    if user_input:
        filter_date = user_input
    else:
        filter_date = date.today().isoformat()
    day_records = df[df["date"] == filter_date]
    if day_records.empty:
        print(f"No records found for {filter_date}.")
        return
    print(f"Attendance for {filter_date}:")
    grouped = day_records.groupby(["student_id", "student_name"]).size().reset_index(name="entries")
    for _, row in grouped.iterrows():
        print(f"{row['student_id']} - {row['student_name']} (entries: {row['entries']})")

if __name__ == "__main__":
    main()
