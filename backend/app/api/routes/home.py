from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.queries.home import build_home_overview
from app.schemas.home import HomeOverview
from app.schemas.response import Response

router = APIRouter(prefix="/home", tags=["观测台"])


@router.get("/overview", response_model=Response[HomeOverview])
async def get_home_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return Response(data=build_home_overview(db, current_user.id))
