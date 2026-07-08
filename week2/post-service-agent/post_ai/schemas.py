from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


SplitName = Literal["train", "val", "test", "policy"]
MessageRole = Literal["system", "user", "assistant"]


class ChatMessage(BaseModel):
    role: MessageRole
    content: str


class ChatDelta(BaseModel):
    content: str
    done: bool = False
    raw: dict[str, Any] = Field(default_factory=dict)


class ChatResult(BaseModel):
    content: str
    raw: dict[str, Any] = Field(default_factory=dict)


class EmbeddingResult(BaseModel):
    vectors: list[list[float]]
    model: str
    provider: str
    raw: dict[str, Any] = Field(default_factory=dict)


class DialogueTurn(BaseModel):
    speaker: Literal["Q", "A"]
    turn: int
    utterance: str


class QASummary(BaseModel):
    QueSumm: str
    AnsSummShort: str
    AnsSummLong: str
    QueSummUttIDs: list[int]
    AnsSummShortUttIDs: list[int]
    AnsSummLongUttIDs: list[int]
    QASumm: str
    intent: str | None = None


class CSDSDialogue(BaseModel):
    DialogueID: int
    QRole: str
    QA: list[QASummary]
    Session_id: str
    Dialogue: list[DialogueTurn]
    UserSumm: list[str]
    AgentSumm: list[str]
    FinalSumm: list[str]


class FilterRecord(BaseModel):
    index: int
    session_id: str
    dialogue_id: int
    is_postal_related: bool
    raw_response: str


class EmbeddingMetadata(BaseModel):
    index: int
    session_id: str
    dialogue_id: int
    turn_count: int


class PostalDocument(BaseModel):
    split: SplitName
    index: int
    session_id: str
    dialogue_id: int
    source_path: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def source_key(self) -> str:
        return f"{self.split}:{self.index}:{self.session_id}:{self.dialogue_id}"


class RetrievalHit(BaseModel):
    document: PostalDocument
    score: float
    rank: int


class TicketPayload(BaseModel):
    user_id: str = ""
    timestamp: str
    service_type: str = ""
    issue_type: str = ""
    user_request: str = ""
    summary: str = ""
    resolution: str = ""
    need_follow_up: bool = False

    model_config = ConfigDict(extra="forbid")

    @classmethod
    def empty_now(cls) -> "TicketPayload":
        return cls(timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"))
