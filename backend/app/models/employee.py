from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Employee(Base):
    __tablename__ = 'employees'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tab_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    department_id: Mapped[int] = mapped_column(Integer, ForeignKey('departments.id'), nullable=True)
    schedule_id: Mapped[int | None] = mapped_column(Integer, ForeignKey('work_schedules.id'), nullable=True)

    # Relationships
    department: Mapped['Department'] = relationship('Department')
    schedule: Mapped['WorkSchedule'] = relationship('WorkSchedule')