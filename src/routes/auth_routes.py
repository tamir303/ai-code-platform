from fastapi import APIRouter, Depends, status
from src.schemas.user import UserCreateRequest, UserResponse
from src.controller.auth_controller import AuthController
from src.di.container import get_auth_controller, get_authenticated_user
from src.models.entities import UserEntity

router = APIRouter(prefix="/auth", tags=["Authentication & Keys"])


@router.post("/provision", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def provision_user(
    req: UserCreateRequest,
    controller: AuthController = Depends(get_auth_controller)
):
    return await controller.register_user(req)


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    user: UserEntity = Depends(get_authenticated_user),
    controller: AuthController = Depends(get_auth_controller)
):
    return await controller.get_me(user)