from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Tabel(Base):
    """Табель учёта рабочего времени за месяц."""
    __tablename__ = "tabels"
    __table_args__ = (
        UniqueConstraint("year", "month", "department_id", name="uq_tabel_period_department"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)  # 1..12
    department_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("departments.id"), nullable=True)
    responsible_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    responsible_user: Mapped["User"] = relationship("User")
    department: Mapped["Department"] = relationship("Department")
    entries: Mapped[list["TabelEntry"]] = relationship("TabelEntry", back_populates="tabel", cascade="all, delete-orphan")


class TabelEntry(Base):
    """Запись сотрудника в табеле + значения по дням месяца.

    Значения дней хранятся как строки: число часов ('8.15') или буквенный код ('В', 'О', '8н').
    """
    __tablename__ = "tabel_entries"
    __table_args__ = (
        UniqueConstraint("tabel_id", "employee_id", name="uq_tabel_entry_employee"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tabel_id: Mapped[int] = mapped_column(Integer, ForeignKey("tabels.id"), nullable=False)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)

    day_1: Mapped[str | None] = mapped_column(String(8))
    day_2: Mapped[str | None] = mapped_column(String(8))
    day_3: Mapped[str | None] = mapped_column(String(8))
    day_4: Mapped[str | None] = mapped_column(String(8))
    day_5: Mapped[str | None] = mapped_column(String(8))
    day_6: Mapped[str | None] = mapped_column(String(8))
    day_7: Mapped[str | None] = mapped_column(String(8))
    day_8: Mapped[str | None] = mapped_column(String(8))
    day_9: Mapped[str | None] = mapped_column(String(8))
    day_10: Mapped[str | None] = mapped_column(String(8))
    day_11: Mapped[str | None] = mapped_column(String(8))
    day_12: Mapped[str | None] = mapped_column(String(8))
    day_13: Mapped[str | None] = mapped_column(String(8))
    day_14: Mapped[str | None] = mapped_column(String(8))
    day_15: Mapped[str | None] = mapped_column(String(8))
    day_16: Mapped[str | None] = mapped_column(String(8))
    day_17: Mapped[str | None] = mapped_column(String(8))
    day_18: Mapped[str | None] = mapped_column(String(8))
    day_19: Mapped[str | None] = mapped_column(String(8))
    day_20: Mapped[str | None] = mapped_column(String(8))
    day_21: Mapped[str | None] = mapped_column(String(8))
    day_22: Mapped[str | None] = mapped_column(String(8))
    day_23: Mapped[str | None] = mapped_column(String(8))
    day_24: Mapped[str | None] = mapped_column(String(8))
    day_25: Mapped[str | None] = mapped_column(String(8))
    day_26: Mapped[str | None] = mapped_column(String(8))
    day_27: Mapped[str | None] = mapped_column(String(8))
    day_28: Mapped[str | None] = mapped_column(String(8))
    day_29: Mapped[str | None] = mapped_column(String(8))
    day_30: Mapped[str | None] = mapped_column(String(8))
    day_31: Mapped[str | None] = mapped_column(String(8))

    comment: Mapped[str | None] = mapped_column(Text)

    tabel: Mapped["Tabel"] = relationship("Tabel", back_populates="entries")
    employee: Mapped["Employee"] = relationship("Employee")
