"""Application-wide constants."""
from enum import Enum


# API tags
API_TAG_HEALTH = "Health"
API_TAG_AUTH = "Authentication"
API_TAG_STUDENTS = "Students"
API_TAG_ATTENDANCE = "Attendance"


class UserRole(str, Enum):
    ADMIN = "admin"
    FACULTY = "faculty"


# ---------------------------------------------------------------------------
# Program durations (years) — used for auto-promotion and final-year detection
# ---------------------------------------------------------------------------

PROGRAM_DURATIONS: dict[str, int] = {
    "MCA": 2,
    "BCA": 3,
    "BTECH": 4,
    "BTech": 4,
    "B.TECH": 4,
    "B. TECH": 4,
    "B.Tech": 4,
    "MTECH": 2,
    "MTech": 2,
    "M.TECH": 2,
    "M. TECH": 2,
    "M.Tech": 2,
    "BSC": 3,
    "B.SC": 3,
    "B. SC": 3,
    "MSC": 2,
    "M.SC": 2,
    "M. SC": 2,
    "MBA": 2,
    "BBA": 3,
    "PHD": 5,
}
DEFAULT_PROGRAM_DURATION = 4


def get_program_duration(major: str) -> int:
    """Return the duration for a program, case-insensitive."""
    return PROGRAM_DURATIONS.get(major, PROGRAM_DURATIONS.get(major.upper(), DEFAULT_PROGRAM_DURATION))
