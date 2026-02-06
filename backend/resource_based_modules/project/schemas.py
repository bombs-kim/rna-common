from datetime import datetime

from resource_based_modules.schema_base import Pagination, PrimaryKey, SchemaBase


class ProjectResponse(SchemaBase):
    """Schema for project in API responses."""

    id: PrimaryKey
    container_name: str | None = None
    created_at: datetime
    updated_at: datetime


class ProjectPaginationResponse(Pagination):
    """Schema for paginated list of projects in API responses."""

    items: list[ProjectResponse]
