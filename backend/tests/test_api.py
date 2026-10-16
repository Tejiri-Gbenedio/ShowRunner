from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.main import _run_windows, app, repository

client = TestClient(app)

def reset() -> None:
    repository._runs.clear()
    _run_windows.clear()

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
    assert advanced.json()["state"] == "awaiting_review"
    rejected = client.post(f"/api/runs/{run_id}/reject", headers=headers, json={"feedback": "Make the takeaway more actionable."})
    assert rejected.json()["rejection_feedback"] == "Make the takeaway more actionable."
    assert rejected.json()["state"] == "rejected"
    assert client.post(f"/api/runs/{run_id}/revise", headers=headers).json()["state"] == "revision_requested"
    assert client.post(f"/api/runs/{run_id}/advance", headers=headers).json()["state"] == "awaiting_review"
    assert client.post(f"/api/runs/{run_id}/approve", headers=headers).json()["state"] == "approved"

def test_rate_limit_creation() -> None:
    reset()
    owner = str(uuid4())
    headers = {"X-Anonymous-User-ID": owner}
    for _ in range(5):
        assert client.post("/api/runs?preset_id=survival-thriller", headers=headers).status_code == 201
    assert client.post("/api/runs?preset_id=survival-thriller", headers=headers).status_code == 429
