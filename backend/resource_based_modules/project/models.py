from sqlalchemy import Column, Integer, String

from resource_based_modules.database.core import Base
from resource_based_modules.model_base import TimeStampMixin


class Project(Base, TimeStampMixin):
    """Project entity: id, container_name, and timestamps."""

    id = Column(Integer, primary_key=True, autoincrement=True)
    container_name = Column(String, nullable=True)
