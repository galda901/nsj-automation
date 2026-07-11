from datetime import datetime

from sqlmodel import Field, SQLModel, UniqueConstraint

from recruitment.models.candidate import now_utc
from recruitment.utils.ids import new_id


class EmbeddingRecord(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("owner_type", "owner_id", "source_type", "content_hash"),
    )

    id: str = Field(default_factory=lambda: new_id("emb"), primary_key=True)
    owner_type: str = Field(index=True)
    owner_id: str = Field(index=True)
    source_type: str = Field(index=True)
    content_hash: str = Field(index=True)
    embedding_model: str
    dimensions: int
    embedding_json: str
    preview_text: str | None = None
    created_at: datetime = Field(default_factory=now_utc)
