from sqlalchemy.orm import Session

from app.repositories.content_repository import ContentRepository
from app.schemas.content import ContentCreate


class ContentService:
    def __init__(self, db: Session):
        self.repository = ContentRepository(db)

    def create_content(self, content: ContentCreate):
        return self.repository.create(content)

    def get_content(self, content_id: int):
        return self.repository.get_by_id(content_id)