from fastapi import APIRouter
from src.routes.session_routes import router as session_router
from src.routes.chat_routes import router as chat_router

api_router = APIRouter()
api_router.include_router(session_router)
api_router.include_router(chat_router)
