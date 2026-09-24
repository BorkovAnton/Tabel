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
    lunch_minutes = Column(Integer, default=60)
    is_day_off = Column(Boolean, default=False)  # Выходной день
    
    # Связь с родителем
    schedule = relationship("WorkSchedule", back_populates="days")