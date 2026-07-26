from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base

if TYPE_CHECKING:
    from ..modules.models import Module
    from ..projects.models import Project


class Design(Base):
    __tablename__ = "designs"

    design_id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.project_id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    file_name: Mapped[str] = mapped_column(String, nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)  # PROCESSING|COMPLETE|ERROR
    upload_time: Mapped[str] = mapped_column(String, nullable=False)
    # Set by the processing worker when it reaches a terminal status. Server-side
    # diagnostics — not part of the DesignOut the client reads.
    processed_time: Mapped[str | None] = mapped_column(String, nullable=True)
    error: Mapped[str | None] = mapped_column(String, nullable=True)

    project: Mapped["Project"] = relationship("Project", back_populates="designs")
    modules: Mapped[list["Module"]] = relationship(
        "Module", back_populates="design", cascade="all, delete-orphan"
    )
