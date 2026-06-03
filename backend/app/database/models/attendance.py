from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.database.models.student import Student


class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (
        Index("ix_attendance_student_recognized", "student_id", "recognized_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Links to the attendance session that produced this record. Nullable so
    # pre-academic-structure records remain valid.
    session_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("attendance_sessions.id"), index=True, nullable=True
    )
    recognized_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="present")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Lazy relationship so attendance responses can embed student identity
    # without callers manually joining. Read-only — attendance never mutates
    # student rows.
    student: Mapped["Student"] = relationship("Student", lazy="joined")
