# Showrunner

Showrunner is an offline-first control room for running a faceless YouTube Shorts pipeline. A judge can choose a channel, run a realistic mock production, inspect the result, and explicitly approve or reject it before anything is considered publish-ready.

**Live demo:** `https://YOUR-RENDER-URL.example.com` (replace this placeholder after deployment)

## What is built

The pipeline has five typed agent stages:

1. **Topic Agent** — returns scored story ideas with hooks and reasons.
2. **Script & Scene Agent** — creates narration and timed scene directions.
3. **Production Agent** — creates deterministic file-based mock voice/visual/video artifacts.
4. **QA Agent** — checks duration, scenes, narration, and production completeness.
5. **Packaging Agent** — prepares a YouTube-style title, description, tags, and upload metadata.

Two channel presets are included:

- **Last Signal** — survival-story thriller, tense cinematic tone.
- **The Quiet Discipline** — stoic philosophy, calm practical tone.

Every run is owner-scoped using an anonymous browser UUID. The backend enforces the human approval gate: a run must reach `awaiting_review`, then be explicitly approved before it can become `approved` (the publish-ready state). Rejections require feedback and can be revised.

## Honest demo limitations

The default storage is **in-memory**. Runs reset when the server restarts or when a free Render instance sleeps. This is intentional for the buildathon demo. The `SupabasePipelineRepository` interface/stub and SQL migration are wired for future work, but the Supabase repository is **not implemented** in this version.

External LLM, voice, image, and video services are not called by default. The mock adapters are deterministic and handcrafted for both presets. Real provider adapters can be added behind the existing contracts later.

## Local setup

Requirements: Python 3.12.7, Node.js 22.11.0, npm, and optionally Docker. Pins are recorded in `.python-version` and `.nvmrc`.

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock
npm ci
```

Run the backend:

```bash
uvicorn app.main:app --app-dir backend --reload --port "${PORT:-8000}"
```

Run the separate frontend development server in another terminal:

```bash
VITE_API_URL=http://localhost:8000 npm run dev
```

Or build the frontend and run the combined app through FastAPI:

```bash
npm run build
uvicorn app.main:app --app-dir backend --port "${PORT:-8000}"
```

Open `http://localhost:8000` for the combined app and `/docs` for the API documentation.

## Tests

The canonical offline test command is:

```bash
make test
```

It runs the backend suite and frontend suite without making network requests. The frontend production build is:

```bash
npm run build
```

## Docker

Dependencies are downloaded while building the image. After the image is built, the test command requires no network:

```bash
docker build -t showrunner .
docker run --rm --network none showrunner make test
docker run --rm -p 8000:8000 showrunner
```

The image checks Python and Node against the repository pins, includes `make`, both test suites, and serves the built frontend plus `/api` from one origin. To verify Render-style port handling:

```bash
docker run --rm -e PORT=18000 -p 18000:18000 showrunner
```

Then visit `http://localhost:18000/health` and `http://localhost:18000`.

## Render deployment

`render.yaml` defines a single free Docker web service named `showrunner` with `/health` as its health check. Render supplies `PORT`; the container uses it and defaults to `8000` locally.

1. Push this repository to GitHub.
2. In Render, choose **New → Blueprint** and select the repository.
3. Review the service created from `render.yaml`.
4. Set `CORS_ORIGINS` to the deployed origin if a separate frontend is used; the combined Docker service normally needs no cross-origin frontend.
5. Deploy and replace the live-demo placeholder at the top of this README.

No secrets are committed. Supabase keys, if enabled in a future version, belong in Render environment settings only.

## Project structure

```text
backend/app/           FastAPI app, state machine, repositories, agents
backend/tests/         API, state, owner isolation, and agent tests
frontend/src/          React control room, API client, review deck, tests
supabase/migrations/   RLS-enabled schema migration for future storage
Dockerfile              Reproducible Node/Python test and runtime image
render.yaml             Render Docker service definition
Makefile                Canonical offline test command
```

## Mock versus real

| Area | Current implementation |
|---|---|
| Topic discovery | Deterministic handcrafted fixtures |
| LLM/script generation | Mock typed adapters |
| Voiceover/visuals/video | Deterministic file metadata; no external API calls |
| QA | Local deterministic checks |
| Packaging | Local deterministic metadata |
| Storage | In-memory repository by default |
| Supabase | Migration and incomplete repository stub only |
| YouTube upload | Not implemented; approval ends at `approved` |
