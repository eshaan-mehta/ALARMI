from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from ..db import Base

if TYPE_CHECKING:
    from ..designs.models import Design


class Module(Base):
    __tablename__ = "modules"

    module_id: Mapped[str] = mapped_column(String, primary_key=True)
    design_id: Mapped[str] = mapped_column(
        ForeignKey("designs.design_id"), nullable=False, index=True
    )
    type: Mapped[str | None] = mapped_column(String, nullable=True)
    dimensions: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # {x, y, z}
    room_id: Mapped[str | None] = mapped_column(String, nullable=True)
    unit_scale: Mapped[str | None] = mapped_column(String, nullable=True)

    design: Mapped["Design"] = relationship("Design", back_populates="modules")
