FROM node:22-alpine AS frontend-builder

WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .
COPY --from=frontend-builder /frontend/dist ./frontend/dist

# Expose FastAPI Web UI / Gateway API port and OAuth callback port
EXPOSE 5678

# Run the gateway using uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5678"]
