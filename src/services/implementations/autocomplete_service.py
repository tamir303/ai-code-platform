import httpx
from src.services.interfaces.services import IAutocompleteService
from src.models.entities import UserEntity
from src.schemas.autocomplete import AutocompleteRequest, AutocompleteResponse
from src.config.settings import AppSettings

FIM_PREFIX_TOKEN = "<|fim_prefix|>"
FIM_SUFFIX_TOKEN = "<|fim_suffix|>"
FIM_MIDDLE_TOKEN = "<|fim_middle|>"


class AutocompleteService(IAutocompleteService):
    def __init__(self, settings: AppSettings):
        self._settings = settings

    async def get_completion(self, request: AutocompleteRequest, user: UserEntity) -> AutocompleteResponse:
        fim_prompt = f"{FIM_PREFIX_TOKEN}{request.prefix}{FIM_SUFFIX_TOKEN}{request.suffix}{FIM_MIDDLE_TOKEN}"

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self._settings.LITELLM_URL}/v1/completions",
                headers={
                    "Authorization": f"Bearer {user.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self._settings.DEFAULT_CODE_MODEL,
                    "prompt": fim_prompt,
                    "max_tokens": 128,
                    "temperature": 0.1
                }
            )
            resp.raise_for_status()
            data = resp.json()
            completion_text = data["choices"][0]["text"]

        return AutocompleteResponse(completion=completion_text)
