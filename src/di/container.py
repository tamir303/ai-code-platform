from typing import AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.connection import AsyncSessionLocal
from src.config.settings import get_settings, AppSettings

# Repositories
from src.db.interfaces.repositories import ISessionRepository
from src.db.repositories.session_repository import PostgresSessionRepository

# Services
from src.services.interfaces.services import ISessionService, IChatService
from src.services.implementations.session_service import SessionService
from src.services.implementations.chat_service import ChatService

# Controllers
from src.controller.session_controller import SessionController
from src.controller.chat_controller import ChatController


# --- DB Session DI ---
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


# --- Repositories DI ---
def get_session_repository(db: AsyncSession = Depends(get_db_session)) -> ISessionRepository:
    return PostgresSessionRepository(db)


# --- Services DI ---
def get_session_service(
    session_repo: ISessionRepository = Depends(get_session_repository)
) -> ISessionService:
    return SessionService(session_repo)


def get_chat_service(
    session_repo: ISessionRepository = Depends(get_session_repository),
    settings: AppSettings = Depends(get_settings)
) -> IChatService:
    return ChatService(session_repo, settings)


# --- Controllers DI ---
def get_session_controller(session_service: ISessionService = Depends(get_session_service)) -> SessionController:
    return SessionController(session_service)


def get_chat_controller(chat_service: IChatService = Depends(get_chat_service)) -> ChatController:
    return ChatController(chat_service)
