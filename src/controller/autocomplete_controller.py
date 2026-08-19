from src.services.interfaces.services import IAutocompleteService
from src.models.entities import UserEntity
from src.schemas.autocomplete import AutocompleteRequest, AutocompleteResponse


class AutocompleteController:
    def __init__(self, autocomplete_service: IAutocompleteService):
        self._autocomplete_service = autocomplete_service

    async def handle_autocomplete(self, request: AutocompleteRequest, user: UserEntity) -> AutocompleteResponse:
        return await self._autocomplete_service.get_completion(request, user)
