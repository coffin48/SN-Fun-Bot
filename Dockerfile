# Multi-stage build untuk optimalisasi size dan speed
FROM python:3.11-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first untuk layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

# Copy installed packages dari builder stage
COPY --from=builder /root/.local /root/.local

# Set working directory
WORKDIR /app

# Copy application code
COPY . .

# Set environment variables for proper encoding
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8

# Expose port for Railway
EXPOSE 8080

# Run auto-migration first, then start the bot
CMD ["sh", "-c", "python scripts/auto_migrate_startup.py && python core/main.py"]
