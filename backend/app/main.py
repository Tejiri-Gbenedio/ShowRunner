from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from app.agents import run_offline_sequence
from app.pipeline import InMemoryPipelineRepository, PipelineRun, PipelineState
from app.presets import PRESETS, list_presets

app = FastAPI(title="Showrunner API", version="0.2.0")
repository = InMemoryPipelineRepository()
_run_windows: dict[UUID, list[datetime]] = {}
MAX_RUNS_PER_HOUR = 5

class Rejection(BaseModel):
    feedback: str = Field(min_length=1, max_length=1000)

def owner_id(value: str | None) -> UUID:
    try:
        return UUID(value or "")
    except ValueError as exc:
        raise HTTPException(400, "X-Anonymous-User-ID must be a valid UUID") from exc

def get_run(owner: UUID, run_id: UUID) -> PipelineRun:
    run = repository.get_for_owner(owner, run_id)
    if run is None:
        raise HTTPException(404, "run not found")
    return run

def output(run: PipelineRun) -> dict:
    return {**asdict(run), "id": str(run.id), "owner_id": str(run.owner_id), "state": run.state.value,
            "created_at": run.created_at.isoformat() if run.created_at else None,
            "updated_at": run.updated_at.isoformat() if run.updated_at else None}

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "showrunner"}

@app.get("/api/presets")
def presets() -> list[dict]:
    return list_presets()

@app.post("/api/runs", status_code=201)
def create_run(preset_id: str, x_anonymous_user_id: str | None = Header(default=None)) -> dict:
    owner = owner_id(x_anonymous_user_id)
    if preset_id not in {preset.id for preset in PRESETS}:
        raise HTTPException(400, "unknown preset")
    now = datetime.now(timezone.utc)
    recent = [stamp for stamp in _run_windows.get(owner, []) if stamp > now - timedelta(hours=1)]
    if len(recent) >= MAX_RUNS_PER_HOUR:
        raise HTTPException(429, "run creation rate limit exceeded")
    _run_windows[owner] = [*recent, now]
    return output(repository.create(PipelineRun(uuid4(), owner, preset_id=preset_id)))

@app.get("/api/runs")
def list_runs(x_anonymous_user_id: str | None = Header(default=None)) -> list[dict]:
    owner = owner_id(x_anonymous_user_id)
    return [output(run) for run in repository.list_for_owner(owner)]

@app.get("/api/runs/{run_id}")
def read_run(run_id: UUID, x_anonymous_user_id: str | None = Header(default=None)) -> dict:
    return output(get_run(owner_id(x_anonymous_user_id), run_id))

@app.post("/api/runs/{run_id}/advance")
def advance_run(run_id: UUID, x_anonymous_user_id: str | None = Header(default=None)) -> dict:
    owner = owner_id(x_anonymous_user_id)
    run = get_run(owner, run_id)
    if run.state not in {PipelineState.DRAFT, PipelineState.REVISION_REQUESTED}:
        raise HTTPException(409, "run is not ready to advance")
    preset = next(p for p in PRESETS if p.id == run.preset_id)
    for state in (PipelineState.QUEUED, PipelineState.GENERATING, PipelineState.AWAITING_REVIEW):
        run = repository.update_for_owner(owner, run_id, state)
    content = asdict(run_offline_sequence(preset))
    run = repository.attach_content(owner, run_id, content)
    return output(run)

@app.post("/api/runs/{run_id}/approve")
def approve_run(run_id: UUID, x_anonymous_user_id: str | None = Header(default=None)) -> dict:
    owner = owner_id(x_anonymous_user_id)
    run = get_run(owner, run_id)
    if run.state != PipelineState.AWAITING_REVIEW:
        raise HTTPException(409, "only runs awaiting review can be approved")
    return output(repository.update_for_owner(owner, run_id, PipelineState.APPROVED))

@app.post("/api/runs/{run_id}/reject")
def reject_run(run_id: UUID, body: Rejection, x_anonymous_user_id: str | None = Header(default=None)) -> dict:
    owner = owner_id(x_anonymous_user_id)
    get_run(owner, run_id)
    return output(repository.update_for_owner(owner, run_id, PipelineState.REJECTED, rejection_feedback=body.feedback))

@app.post("/api/runs/{run_id}/revise")
def revise_run(run_id: UUID, x_anonymous_user_id: str | None = Header(default=None)) -> dict:
    owner = owner_id(x_anonymous_user_id)
    get_run(owner, run_id)
    return output(repository.update_for_owner(owner, run_id, PipelineState.REVISION_REQUESTED))
