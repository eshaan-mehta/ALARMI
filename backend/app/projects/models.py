from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base

if TYPE_CHECKING:
    from ..designs.models import Design


class Project(Base):
    __tablename__ = "projects"

    project_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    location: Mapped[str] = mapped_column(String, nullable=False)
    created_time: Mapped[str] = mapped_column(String, nullable=False)

    designs: Mapped[list["Design"]] = relationship(
        "Design", back_populates="project", cascade="all, delete-orphan"
    )
