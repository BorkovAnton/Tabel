from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Department(Base):
    __tablename__ = 'departments'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(Integer, ForeignKey('departments.id'), nullable=True)

    # Relationships
    children: Mapped[list['Department']] = relationship('Department', back_populates='parent')
    parent: Mapped['Department'] = relationship('Department', remote_side=[id], back_populates='children')