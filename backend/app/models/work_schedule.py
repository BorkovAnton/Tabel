from datetime import date as _date, datetime

from sqlalchemy import Column, Integer, String, Time, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class WorkSchedule(Base):
    __tablename__ = "work_schedules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    
    # Связь с днями недели (cascade удаляет дни при удалении графика)
    days = relationship("WorkScheduleDay", back_populates="schedule", cascade="all, delete-orphan")
    
    # Связь с сотрудниками
    employees = relationship("Employee", back_populates="schedule")


class WorkScheduleDay(Base):
    __tablename__ = "work_schedule_days"

    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey("work_schedules.id", ondelete="CASCADE"), nullable=False)
    day_of_week = Column(Integer, nullable=False)  # 0=Пн, 1=Вт, ..., 6=Вс
    
    start_time = Column(Time, nullable=True)  # NULL если выходной
    end_time = Column(Time, nullable=True)
    # Конкретный промежуток времени обеда (например 12:00–13:00).
    lunch_start = Column(Time, nullable=True)
    lunch_end = Column(Time, nullable=True)
    # Старое поле сохранено для обратной совместимости: если промежуток
    # обеда не задан, используется количество минут из него.
    lunch_minutes = Column(Integer, default=60)
    is_day_off = Column(Boolean, default=False)  # Выходной день

    # Код из справочника для функции «Заполнить по графику» (например "8ч15м", "В").
    # Если пусто — автозаполнение пропускает этот день недели.
    auto_fill_code = Column(String, nullable=True)
    
    # Связь с родителем
    schedule = relationship("WorkSchedule", back_populates="days")

    @property
    def lunch_duration_minutes(self) -> int:
        """Длительность обеда в минутах.

        Если задан конкретный промежуток (lunch_start/lunch_end) — считаем
        от него; иначе — обратная совместимость со старым lunch_minutes.
        """
        if self.lunch_start and self.lunch_end:
            delta = (
                datetime.combine(_date.min, self.lunch_end)
                - datetime.combine(_date.min, self.lunch_start)
            )
            minutes = int(delta.total_seconds() / 60)
            if minutes > 0:
                return minutes
        return self.lunch_minutes or 0