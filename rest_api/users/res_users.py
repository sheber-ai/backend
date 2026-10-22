from aioinject import Injected
from aioinject.ext.fastapi import inject
from fastapi import APIRouter

from rest_api.dependencies import CurrentUser, Language
from schemas.users.sch_user import UserSchema, UserUpdateSchema
from services.users.svc_users import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
@inject
async def get_my_profile(user: CurrentUser, language: Language, svc_users: Injected[UserService]) -> UserSchema:
    return await svc_users.get_me(user, language)


@router.put("/me")
@inject
async def update_my_profile(
    body: UserUpdateSchema, user: CurrentUser, language: Language, svc_users: Injected[UserService]
) -> UserSchema:
    return await svc_users.update_me(user, body, language)
