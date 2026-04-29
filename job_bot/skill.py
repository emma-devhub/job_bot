from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .context import ApplicationContext


class Skill(ABC):
    """Base class for every pipeline skill module."""

    name: str = ""
    description: str = ""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config: dict[str, Any] = config or {}

    @abstractmethod
    def run(self, ctx: ApplicationContext) -> ApplicationContext:
        """Execute the skill, mutate ctx in-place, return it."""

    def skip(self, ctx: ApplicationContext, reason: str) -> ApplicationContext:
        ctx.skipped_skills.append(self.name)
        ctx.metadata[f"{self.name}.skip_reason"] = reason
        return ctx

    # Convenience helpers -------------------------------------------------

    def cfg(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)
