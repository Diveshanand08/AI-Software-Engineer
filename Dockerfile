FROM python:3.11-slim

# Install git (required for cloning repos)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    CHROMA_DIR=/app/chroma_db \
    CLONE_DIR=/app/_cloned_repos

# Expose Chroma volume so data persists across container restarts
VOLUME ["/app/chroma_db"]

# Expose backend API port
EXPOSE 8000

# Run uvicorn
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
