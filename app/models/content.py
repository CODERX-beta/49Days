from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ContentStatus(str, Enum):
    QUEUED = "queued"
    POSTING = "posting"
    POSTED = "posted"
    FAILED = "failed"


class Content(Base):
    __tablename__ = "content"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    title: Mapped[str] = mapped_column(String(255))
    caption: Mapped[str] = mapped_column(String)

    media_url: Mapped[str] = mapped_column(String)

    platform: Mapped[str] = mapped_column(String(50))

    status: Mapped[ContentStatus] = mapped_column(
        SqlEnum(ContentStatus),
        default=ContentStatus.QUEUED,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    