from fastapi import APIRouter, Depends
from src.schemas.autocomplete import AutocompleteRequest, AutocompleteResponse
from src.controller.autocomplete_controller import AutocompleteController
from src.di.container import get_autocomplete_controller, get_authenticated_user
from src.models.entities import UserEntity

router = APIRouter(prefix="/autocomplete", tags=["Code Autocomplete"])


@router.post("", response_model=AutocompleteResponse)
async def get_autocomplete(
    req: AutocompleteRequest,
    user: UserEntity = Depends(get_authenticated_user),
    controller: AutocompleteController = Depends(get_autocomplete_controller)
):
    """
    Returns a single fill-in-the-middle code completion for the given prefix/suffix.
    """
    return await controller.handle_autocomplete(req, user)
