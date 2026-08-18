import httpx
from fastapi import HTTPException, status
from src.services.interfaces.services import IAuthService
from src.db.interfaces.repositories import IUserRepository
from src.models.entities import UserEntity
from src.schemas.user import UserResponse
from src.utils.mappers import EntityMapper
from src.config.settings import AppSettings


class AuthService(IAuthService):
    def __init__(self, user_repo: IUserRepository, settings: AppSettings):
        self._user_repo = user_repo
        self._settings = settings

    async def authenticate_key(self, api_key: str) -> UserEntity:
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authentication credentials in X-API-Key or Bearer header"
            )
        user = await self._user_repo.get_by_api_key(api_key)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid or unauthorized API key"
            )
        return user

    async def provision_user(self, username: str) -> UserResponse:
        # Generate virtual key in LiteLLM
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{self._settings.LITELLM_URL}/key/generate",
                headers={"Authorization": f"Bearer {self._settings.LITELLM_MASTER_KEY}"},
                json={
                    "models": [self._settings.DEFAULT_CODE_MODEL],
                    "rpm_limit": 120,
                    "tpm_limit": 200000,
                    "user_id": username
                }
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=500, detail=f"Failed to generate LiteLLM key: {resp.text}")
            key_data = resp.json()
            virtual_key = key_data.get("key")

        # Persist User in local DB
        user_entity = await self._user_repo.create(username=username, api_key=virtual_key)
        return EntityMapper.user_entity_to_schema(user_entity)

    async def get_current_user(self, user: UserEntity) -> UserResponse:
        return EntityMapper.user_entity_to_schema(user)