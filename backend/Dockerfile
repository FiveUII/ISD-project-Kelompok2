# Backend Dockerfile — production image
# No --reload in production (D-08); override.yml adds --reload for dev
FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Run Alembic migration then start uvicorn (production: no --reload)
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
