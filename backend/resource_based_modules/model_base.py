"""Shared models and mixins for the Dispatch application."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, event, ForeignKey
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import relationship


# SQLAlchemy Mixins


class ProjectMixin:
    """Project mixin for adding project relationships to models."""

    @declared_attr
    def project_id(cls):  # noqa
        """Returns the project_id column."""
        return Column(Integer, ForeignKey("project.id", ondelete="CASCADE"))

    @declared_attr
    def project(cls):
        """Returns the project relationship."""
        return relationship("Project")


class TimeStampMixin:
    """Timestamping mixin for created_at and updated_at fields."""

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_at._creation_order = 9998
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at._creation_order = 9998

    @staticmethod
    def _updated_at(mapper, connection, target):
        """Updates the updated_at field to the current UTC time."""
        target.updated_at = datetime.now(timezone.utc)

    @classmethod
    def __declare_last__(cls):
        """Registers the before_update event to update the updated_at field."""
        event.listen(cls, "before_update", cls._updated_at)


class ResourceMixin(TimeStampMixin):
    """Resource mixin for resource-related fields."""

    resource_type = Column(String)
    resource_id = Column(String)
    weblink = Column(String)
