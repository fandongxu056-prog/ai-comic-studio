"""Shared LLM service — unified client factory with structured output support.

Supports OpenAI (GPT-4o) and Anthropic (Claude) backends via LangChain.
Provides a singleton factory that reads configuration from app settings.
"""

from functools import lru_cache
from typing import Any, Literal

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.config import settings


class LLMConfig(BaseModel):
    """Configuration for a single LLM backend instance."""

    provider: Literal["openai", "anthropic"] = "openai"
    model: str = "gpt-4o"
    api_key: str = ""
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=16000, ge=100, le=200000)


class LLMService:
    """Unified LLM client factory with structured output support.

    Usage:
        service = LLMService(LLMConfig(provider="openai", model="gpt-4o", api_key="..."))
        chat_model = service.get_chat_model()
        structured_model = service.get_structured_model(MyPydanticModel)

        # Convenience: one-shot structured generation
        result = await service.generate_structured(
            system_prompt="You are a helpful assistant.",
            human_prompt="Generate a story outline.",
            schema=StoryOutline,
        )
    """

    def __init__(self, config: LLMConfig | None = None):
        self.config = config or LLMConfig(
            provider="openai",
            model=settings.openai_model,
            api_key=settings.openai_api_key,
        )

    # ── Provider Detection ──

    @property
    def provider(self) -> str:
        return self.config.provider

    @property
    def is_openai(self) -> bool:
        return self.config.provider == "openai"

    @property
    def is_anthropic(self) -> bool:
        return self.config.provider == "anthropic"

    # ── Client Creation ──

    def get_chat_model(self, **overrides: Any) -> BaseChatModel:
        """Create a LangChain-compatible chat model.

        Args:
            **overrides: Override any LLMConfig field (temperature, max_tokens, etc.)
        """
        temp = overrides.pop("temperature", self.config.temperature)
        max_tok = overrides.pop("max_tokens", self.config.max_tokens)

        if self.is_openai:
            return ChatOpenAI(
                model=self.config.model,
                api_key=self.config.api_key,
                temperature=temp,
                max_tokens=max_tok,
                **overrides,
            )
        else:
            return ChatAnthropic(
                model=self.config.model,
                api_key=self.config.api_key,
                temperature=temp,
                max_tokens=max_tok,
                **overrides,
            )

    def get_structured_model(self, schema: type[BaseModel], **overrides: Any) -> BaseChatModel:
        """Create a chat model that returns structured output matching the given Pydantic schema.

        Uses LangChain's with_structured_output() for JSON-mode generation.

        Args:
            schema: A Pydantic BaseModel subclass defining the output structure.
            **overrides: Override any LLMConfig field.

        Returns:
            A BaseChatModel that will return instances of `schema`.
        """
        model = self.get_chat_model(**overrides)
        return model.with_structured_output(schema)

    # ── Convenience Methods ──

    async def generate_structured(
        self,
        system_prompt: str,
        human_prompt: str,
        schema: type[BaseModel],
        **overrides: Any,
    ) -> BaseModel:
        """One-shot: generate structured output from prompts.

        Args:
            system_prompt: System-level instruction.
            human_prompt: User-level input.
            schema: Pydantic model to constrain the output.
            **overrides: LLMConfig overrides for this call.

        Returns:
            An instance of `schema` populated by the LLM.
        """
        structured_model = self.get_structured_model(schema, **overrides)
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt),
        ]
        return await structured_model.ainvoke(messages)

    async def generate_text(
        self,
        system_prompt: str,
        human_prompt: str,
        **overrides: Any,
    ) -> str:
        """One-shot: generate free-text response.

        Args:
            system_prompt: System-level instruction.
            human_prompt: User-level input.
            **overrides: LLMConfig overrides for this call.

        Returns:
            Raw text response from the LLM.
        """
        model = self.get_chat_model(**overrides)
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt),
        ]
        response = await model.ainvoke(messages)
        return str(response.content)

    # ── Cost Estimation ──

    def estimate_tokens(self, text: str) -> int:
        """Rough token count estimation (4 chars ≈ 1 token for Chinese)."""
        # Chinese text: ~1.5 chars per token; English: ~4 chars per token
        return max(1, len(text) // 2)


# ── Singleton Factory ──


def create_llm_service_from_settings() -> LLMService:
    """Create an LLMService from global application settings.

    Chooses the provider based on which API key is configured.
    Prefers Anthropic if available (Claude produces better creative writing in Chinese),
    falls back to OpenAI.
    """
    if settings.anthropic_api_key:
        config = LLMConfig(
            provider="anthropic",
            model=settings.anthropic_model,
            api_key=settings.anthropic_api_key,
        )
    elif settings.openai_api_key:
        config = LLMConfig(
            provider="openai",
            model=settings.openai_model,
            api_key=settings.openai_api_key,
        )
    else:
        raise ValueError(
            "No LLM API key configured. Set ANTHROPIC_API_KEY or OPENAI_API_KEY in .env"
        )

    return LLMService(config)


@lru_cache(maxsize=1)
def get_llm_service() -> LLMService:
    """Get the cached singleton LLMService instance.

    Uses lru_cache so the service is created once and reused across the application.
    """
    return create_llm_service_from_settings()
