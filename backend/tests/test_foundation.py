from fastapi.testclient import TestClient
from app.main import app

def test_health() -> None:
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_both_channel_presets_are_available() -> None:
    presets = TestClient(app).get("/api/presets").json()
    assert {preset["id"] for preset in presets} == {"survival-thriller", "stoic-philosophy"}
    assert all(preset["quality_rules"] for preset in presets)
