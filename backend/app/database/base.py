"""SQLAlchemy declarative base.

Import all model modules here (once they exist) so that Base.metadata is
aware of every table at startup / migration time.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Model imports go here as they are introduced, e.g.:
# from app.database.models.user import User  # noqa: F401
