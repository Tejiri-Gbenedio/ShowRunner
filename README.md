# Showrunner

Showrunner is an offline-first agent pipeline for faceless YouTube Shorts channels. Step 1 establishes the reproducible foundation and two channel presets; later steps add the pipeline and approval workflow.

## Requirements

- Python 3.12.7
- Node.js 22.11.0 and npm
- Docker (optional)

## Local setup

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock
npm ci
```

Run the API with `uvicorn app.main:app --app-dir backend --reload`. It is available at http://localhost:8000 and its docs at http://localhost:8000/docs.

## Tests

After dependencies are installed, this command performs no network requests and is the canonical offline test command: `make test`.

## Docker

```bash
docker build -t showrunner .
docker run --rm -p 8000:8000 showrunner
```

## Storage and Supabase

The default storage selection is `memory`. Production storage will be selected with `STORAGE_BACKEND=supabase`; the Supabase service key remains backend-only. Required variable names are in `.env.example`. SQL migrations will be added before the Supabase repository is enabled.

## Deployment

The backend is intended for Render using the Dockerfile. The frontend is intended for Vercel using the repository root as the project and the frontend build configuration. A live demo URL will be added after deployment.
