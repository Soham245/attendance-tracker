"""Import every model here so Base.metadata sees them at startup."""
from app.database.models.academic_class import AcademicClass
from app.database.models.attendance import Attendance
from app.database.models.attendance_session import AttendanceSession
from app.database.models.faculty_class import FacultyClass
from app.database.models.student import Student
from app.database.models.user import User

__all__ = [
    "AcademicClass",
    "Attendance",
    "AttendanceSession",
    "FacultyClass",
    "Student",
    "User",
]
