import hashlib
import json
import math
from collections import Counter

from sqlmodel import Session, select

from recruitment.config import get_settings
from recruitment.integrations.openai_client import create_embedding, openai_enabled
from recruitment.models.vector import EmbeddingRecord


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def deterministic_embedding(text: str, dimensions: int = 512) -> list[float]:
    counts: Counter[int] = Counter()
    for token in text.casefold().split():
        digest = hashlib.sha256(token.encode("utf-8", errors="ignore")).digest()
        counts[int.from_bytes(digest[:4], "big") % dimensions] += 1
    vector = [0.0] * dimensions
    for index, value in counts.items():
        vector[index] = float(value)
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def embedding_for_text(text: str) -> list[float]:
    settings = get_settings()
    if openai_enabled():
        try:
            return create_embedding(text)
        except Exception:
            pass
    return deterministic_embedding(text, settings.openai_embedding_dimensions)


def cosine_similarity(left: list[float], right: list[float]) -> float:
    limit = min(len(left), len(right))
    if limit == 0:
        return 0.0
    dot = sum(left[index] * right[index] for index in range(limit))
    left_norm = math.sqrt(sum(value * value for value in left[:limit])) or 1.0
    right_norm = math.sqrt(sum(value * value for value in right[:limit])) or 1.0
    return dot / (left_norm * right_norm)


def upsert_embedding(
    session: Session,
    owner_type: str,
    owner_id: str,
    source_type: str,
    text: str,
) -> EmbeddingRecord | None:
    clean = text.strip()
    if not clean:
        return None
    settings = get_settings()
    digest = content_hash(clean)
    existing = session.exec(
        select(EmbeddingRecord).where(
            EmbeddingRecord.owner_type == owner_type,
            EmbeddingRecord.owner_id == owner_id,
            EmbeddingRecord.source_type == source_type,
            EmbeddingRecord.content_hash == digest,
        )
    ).first()
    if existing:
        return existing
    record = EmbeddingRecord(
        owner_type=owner_type,
        owner_id=owner_id,
        source_type=source_type,
        content_hash=digest,
        embedding_model=(
            settings.openai_embedding_model if openai_enabled() else "deterministic-local"
        ),
        dimensions=settings.openai_embedding_dimensions,
        embedding_json=json.dumps(embedding_for_text(clean)),
        preview_text=clean[:500],
    )
    session.add(record)
    return record


def latest_embedding(
    session: Session, owner_type: str, owner_id: str, source_type: str | None = None
) -> EmbeddingRecord | None:
    statement = select(EmbeddingRecord).where(
        EmbeddingRecord.owner_type == owner_type,
        EmbeddingRecord.owner_id == owner_id,
    )
    if source_type:
        statement = statement.where(EmbeddingRecord.source_type == source_type)
    return session.exec(statement.order_by(EmbeddingRecord.created_at.desc())).first()


def decode_embedding(record: EmbeddingRecord) -> list[float]:
    return [float(value) for value in json.loads(record.embedding_json)]
