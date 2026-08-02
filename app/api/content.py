from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.content import ContentCreate, ContentResponse
from app.services.content_service import ContentService

router = APIRouter(
    prefix="/api/v1/content",
    tags=["Content"],
)


@router.post(
    "/",
    response_model=ContentResponse,
    status_code=201,
)
def create_content(
    content: ContentCreate,
    db: Session = Depends(get_db),
):
    service = ContentService(db)
    return service.create_content(content)