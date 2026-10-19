from uuid import UUID, uuid4
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import _ip_windows, _run_windows, app, client_ip, repository, server_port
from app.pipeline import PipelineState

client = TestClient(app)

def reset() -> None:
    repository._runs.clear()
    _run_windows.clear()
    _ip_windows.clear()

def wait_for_state(run_id, headers, state):
    import time
    for _ in range(100):
        result = client.get(f"/api/runs/{run_id}", headers=headers).json()
        if result["state"] == state:
            return result
        time.sleep(0.01)
    raise AssertionError(f"run did not reach {state}: {result}")

def test_owner_isolation_for_read_list_and_approval() -> None:
    reset()
    owner_a, owner_b = str(uuid4()), str(uuid4())
    created = client.post("/api/runs?preset_id=survival-thriller", headers={"X-Anonymous-User-ID": owner_a}).json()
    run_id = created["id"]
    assert client.get("/api/runs", headers={"X-Anonymous-User-ID": owner_b}).json() == []
    assert client.get(f"/api/runs/{run_id}", headers={"X-Anonymous-User-ID": owner_b}).status_code == 404
    assert client.post(f"/api/runs/{run_id}/approve", headers={"X-Anonymous-User-ID": owner_b}).status_code == 404

def test_offline_pipeline_and_rejection_revision_approval() -> None:
    reset()
    owner = str(uuid4())
    headers = {"X-Anonymous-User-ID": owner}
    run = client.post("/api/runs?preset_id=stoic-philosophy", headers=headers).json()
    run_id = run["id"]
    advanced = client.post(f"/api/runs/{run_id}/advance", headers=headers)
    assert advanced.status_code == 200
    assert advanced.json()["state"] in {"queued", "generating"}
    wait_for_state(run_id, headers, "awaiting_review")
    rejected = client.post(f"/api/runs/{run_id}/reject", headers=headers, json={"feedback": "Make the takeaway more actionable."})
    assert rejected.json()["rejection_feedback"] == "Make the takeaway more actionable."
    assert rejected.json()["state"] == "rejected"
    assert client.post(f"/api/runs/{run_id}/revise", headers=headers).json()["state"] == "revision_requested"
    client.post(f"/api/runs/{run_id}/advance", headers=headers)
    assert wait_for_state(run_id, headers, "awaiting_review")["state"] == "awaiting_review"
    assert client.post(f"/api/runs/{run_id}/approve", headers=headers).json()["state"] == "approved"

def test_api_run_payload_contains_review_deck_contract() -> None:
    reset()
    owner = str(uuid4())
    headers = {"X-Anonymous-User-ID": owner}
    run = client.post("/api/runs?preset_id=survival-thriller", headers=headers).json()
    client.post(f"/api/runs/{run['id']}/advance", headers=headers)
    payload = wait_for_state(run["id"], headers, "awaiting_review")["content"]
    assert payload["production"]["scenes"][0]["asset_key"]
    assert payload["qa"]["score"] >= 0
    assert all("label" in check and "passed" in check for check in payload["qa"]["check_results"])
    assert payload["package"]["title"]
    assert payload["package"]["description"]
    assert payload["package"]["tags"]


def test_api_exposes_mock_fallback_metadata(monkeypatch):
    reset()
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    from app.agents import run_offline_sequence
    monkeypatch.setattr("app.main.run_pipeline", lambda preset: (run_offline_sequence(preset), "mock", "real LLM failed; mock fallback used (topic: provider unavailable)"))
    owner = str(uuid4())
    headers = {"X-Anonymous-User-ID": owner}
    run = client.post("/api/runs?preset_id=survival-thriller", headers=headers).json()
    client.post(f"/api/runs/{run['id']}/advance", headers=headers)
    result = wait_for_state(run["id"], headers, "awaiting_review")
    assert result["run_mode"] == "mock"
    assert result["mock_output"] is True
    assert result["mock_output_reason"].startswith("real LLM failed; mock fallback used")

def test_rate_limit_creation() -> None:
    reset()
    owner = str(uuid4())
    headers = {"X-Anonymous-User-ID": owner}
    for _ in range(10):
        assert client.post("/api/runs?preset_id=survival-thriller", headers=headers).status_code == 201
    assert client.post("/api/runs?preset_id=survival-thriller", headers=headers).status_code == 429

def test_invalid_owner_uuid_is_rejected() -> None:
    reset()
    assert client.get("/api/runs", headers={"X-Anonymous-User-ID": "not-a-uuid"}).status_code == 400

def test_ip_rate_limit_is_configurable(monkeypatch) -> None:
    reset()
    monkeypatch.setenv("MAX_RUNS_PER_OWNER_PER_HOUR", "100")
    monkeypatch.setenv("MAX_RUNS_PER_IP_PER_HOUR", "2")
    for index in range(2):
        assert client.post("/api/runs?preset_id=survival-thriller", headers={"X-Anonymous-User-ID": str(uuid4()), "X-Forwarded-For": "203.0.113.10, 10.0.0.1"}).status_code == 201
    assert client.post("/api/runs?preset_id=survival-thriller", headers={"X-Anonymous-User-ID": str(uuid4()), "X-Forwarded-For": "203.0.113.10, 10.0.0.1"}).status_code == 429


def test_ip_rate_limit_uses_last_forwarded_entry_to_prevent_bypass(monkeypatch) -> None:
    reset()
    monkeypatch.setenv("MAX_RUNS_PER_OWNER_PER_HOUR", "100")
    monkeypatch.setenv("MAX_RUNS_PER_IP_PER_HOUR", "1")
    headers = {"X-Forwarded-For": "198.51.100.10, 10.0.0.1"}
    assert client_ip(headers["X-Forwarded-For"], None) == "10.0.0.1"
    assert client.post("/api/runs?preset_id=survival-thriller", headers={**headers, "X-Anonymous-User-ID": str(uuid4())}).status_code == 201
    assert client.post("/api/runs?preset_id=survival-thriller", headers={"X-Anonymous-User-ID": str(uuid4()), "X-Forwarded-For": "203.0.113.99, 10.0.0.1"}).status_code == 429


def test_proxy_hops_and_malformed_port_have_safe_fallbacks(monkeypatch) -> None:
    monkeypatch.setenv("TRUSTED_PROXY_HOPS", "2")
    assert client_ip("198.51.100.10, 10.0.0.1, 10.0.0.2", None) == "10.0.0.1"
    assert client_ip("198.51.100.10", "10.0.0.9") == "10.0.0.9"
    monkeypatch.setenv("PORT", "not-a-port")
    assert server_port() == 8000
    monkeypatch.setenv("PORT", "9187")
    assert server_port() == 9187

def test_revision_endpoint_requires_a_rejection(monkeypatch) -> None:
    reset()
    owner = str(uuid4())
    headers = {"X-Anonymous-User-ID": owner}
    run = client.post("/api/runs?preset_id=survival-thriller", headers=headers).json()
    assert client.post(f"/api/runs/{run['id']}/revise", headers=headers).status_code == 409

def test_agent_exception_is_recorded_as_failed(monkeypatch) -> None:
    reset()
    owner = str(uuid4())
    headers = {"X-Anonymous-User-ID": owner}
    run = client.post("/api/runs?preset_id=survival-thriller", headers=headers).json()
    def fail(_preset):
        from app.agents import AgentExecutionError
        raise AgentExecutionError("production", RuntimeError("fixture failure"))
    monkeypatch.setattr("app.main.run_offline_sequence", fail)
    client.post(f"/api/runs/{run['id']}/advance", headers=headers)
    result = wait_for_state(run["id"], headers, "failed")
    assert result["state"] == "failed"
    assert result["failed_agent"] == "production"
    assert result["error"] == "fixture failure"

def test_advance_returns_background_generating_state_and_duplicate_is_safe(monkeypatch):
    reset()
    owner = str(uuid4()); headers = {"X-Anonymous-User-ID": owner}
    run = client.post("/api/runs?preset_id=survival-thriller", headers=headers).json()
    import threading
    gate = threading.Event()
    monkeypatch.setattr("app.main.run_offline_sequence", lambda preset: (gate.wait(1), None)[1])
    first = client.post(f"/api/runs/{run['id']}/advance", headers=headers).json()
    second = client.post(f"/api/runs/{run['id']}/advance", headers=headers)
    assert first["state"] == "generating"
    assert second.status_code == 409
    gate.set()

def test_sweeper_marks_old_generating_run_failed(monkeypatch):
    reset(); owner = uuid4(); run = repository.create(__import__("app.pipeline", fromlist=["PipelineRun"]).PipelineRun(uuid4(), owner))
    repository.update_for_owner(owner, run.id, PipelineState.QUEUED)
    generating = repository.update_for_owner(owner, run.id, PipelineState.GENERATING)
    repository._runs[run.id] = __import__("dataclasses").replace(generating, updated_at=datetime.now(timezone.utc) - timedelta(seconds=20))
    monkeypatch.setenv("PIPELINE_GENERATING_TIMEOUT_SECONDS", "1")
    assert client.get(f"/api/runs/{run.id}", headers={"X-Anonymous-User-ID": str(owner)}).json()["state"] == "failed"

def test_failed_retry_requeues_and_runs_pipeline():
    reset(); owner = str(uuid4()); headers = {"X-Anonymous-User-ID": owner}
    run = client.post("/api/runs?preset_id=survival-thriller", headers=headers).json()
    repository.update_for_owner(UUID(owner), UUID(run["id"]), PipelineState.QUEUED)
    repository.update_for_owner(UUID(owner), UUID(run["id"]), PipelineState.GENERATING)
    repository.update_for_owner(UUID(owner), UUID(run["id"]), PipelineState.FAILED, error="temporary")
    retried = client.post(f"/api/runs/{run['id']}/retry", headers=headers).json()
    assert retried["state"] == "generating"
    assert wait_for_state(run["id"], headers, "awaiting_review")["content"]
