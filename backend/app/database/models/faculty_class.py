from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class FacultyClass(Base):
    """Many-to-many join: which faculty members teach which classes."""

    __tablename__ = "faculty_classes"
    __table_args__ = (
        UniqueConstraint("user_id", "class_id", name="uq_faculty_class"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    class_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("academic_classes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
