"""Per-role LLM provider/model configuration.

Seven roles: three generators, three validators, one feedback classifier.
Each role can be configured independently via env vars or by passing overrides
to llm_factory.get_llm().

Env shape (Pydantic Settings nested syntax):
    AGENT_GENERATOR_QUESTION__PROVIDER=anthropic
    AGENT_GENERATOR_QUESTION__MODEL=claude-opus-4-7
    AGENT_VALIDATOR_SOLVER__MODEL=claude-haiku-4-5
"""

from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

Provider = Literal["anthropic", "openai"]


class RoleConfig(BaseModel):
    provider: Provider = "anthropic"
    model: str = "claude-haiku-4-5"
    temperature: float | None = None
    max_tokens: int | None = None


def _generator_default() -> RoleConfig:
    return RoleConfig(provider="openai", model="gpt-5.4-mini")


def _cheap_default() -> RoleConfig:
    return RoleConfig(provider="openai", model="gpt-5.4-mini")


class AgentSettings(BaseSettings):
    generator_question: RoleConfig = Field(default_factory=_generator_default)
    generator_solver: RoleConfig = Field(default_factory=_generator_default)
    generator_game: RoleConfig = Field(default_factory=_generator_default)
    validator_question: RoleConfig = Field(default_factory=_cheap_default)
    validator_solver: RoleConfig = Field(default_factory=_cheap_default)
    validator_game: RoleConfig = Field(default_factory=_cheap_default)
    feedback_classifier: RoleConfig = Field(default_factory=_cheap_default)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="AGENT_",
        env_nested_delimiter="__",
        extra="ignore",
    )


ROLE_NAMES = (
    "generator_question",
    "generator_solver",
    "generator_game",
    "validator_question",
    "validator_solver",
    "validator_game",
    "feedback_classifier",
)


@lru_cache(maxsize=1)
def get_settings() -> AgentSettings:
    return AgentSettings()
