from uuid import UUID
from fastapi import APIRouter, Depends, status
from src.schemas.session import SessionResponse, SessionDetailResponse
from src.controller.session_controller import SessionController
from src.di.container import get_session_controller, get_authenticated_user
from src.models.entities import UserEntity

router = APIRouter(prefix="/sessions", tags=["Chat Sessions & History"])


@router.get("", response_model=list[SessionResponse])
async def list_sessions(
    user: UserEntity = Depends(get_authenticated_user),
    controller: SessionController = Depends(get_session_controller)
):
    return await controller.get_all_sessions(user)


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session_history(
    session_id: UUID,
    user: UserEntity = Depends(get_authenticated_user),
    controller: SessionController = Depends(get_session_controller)
):
    return await controller.get_session(session_id, user)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: UUID,
    user: UserEntity = Depends(get_authenticated_user),
    controller: SessionController = Depends(get_session_controller)
):
    await controller.delete_session(session_id, user)