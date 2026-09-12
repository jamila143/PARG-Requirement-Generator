# Single-container build: compiles the React frontend, then serves it AND
# the FastAPI backend from one Python process on one port. This is what lets
# the whole thing be reachable at one public URL instead of needing two
# separate hosted services.

# ---- Stage 1: build the React frontend ----
FROM node:20-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: the actual app ----
FROM python:3.11-slim
WORKDIR /app

# System deps some Python packages need to build
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY backend/data ./data
COPY backend/models ./models

# The compiled frontend from stage 1 -- app/main.py serves this at "/"
# whenever this folder exists (see the bottom of main.py).
COPY --from=frontend-build /frontend/dist ./frontend_dist

# Hugging Face Spaces (Docker SDK) expects the app to listen on 7860.
ENV PORT=7860
EXPOSE 7860

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
