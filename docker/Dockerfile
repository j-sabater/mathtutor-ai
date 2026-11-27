# Dockerfile para MathTutor-AI
FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy source code first (needed for setuptools find_packages)
COPY src/ ./src/
COPY specs/ ./specs/
COPY scripts/ ./scripts/
COPY pyproject.toml .

# Install Python dependencies
RUN pip install --no-cache-dir ".[dev,anthropic,langgraph]"

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["python", "-m", "mathtutor.api.main"]
