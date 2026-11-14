from typing import Literal

from backend.llm import llm
from backend.llm.models import Suggestion

Provider = Literal['openai', 'anthropic']


def run_suggest(prompt: str, provider: Provider) -> Suggestion:
    return llm.suggest(prompt, provider)
