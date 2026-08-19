from typing import AsyncGenerator
from fastapi import Depends, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.connection import AsyncSessionLocal
from src.config.settings import get_settings, AppSettings
from src.models.entities import UserEntity

# Repositories
from src.db.interfaces.repositories import IUserRepository, ISessionRepository, ITaskRepository
from src.db.repositories.user_repository import PostgresUserRepository
from src.db.repositories.session_repository import PostgresSessionRepository
from src.db.repositories.task_repository import PostgresTaskRepository

# Services
from src.services.interfaces.services import IAuthService, ISessionService, IChatService, ITaskService, IAutocompleteService
from src.services.implementations.auth_service import AuthService
from src.services.implementations.session_service import SessionService
from src.services.implementations.chat_service import ChatService
from src.services.implementations.task_service import TaskService
from src.services.implementations.autocomplete_service import AutocompleteService

# Controllers
from src.controller.auth_controller import AuthController
from src.controller.session_controller import SessionController
from src.controller.chat_controller import ChatController
from src.controller.task_controller import TaskController
from src.controller.autocomplete_controller import AutocompleteController

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


# --- DB Session DI ---
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


# --- Repositories DI ---
def get_user_repository(db: AsyncSession = Depends(get_db_session)) -> IUserRepository:
    return PostgresUserRepository(db)


def get_session_repository(db: AsyncSession = Depends(get_db_session)) -> ISessionRepository:
    return PostgresSessionRepository(db)


def get_task_repository(db: AsyncSession = Depends(get_db_session)) -> ITaskRepository:
    return PostgresTaskRepository(db)


# --- Services DI ---
def get_auth_service(
    user_repo: IUserRepository = Depends(get_user_repository),
    settings: AppSettings = Depends(get_settings)
) -> IAuthService:
    return AuthService(user_repo, settings)


def get_session_service(
    session_repo: ISessionRepository = Depends(get_session_repository)
) -> ISessionService:
    return SessionService(session_repo)


def get_chat_service(
    session_repo: ISessionRepository = Depends(get_session_repository),
    settings: AppSettings = Depends(get_settings)
) -> IChatService:
    return ChatService(session_repo, settings)


def get_task_service(
    task_repo: ITaskRepository = Depends(get_task_repository)
) -> ITaskService:
    return TaskService(task_repo)


def get_autocomplete_service(
    settings: AppSettings = Depends(get_settings)
) -> IAutocompleteService:
    return AutocompleteService(settings)


# --- Auth Principal DI ---
async def get_authenticated_user(
    api_key: str = Security(api_key_header),
    auth_service: IAuthService = Depends(get_auth_service)
) -> UserEntity:
    return await auth_service.authenticate_key(api_key)


# --- Controllers DI ---
def get_auth_controller(auth_service: IAuthService = Depends(get_auth_service)) -> AuthController:
    return AuthController(auth_service)


def get_session_controller(session_service: ISessionService = Depends(get_session_service)) -> SessionController:
    return SessionController(session_service)


def get_chat_controller(chat_service: IChatService = Depends(get_chat_service)) -> ChatController:
    return ChatController(chat_service)


def get_task_controller(task_service: ITaskService = Depends(get_task_service)) -> TaskController:
    return TaskController(task_service)


def get_autocomplete_controller(
    autocomplete_service: IAutocompleteService = Depends(get_autocomplete_service)
) -> AutocompleteController:
    return AutocompleteController(autocomplete_service)