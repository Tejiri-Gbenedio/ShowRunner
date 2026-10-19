# Build the frontend with the exact Node version pinned by .nvmrc.
FROM node:22.11.0-bookworm-slim AS frontend-build
WORKDIR /app
COPY .nvmrc ./
RUN test "$(node --version | tr -d 'v')" = "$(tr -d '\r\n' < .nvmrc)"
COPY package.json package-lock.json ./
RUN npm ci
COPY frontend ./frontend
RUN npm run build

# Use the exact Python version pinned by .python-version. Node is copied from
# the build stage so the runtime image has both pinned runtimes without apt
# installing Debian's Python 3.11.
FROM python:3.12.7-slim-bookworm
WORKDIR /app
ENV PATH="/opt/venv/bin:/usr/local/bin:$PATH"
RUN apt-get update \
    && apt-get install -y --no-install-recommends make ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY .python-version .nvmrc ./
RUN test "$(python --version | awk '{print $2}')" = "$(tr -d '\r\n' < .python-version)"
COPY --from=frontend-build /usr/local/bin/node /usr/local/bin/node
COPY --from=frontend-build /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx
RUN test "$(node --version | tr -d 'v')" = "$(tr -d '\r\n' < .nvmrc)"
RUN node --version && npm --version
COPY pyproject.toml requirements.lock .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.lock
COPY package.json package-lock.json ./
COPY frontend ./frontend
COPY backend ./backend
COPY Makefile README.md .env.example ./
COPY --from=frontend-build /app/node_modules ./node_modules
COPY --from=frontend-build /app/dist ./dist
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
