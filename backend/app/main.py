from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
import os
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.agents import AgentExecutionError, run_pipeline, run_offline_sequence
from app.pipeline import InMemoryPipelineRepository, PipelineRun, PipelineState
from app.presets import PRESETS, list_presets

app = FastAPI(title="Showrunner API", version="0.2.0")
cors_origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
repository = InMemoryPipelineRepository()
_run_windows: dict[UUID, list[datetime]] = {}
_ip_windows: dict[str, list[datetime]] = {}

_dist = Path(__file__).resolve().parents[2] / "dist"
if (_dist / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=_dist / "assets"), name="assets")

class Rejection(BaseModel):
    feedback: str = Field(min_length=1, max_length=1000)

def owner_id(value: str | None) -> UUID:
    try:
        return UUID(value or "")
    except (ValueError, AttributeError) as exc:
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

def server_port() -> int:
    """Return a valid listening port, with the local/Render default of 8000."""
    try:
        value = int(os.getenv("PORT", "8000"))
    except (TypeError, ValueError):
        return 8000
    return value if 1 <= value <= 65535 else 8000


def trusted_proxy_hops() -> int:
    try:
        value = int(os.getenv("TRUSTED_PROXY_HOPS", "1"))
    except (TypeError, ValueError):
        return 1
    return value if value >= 1 else 1


def client_ip(x_forwarded_for: str | None, x_real_ip: str | None) -> str:
    """Resolve an address without allowing arbitrary XFF prefixes to bypass limits."""
    if x_forwarded_for:
        addresses = [part.strip() for part in x_forwarded_for.split(",") if part.strip()]
        hops = trusted_proxy_hops()
        if len(addresses) >= hops:
            return addresses[-hops]
    return (x_real_ip or "unknown").strip() or "unknown"

def limit(name: str, default: int) -> int:
    try: return max(0, int(os.getenv(name, str(default))))
    except ValueError: return default

@app.get("/", include_in_schema=False)
def frontend_root():
    p=Path(__file__).resolve().parents[2]/"dist"/"index.html"
    if p.exists(): return FileResponse(p)
    raise HTTPException(404, "frontend build not found")

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "showrunner"}

@app.get("/api/presets")
def presets() -> list[dict]:
    return list_presets()

@app.post("/api/runs", status_code=201)
def create_run(preset_id: str, x_anonymous_user_id: str | None = Header(default=None), x_forwarded_for: str | None = Header(default=None), x_real_ip: str | None = Header(default=None)) -> dict:
    owner = owner_id(x_anonymous_user_id)
    if preset_id not in {preset.id for preset in PRESETS}:
        raise HTTPException(400, "unknown preset")
    now = datetime.now(timezone.utc)
    recent = [stamp for stamp in _run_windows.get(owner, []) if stamp > now - timedelta(hours=1)]
    if len(recent) >= limit("MAX_RUNS_PER_OWNER_PER_HOUR", 10):
        raise HTTPException(429, "run creation rate limit exceeded")
    _run_windows[owner] = [*recent, now]
    ip = client_ip(x_forwarded_for, x_real_ip)
    ip_recent = [stamp for stamp in _ip_windows.get(ip, []) if stamp > now - timedelta(hours=1)]
    if len(ip_recent) >= limit("MAX_RUNS_PER_IP_PER_HOUR", 30): raise HTTPException(429, "run creation rate limit exceeded")
    _ip_windows[ip] = [*ip_recent, now]
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
    for state in (PipelineState.QUEUED, PipelineState.GENERATING): run = repository.update_for_owner(owner, run_id, state)
    try:
        if os.getenv("LLM_PROVIDER", "mock").lower() == "mock":
            result, run_mode, mock_reason = run_offline_sequence(preset), "mock", None
        else:
            result, run_mode, mock_reason = run_pipeline(preset)
        content = asdict(result)
    except AgentExecutionError as exc:
        real_attempt = os.getenv("LLM_PROVIDER", "mock").lower() != "mock"
        return output(repository.update_for_owner(owner, run_id, PipelineState.FAILED, error=str(exc), failed_agent=exc.agent, run_mode="real" if real_attempt else "mock", mock_output=not real_attempt))
    run = repository.update_for_owner(owner, run_id, PipelineState.AWAITING_REVIEW, run_mode=run_mode, mock_output=(run_mode == "mock"), mock_output_reason=mock_reason)
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
    run = get_run(owner, run_id)
    if run.state != PipelineState.REJECTED: raise HTTPException(409, "a rejection with feedback is required before requesting revision")
    return output(repository.update_for_owner(owner, run_id, PipelineState.REVISION_REQUESTED))
