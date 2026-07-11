from datetime import datetime

from sqlmodel import Field, SQLModel

from recruitment.models.candidate import now_utc
from recruitment.utils.ids import new_id


class IngestionLog(SQLModel, table=True):
    id: str = Field(default_factory=lambda: new_id("ing"), primary_key=True)
    source: str = Field(index=True)
    source_label: str | None = Field(default=None, index=True)
    source_message_id: str | None = Field(default=None, index=True)
    source_attachment_id: str | None = Field(default=None, index=True)
    entity_type: str | None = Field(default=None, index=True)
    entity_id: str | None = Field(default=None, index=True)
    status: str = Field(index=True)
    detail: str | None = None
    created_at: datetime = Field(default_factory=now_utc)
