from fastapi import APIRouter

from rest_api.dependencies import CurrentUser
from schemas.auth.sch_auth import CurrentUserSchema

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me")
async def get_me(user: CurrentUser) -> CurrentUserSchema:
    return user
