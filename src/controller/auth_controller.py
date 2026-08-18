from src.services.interfaces.services import IAuthService
from src.schemas.user import UserCreateRequest, UserResponse
from src.models.entities import UserEntity


class AuthController:
    def __init__(self, auth_service: IAuthService):
        self._auth_service = auth_service

    async def register_user(self, request: UserCreateRequest) -> UserResponse:
        return await self._auth_service.provision_user(request.username)

    async def get_me(self, user: UserEntity) -> UserResponse:
        return await self._auth_service.get_current_user(user)