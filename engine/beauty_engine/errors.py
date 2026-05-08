from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EngineError(Exception):
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "details": self.details}


def ensure(condition: bool, code: str, message: str, **details: Any) -> None:
    if not condition:
        raise EngineError(code, message, details)
