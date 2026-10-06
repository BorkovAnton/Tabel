from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Document(Base):
    """«Документы и приказы»: события сотрудника с датами для автозаполнения табеля.

    При «Заполнить по графику» активные документы имеют приоритет над графиком
    работы: дни, попадающие в период [start_date, end_date], заполняются полем
    code (например «О» — отпуск, «К» — командировка, «Б» — больничный).
    """
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )

    doc_type: Mapped[str] = mapped_column(String(50), nullable=False)   # vacation/business_trip/sick/other
    title: Mapped[str] = mapped_column(String(255), default="")         # произвольное название/комментарий
    doc_number: Mapped[str] = mapped_column(String(100), default="")    # номер приказа/больничного
    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    # Код справочника «Коды часов», которым автозаполнение отметит дни события
    code: Mapped[str] = mapped_column(String(10), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[date] = mapped_column(Date, default=date.today)

    employee: Mapped["Employee"] = relationship("Employee")
