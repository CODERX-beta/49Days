from datetime import datetime

from pydantic import BaseModel, Field


class ContentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    caption: str
    media_url: str
    platform: str


class ContentResponse(BaseModel):
    id: int
    title: str
    caption: str
    media_url: str
    platform: str
    status: str
    created_at: datetime

    model_config = {
        "from_attributes": True
    }