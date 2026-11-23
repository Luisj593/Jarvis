"""JARVIS: núcleo independiente, sin dependencias externas ni modelos de IA."""
from .engine import AssistantEngine
from .memory import InMemoryStore, Lesson
from .contracts import Request, Response

__all__ = ["AssistantEngine", "InMemoryStore", "Lesson", "Request", "Response"]
