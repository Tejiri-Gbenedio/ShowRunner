FROM node:22.11.0-bookworm-slim AS frontend-build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY frontend ./frontend
RUN npm run build

FROM node:22.11.0-bookworm-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-pip make && rm -rf /var/lib/apt/lists/*
COPY requirements.lock .
RUN pip3 install --no-cache-dir -r requirements.lock
COPY . .
COPY --from=frontend-build /app/dist ./dist
EXPOSE 8000
CMD ["python3", "-m", "uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
