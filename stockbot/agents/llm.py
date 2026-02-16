"""LLM provider factory."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from langchain_core.language_models import BaseChatModel

from config.settings import Settings


def get_llm(settings: Settings) -> BaseChatModel:
    """Create an LLM instance based on settings."""
    if settings.llm_provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            api_key=settings.anthropic_api_key,
            max_tokens=4096,
        )
    elif settings.llm_provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            api_key=settings.openai_api_key,
        )
    else:
        raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")


def load_prompt(prompt_name: str) -> str:
    """Load a system prompt from the prompts directory."""
    prompt_path = Path(__file__).parent / "prompts" / prompt_name
    return prompt_path.read_text()
