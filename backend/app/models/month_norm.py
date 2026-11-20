from sqlalchemy import Integer, Float, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class MonthNorm(Base):
    __tablename__ = "month_norms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    norm_hours: Mapped[float] = mapped_column(Float, nullable=False)
    working_days: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint('year', 'month', name='uq_year_month'),
    )