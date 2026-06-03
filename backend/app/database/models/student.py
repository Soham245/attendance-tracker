from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.database.models.academic_class import AcademicClass


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    roll_number: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, nullable=False
    )
    department: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(
        String(255), unique=True, index=True, nullable=True
    )
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # Academic class assignment — nullable so existing students remain valid.
    # Set to NULL when a student is graduated or deactivated.
    class_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("academic_classes.id"), index=True, nullable=True
    )

    # Relative path under settings.STORAGE_DIR; absolute path resolved by storage layer.
    dataset_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Flipped by the dataset service when images are added/removed; cleared by
    # the training service after a successful train.
    training_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # ---- Lifecycle fields (migration 0007) ---------------------------------

    # "active" | "graduated" | "inactive"
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="active", server_default="active",
        index=True,
    )

    # When the student graduated (NULL for active / inactive students).
    graduated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Preserves the student's last class before graduation / deactivation.
    # NULL for active students.
    last_class_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("academic_classes.id"), index=True, nullable=True
    )

    # Groups batch lifecycle operations (e.g. class-wide graduation) so they
    # can be reversed atomically. NULL for active students.
    lifecycle_batch_id: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, index=True
    )

    # ---- Relationships ------------------------------------------------------

    # Lazy relationship for easy access to the class details.
    academic_class: Mapped[Optional["AcademicClass"]] = relationship(
        "AcademicClass", lazy="joined", foreign_keys=[class_id]
    )

    last_class: Mapped[Optional["AcademicClass"]] = relationship(
        "AcademicClass", lazy="joined", foreign_keys=[last_class_id]
    )
