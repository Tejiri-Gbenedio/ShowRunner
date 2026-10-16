from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

@dataclass(frozen=True)
class StoredRun:
    id: UUID
    user_id: UUID

class RunRepository(Protocol):
    def list_for_user(self, user_id: UUID) -> list[StoredRun]: ...
    def get_for_user(self, user_id: UUID, run_id: UUID) -> StoredRun | None: ...
    def save(self, run: StoredRun) -> StoredRun: ...

class LLMAdapter(Protocol):
    def complete(self, prompt: str) -> str: ...
