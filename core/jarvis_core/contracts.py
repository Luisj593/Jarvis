"""Contratos puros entre interfaces y núcleo."""
from dataclasses import dataclass, field
from typing import Literal

@dataclass(frozen=True)
class Request:
    text: str
    project: str = "general"
    session_id: str = "default"

@dataclass(frozen=True)
class Response:
    text: str
    intent: Literal["teach", "recall", "query", "clarify", "unknown"]
    memory_ids: tuple[str, ...] = field(default_factory=tuple)
    requires_confirmation: bool = False
