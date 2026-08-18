from src.models.entities import UserEntity, SessionEntity, MessageEntity
from src.schemas.user import UserResponse
from src.schemas.session import SessionResponse, SessionDetailResponse, MessageItem


class EntityMapper:
    @staticmethod
    def user_entity_to_schema(entity: UserEntity) -> UserResponse:
        return UserResponse(
            id=entity.id,
            username=entity.username,
            api_key=entity.api_key
        )

    @staticmethod
    def session_entity_to_summary(entity: SessionEntity) -> SessionResponse:
        return SessionResponse(
            id=entity.id,
            title=entity.title,
            created_at=entity.created_at,
            updated_at=entity.updated_at
        )

    @staticmethod
    def session_entity_to_detail(entity: SessionEntity) -> SessionDetailResponse:
        messages = [
            MessageItem(role=m.role, content=m.content, created_at=m.created_at)
            for m in entity.messages
        ]
        return SessionDetailResponse(
            id=entity.id,
            title=entity.title,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            messages=messages
        )
