import httpx
from src.services.interfaces.services import IAutocompleteService
from src.models.entities import UserEntity
from src.schemas.autocomplete import AutocompleteRequest, AutocompleteResponse
from src.config.settings import AppSettings

FIM_PREFIX_TOKEN = "<|fim_prefix|>"
FIM_SUFFIX_TOKEN = "<|fim_suffix|>"
FIM_MIDDLE_TOKEN = "<|fim_middle|>"

# Sent as `stop` so the model halts at the end of the hole it is filling, and
# used again to trim anything that leaks into the text despite them.
FIM_STOP_TOKENS = [
    FIM_PREFIX_TOKEN,
    FIM_SUFFIX_TOKEN,
    FIM_MIDDLE_TOKEN,
    "<|fim_pad|>",
    "<|endoftext|>",
    "<|repo_name|>",
    "<|file_sep|>",
]


def _trim_to_filled_block(text: str) -> str:
    """
    Keep only the completion for the current hole.

    Qwen2.5-Coder does not reliably emit a FIM terminator, so a raw completion
    runs on into whole unrelated functions until max_tokens. A blank line marks
    the end of the block being filled, so cut there.
    """
    for token in FIM_STOP_TOKENS:
        index = text.find(token)
        if index != -1:
            text = text[:index]

    paragraph_break = text.find("\n\n")
    if paragraph_break != -1:
        text = text[:paragraph_break]

    return text.rstrip()


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
                    "temperature": 0.1,
                    "stop": FIM_STOP_TOKENS
                }
            )
            resp.raise_for_status()
            data = resp.json()
            completion_text = data["choices"][0]["text"]

        return AutocompleteResponse(completion=_trim_to_filled_block(completion_text))
