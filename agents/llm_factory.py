"""Factory for role-keyed BaseChatModel instances.

Nodes call `get_llm(role)` rather than importing provider classes directly,
so prompts stay model-agnostic and providers can be swapped via config or
per-call override (used by the manual-test CLIs).
"""

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from agents.config import ROLE_NAMES, RoleConfig, get_settings


def _build(cfg: RoleConfig) -> BaseChatModel:
    if cfg.provider == "anthropic":
        kwargs = {"model": cfg.model}
        if cfg.temperature is not None:
            kwargs["temperature"] = cfg.temperature
        kwargs["max_tokens"] = cfg.max_tokens or 4096
        return ChatAnthropic(**kwargs)
    if cfg.provider == "openai":
        kwargs = {"model": cfg.model}
        if cfg.temperature is not None:
            kwargs["temperature"] = cfg.temperature
        if cfg.max_tokens is not None:
            kwargs["max_tokens"] = cfg.max_tokens
        return ChatOpenAI(**kwargs)
    raise ValueError(f"unknown provider: {cfg.provider}")


def get_llm(
    role: str,
    *,
    provider: str | None = None,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> BaseChatModel:
    if role not in ROLE_NAMES:
        raise ValueError(f"unknown role: {role!r}; expected one of {ROLE_NAMES}")

    base: RoleConfig = getattr(get_settings(), role)
    cfg = base.model_copy(
        update={
            k: v
            for k, v in {
                "provider": provider,
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }.items()
            if v is not None
        }
    )
    return _build(cfg)
