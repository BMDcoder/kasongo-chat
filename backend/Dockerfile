# Use official Python slim image
FROM python:3.11-slim
WORKDIR /app
# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Copy app code
COPY . /app
# Expose port 8000 (for documentation, Docker Compose handles actual port mapping)
EXPOSE 8000
# Run uvicorn with port from env var (Railway sets $PORT, default 8000 locally)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
