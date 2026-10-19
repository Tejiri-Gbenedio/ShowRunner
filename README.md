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

For the separate frontend development server, set `VITE_API_URL=http://localhost:8000` in a frontend environment file and run `npm run dev -- --config frontend/vite.config.ts`. The Docker image serves the built frontend and API together from http://localhost:8000.

## Tests

After dependencies are installed, this command performs no network requests and is the canonical offline test command: `make test`.

## Docker

```bash
docker build -t showrunner .
docker run --rm --network none showrunner make test
docker run --rm -p 8000:8000 showrunner
```

## Storage and Supabase

The default storage selection is `memory`. Production storage will be selected with `STORAGE_BACKEND=supabase`; the Supabase service key remains backend-only. Required variable names are in `.env.example` and must only be loaded by the backend. Apply `supabase/migrations/0001_initial.sql` in the Supabase SQL Editor, or with the Supabase CLI after linking your project:

```bash
supabase link --project-ref YOUR_PROJECT_REF
supabase db push
```

The migration enables Row Level Security on `pipeline_runs` and intentionally creates no public policies. Backend access is expected to use the Supabase service key.

## Offline Docker tests

The image contains Node.js, Python, `make`, frontend dependencies, and backend dependencies. Build it while connected, then the test run needs no network:

```bash
docker build -t showrunner .
docker run --rm --network none showrunner make test
docker run --rm -p 8000:8000 showrunner
```

The Docker build checks that the Python and Node versions inside the image match `.python-version` and `.nvmrc`. The image uses Python 3.12.7 as its runtime, a virtual environment for locked Python dependencies, Node 22.11.0 copied from the pinned frontend build stage, and includes `make` plus both test suites. Dependencies are fetched during `docker build`; the test command itself runs with networking disabled.

## Deployment

The backend is intended for Render using the Dockerfile. The frontend is intended for Vercel using the repository root as the project and the frontend build configuration. A live demo URL will be added after deployment.
