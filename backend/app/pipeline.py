"""Pipeline state machine and ownership-safe repository contracts."""
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import StrEnum
from typing import Protocol
from uuid import UUID


class PipelineState(StrEnum):
    DRAFT = "draft"
    QUEUED = "queued"
    GENERATING = "generating"
    AWAITING_REVIEW = "awaiting_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISION_REQUESTED = "revision_requested"
    PUBLISHED = "published"


# The sole source of truth for legal workflow movement.
TRANSITIONS: dict[PipelineState, frozenset[PipelineState]] = {
    PipelineState.DRAFT: frozenset({PipelineState.QUEUED}),
    PipelineState.QUEUED: frozenset({PipelineState.GENERATING}),
    PipelineState.GENERATING: frozenset({PipelineState.AWAITING_REVIEW}),
    PipelineState.AWAITING_REVIEW: frozenset({PipelineState.APPROVED, PipelineState.REJECTED, PipelineState.REVISION_REQUESTED}),
    PipelineState.APPROVED: frozenset({PipelineState.PUBLISHED}),
    PipelineState.REJECTED: frozenset({PipelineState.REVISION_REQUESTED}),
    PipelineState.REVISION_REQUESTED: frozenset({PipelineState.QUEUED}),
    PipelineState.PUBLISHED: frozenset(),
}


def transition(current: PipelineState, target: PipelineState) -> PipelineState:
    if target not in TRANSITIONS[current]:
        raise ValueError(f"illegal pipeline transition: {current.value} -> {target.value}")
    return target


@dataclass(frozen=True)
class PipelineRun:
    id: UUID
    owner_id: UUID
    state: PipelineState = PipelineState.DRAFT
    created_at: datetime | None = None
    updated_at: datetime | None = None
    content: object | None = None
    rejection_feedback: str | None = None


class PipelineRepository(Protocol):
    def list_for_owner(self, owner_id: UUID) -> list[PipelineRun]: ...
    def get_for_owner(self, owner_id: UUID, run_id: UUID) -> PipelineRun | None: ...
    def update_for_owner(self, owner_id: UUID, run_id: UUID, state: PipelineState) -> PipelineRun | None: ...
    def attach_content(self, owner_id: UUID, run_id: UUID, content: object) -> PipelineRun | None: ...


class InMemoryPipelineRepository:
    def __init__(self) -> None:
        self._runs: dict[UUID, PipelineRun] = {}

    def create(self, run: PipelineRun) -> PipelineRun:
        if run.id in self._runs:
            raise ValueError(f"pipeline run already exists: {run.id}")
        now = datetime.now(timezone.utc)
        stored = replace(run, created_at=run.created_at or now, updated_at=run.updated_at or now)
        self._runs[run.id] = stored
        return stored

    def list_for_owner(self, owner_id: UUID) -> list[PipelineRun]:
        return [run for run in self._runs.values() if run.owner_id == owner_id]

    def get_for_owner(self, owner_id: UUID, run_id: UUID) -> PipelineRun | None:
        run = self._runs.get(run_id)
        return run if run is not None and run.owner_id == owner_id else None

    def update_for_owner(self, owner_id: UUID, run_id: UUID, state: PipelineState, **changes: object) -> PipelineRun | None:
        current = self.get_for_owner(owner_id, run_id)
        if current is None:
            return None
        updated = replace(current, state=transition(current.state, state), updated_at=datetime.now(timezone.utc), **changes)
        self._runs[run_id] = updated
        return updated

    def attach_content(self, owner_id: UUID, run_id: UUID, content: object) -> PipelineRun | None:
        current = self.get_for_owner(owner_id, run_id)
        if current is None:
            return None
        updated = replace(current, content=content, updated_at=datetime.now(timezone.utc))
        self._runs[run_id] = updated
        return updated


class SupabasePipelineRepository:
    """Incomplete persistence adapter; wire Supabase queries in a later step."""

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        self._incomplete = True

    def _not_implemented(self) -> None:
        raise NotImplementedError("SupabasePipelineRepository is intentionally incomplete")

    def list_for_owner(self, owner_id: UUID) -> list[PipelineRun]:
        self._not_implemented()

    def get_for_owner(self, owner_id: UUID, run_id: UUID) -> PipelineRun | None:
        self._not_implemented()

    def update_for_owner(self, owner_id: UUID, run_id: UUID, state: PipelineState) -> PipelineRun | None:
        self._not_implemented()
