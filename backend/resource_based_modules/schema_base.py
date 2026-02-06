from datetime import datetime
from typing import Annotated, ClassVar

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    StringConstraints,
    field_serializer,
)

NameStr = Annotated[
    str, StringConstraints(pattern=r".*\S.*", strip_whitespace=True, min_length=3)
]
OrganizationSlug = Annotated[
    str, StringConstraints(pattern=r"^[\w]+(?:_[\w]+)*$", min_length=3)
]


# pydantic type that limits the range of primary keys
PrimaryKey = Annotated[int, Field(gt=0, lt=2147483647)]


# Pydantic models...
class SchemaBase(BaseModel):
    """Base Pydantic model with shared config for resource schemas."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        arbitrary_types_allowed=True,
        str_strip_whitespace=True,
    )

    @field_serializer("*")
    def _serialize_special(self, v, _info):
        """Serialize datetime and SecretStr for JSON output (Pydantic V2)."""
        if isinstance(v, datetime):
            return v.strftime("%Y-%m-%dT%H:%M:%S.%fZ") if v else None
        if isinstance(v, SecretStr):
            return v.get_secret_value() if v else None
        return v


class Pagination(SchemaBase):
    """Pydantic model for paginated results."""

    itemsPerPage: int
    page: int
    total: int


class PrimaryKeyModel(BaseModel):
    """Pydantic model for a primary key field."""

    id: PrimaryKey
