FROM python:3.11-slim-bookworm

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    build-essential \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create application directories with proper permissions
RUN mkdir -p /app/src /app/workspace /app/logs /app/cache /app/.cache && \
    chmod -R 755 /app && \
    chown -R root:root /app

# Copy only necessary files (исключая .git благодаря .dockerignore)
COPY requirements.txt .
COPY src/ ./src/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create user with proper permissions
RUN useradd -m appuser && \
    chown -R appuser:appuser /app/workspace /app/logs /app/cache /app/.cache /app/src

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    CODE_WORK_DIR=/app/workspace \
    LOG_LEVEL=INFO

# Switch to non-root user
USER appuser

CMD ["python", "src/main.py"]

LABEL org.opencontainers.image.title="YandexGPT Autogen Telegram Bot" \
      org.opencontainers.image.description="Multi-agent Telegram bot using YandexGPT and pyautogen" \
      org.opencontainers.image.authors="Vladimir Baranov vl_1909@mail.ru" \
      org.opencontainers.image.url="https://github.com/Vladimir-1909/autogen_telegram_bot" \
      org.opencontainers.image.source="https://github.com/Vladimir-1909/autogen_telegram_bot" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.created="2025-11-26"
