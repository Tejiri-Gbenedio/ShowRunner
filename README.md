# Showrunner

Showrunner is an offline-first control room for running a faceless YouTube Shorts pipeline. The live demo currently runs **Real Gemini LLM for Topic and Script with a labelled mock fallback**. A judge can choose a channel, run a production, inspect the result, and explicitly approve or reject it before anything is considered publish-ready.

**Live demo:** https://showrunner-e1cz.onrender.com

The Render free tier sleeps when idle, so the first load can take 30 to 60 seconds.

## What is built

The pipeline has five typed agent stages:

1. **Topic Agent** — returns scored story ideas with hooks and reasons.
2. **Script & Scene Agent** — creates narration and timed scene directions.
3. **Production Agent** — creates placeholder asset records for mock image, audio, and video outputs; it does not create real media files.
4. **QA Agent** — checks total duration, each scene's duration, narration fit against the preset speaking rate, a hook in scene 1, and banned words/topics. It produces a score and a reason for every check.
5. **Packaging Agent** — prepares a YouTube-style title, description, tags, and upload metadata.

Two channel presets are included:

- **Last Signal** — survival-story thriller, tense cinematic tone.
- **The Quiet Discipline** — stoic philosophy, calm practical tone.

Every run is owner-scoped using an anonymous browser UUID. The backend enforces the human approval gate: a run must reach `awaiting_review`, then be explicitly approved before it can become `approved` (the publish-ready state). Rejections require feedback and can be revised.

## Honest demo limitations

The default storage is **in-memory**. Runs reset when the server restarts or when a free Render instance sleeps. This is intentional for the buildathon demo. The `SupabasePipelineRepository` interface/stub and SQL migration are wired for future work, but the Supabase repository is **not implemented** in this version.

External voice, image, and video services are not called by default. Set `LLM_PROVIDER=openai_compatible` with an OpenAI-compatible `LLM_BASE_URL`, `LLM_MODEL`, and backend-only `LLM_API_KEY` to enable real Topic and Script stages. Production, QA, and Packaging remain deterministic local stages. Runs expose `run_mode` (`real`/`mock`); daily-cap exhaustion or a configured provider fallback produces labelled mock output with a visible reason. Keep the cap bounded (`LLM_DAILY_CAP`, default 50) and never commit a provider key.

### Enabling the real LLM on Render

In the Render service environment settings, set `LLM_PROVIDER` to `openai_compatible`, provide the provider's base URL and model, and add the API key as the secret `LLM_API_KEY`. The key is never returned to the browser or written to logs. `LLM_TIMEOUT` defaults to 30 seconds and `LLM_MAX_TOKENS` defaults to 2000, with a small reservation for structured JSON. Each real agent call can make up to three total attempts; a run that still fails enters `failed` unless `LLM_FALLBACK_TO_MOCK=true`, in which case the affected agent uses a clearly labelled mock fallback. After 50 real runs per day, new runs use deterministic mock Topic and Script output and expose `mock_output=true` plus a reason.

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
5. Deploy and open the service URL shown by Render.

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
| LLM/script generation | Real OpenAI-compatible adapters when enabled; deterministic fallback otherwise |
| Voiceover/visuals/video | Deterministic file metadata; no external API calls |
| QA | Local deterministic checks |
| Packaging | Local deterministic metadata |
| Storage | In-memory repository by default |
| Supabase | Migration and incomplete repository stub only |
| YouTube upload | Not implemented; approval ends at `approved` |

## What else is in the box

- A single pipeline state machine and transition table, including `failed → queued` retry and `rejected → revision_requested → queued` revision flow.
- Per-owner and per-IP run-creation limits, with configurable trusted-proxy handling for forwarded client addresses.
- Configurable CORS origins.
- A GitHub Actions workflow that builds the Docker image and runs the offline Docker test command.
- A **View sample package** button containing a pre-written sample; it is not a live run and is not saved by the API.
- A readable review deck for topic, scenes, placeholder assets, QA warnings, and packaging, with a raw-data toggle.
- Current automated test counts: **43 backend tests** and **13 frontend tests**.

## Known issues

- The real-LLM path failed intermittently on the live demo during development. Diagnostics, tolerant parsing, retries, and a labelled mock fallback were added in response; provider behavior can still vary.
- `npm audit` reports warnings in development dependencies. They were not addressed in this buildathon scope.
- Storage is in memory, so runs reset when the server restarts or when the free Render service sleeps.

## How this was built with OmniRush

The repository history and development sessions followed this sequence:

1. **Architecture plan** — defined the five-agent pipeline, channel presets, adapter boundaries, offline-first requirement, human approval gate, and the five-step delivery plan. The initial design work was done in the main session; later implementation work was delegated in bounded sub-agent tasks.
2. **Foundation, Docker, and presets** — created the FastAPI/React foundation, pinned Python and Node versions, lockfiles, Docker image, offline test command, README, and the two presets. A sub-agent reviewed the initial structure. The Docker work later fixed a Python PEP 668 installation problem and ensured the image used the pinned Python 3.12 and Node 22 versions.
3. **Pipeline, state machine, and agents** — added owner-scoped runs, the transition table, repository interfaces, five typed agents, deterministic fixtures, approval/rejection flow, QA, and packaging. Sub-agents handled the state/repository and agent-contract portions. Real bugs found and fixed included the missing pytest configuration in the image and preset fields that had not been committed, which caused the first deployed QA path to fail.
4. **Web UI** — connected the React control room, anonymous browser UUID, polling, review actions, readable review deck, and sample package. Sub-agents handled the API client/UI workflow and frontend tests. A real bug found here was that the review panels read field names different from the API contract; the panels and fixtures were aligned.
5. **Deployment** — added the single Render Docker service, `/health`, Render `PORT` support, CORS and rate-limit configuration, and GitHub Actions. A Docker bug found during verification was that copying npm symlinks into the Python image turned them into regular files; the final image recreates the npm and npx links. The missing pytest configuration in the image was also fixed.
6. **Real LLM adapter** — added the OpenAI-compatible chat-completions adapter, JSON validation, retries, reasoning effort, token limits, daily cap, and labelled fallback. Sub-agents implemented the adapter and integration tests. The default remains mock and the offline Docker test never calls the network.
7. **Reliability and QA fixes** — added background execution, per-agent timeouts, stale-run sweeping, retry handling, tolerant model parsing, specific diagnostics, preset-based QA, topic-derived packaging, tag normalization, and real-preset HTTP coverage. The live-deployment issues found included generic LLM errors, stuck generating runs, malformed tags, wrong review-panel field names, and the missing QA preset fields; each was addressed with code or regression tests.

## Next steps

- Implement real production adapters for voice, images, and video assembly.
- Implement the Supabase repository behind the existing interface.
- Add publishing to YouTube after the approval gate.
- Add authentication and stronger identity controls.
- Add real analytics and trend data for topic scoring.
