from sqlalchemy.orm import Session

from app.models.content import Content
from app.schemas.content import ContentCreate


class ContentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, content: ContentCreate) -> Content:
        db_content = Content(
            title=content.title,
            caption=content.caption,
            media_url=content.media_url,
            platform=content.platform,
        )

        self.db.add(db_content)
        self.db.commit()
        self.db.refresh(db_content)

        return db_content

    def get_by_id(self, content_id: int):
        return (
            self.db.query(Content)
            .filter(Content.id == content_id)
            .first()
        )