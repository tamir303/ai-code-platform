from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from src.schemas.session import SessionResponse, SessionDetailResponse
from src.controller.session_controller import SessionController
from src.di.container import get_session_controller

router = APIRouter(prefix="/sessions", tags=["Chat Sessions & History"])


@router.get("", response_model=list[SessionResponse])
async def list_sessions(
    limit: int = Query(default=20, ge=1, le=100, description="Max number of sessions to return"),
    offset: int = Query(default=0, ge=0, description="Number of sessions to skip"),
    controller: SessionController = Depends(get_session_controller)
):
    return await controller.get_all_sessions(limit=limit, offset=offset)


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session_history(
    session_id: UUID,
    limit: int = Query(default=50, ge=1, le=100, description="Max number of messages to return"),
    offset: int = Query(default=0, ge=0, description="Number of messages to skip"),
    controller: SessionController = Depends(get_session_controller)
):
    return await controller.get_session(session_id, limit=limit, offset=offset)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: UUID,
    controller: SessionController = Depends(get_session_controller)
):
    await controller.delete_session(session_id)
