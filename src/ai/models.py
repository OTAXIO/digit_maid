from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class PanelState(str, Enum):
    HIDDEN = "hidden"
    INPUTTING = "inputting"
    REQUESTING = "requesting"
    ERROR = "error"


@dataclass
class ChatMessage:
    role: str
    content: str
    render_type: str = "text"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def to_request_payload(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}
