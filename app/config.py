import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
IMAGES_DIR = os.path.join(DATA_DIR, "images")
ENCODINGS_PATH = os.path.join(DATA_DIR, "encodings.pkl")
ATTENDANCE_CSV = os.path.join(DATA_DIR, "attendance.csv")
MODEL_PATH = os.path.join(DATA_DIR, "trainer.yml")
LABELS_PATH = os.path.join(DATA_DIR, "labels.pkl")

os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
