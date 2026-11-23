"""Intenciones deterministas: no se aprende de conversaciones sin autorización."""
import unicodedata
from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class Intent:
    name: Literal["teach", "recall", "query", "unknown"]
    payload: str = ""

def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(c for c in decomposed if not unicodedata.combining(c)).strip()

def classify(text: str) -> Intent:
    raw = text.strip()
    clean = normalize(raw)
    for prefix in ("aprende:", "recuerda:", "aprende que ", "recuerda que "):
        if clean.startswith(prefix):
            return Intent("teach", raw[len(prefix):].strip())
    if clean in ("que recuerdas", "que sabes", "muestra memoria"):
        return Intent("recall")
    if clean:
        return Intent("query", raw)
    return Intent("unknown")
