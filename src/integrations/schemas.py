"""SIS integration schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from src.schemas import BaseSchema


class SISConnectRequest(BaseSchema):
    group_id: UUID
    provider: str = Field(pattern="^(clever|classlink|powerschool|canvas)$")
    access_token: str = Field(min_length=1)
    config: dict | None = None


class SISConnectionResponse(BaseSchema):
    id: UUID
    group_id: UUID
    provider: str
    status: str
    last_synced: datetime | None
    created_at: datetime


class SISSyncResponse(BaseSchema):
    connection_id: UUID
    members_created: int
    members_updated: int
    members_deactivated: int
