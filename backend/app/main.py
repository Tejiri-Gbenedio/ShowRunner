from fastapi import FastAPI
from app.presets import list_presets

app = FastAPI(title="Showrunner API", version="0.1.0")

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "showrunner"}

@app.get("/api/presets")
def presets() -> list[dict]:
    return list_presets()
