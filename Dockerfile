FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r neko && useradd -r -g neko -d /app neko

# Copy requirements first (Docker layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p downloads thumbnails logs && chown -R neko:neko /app

USER neko

# Run bot
CMD ["python", "AcxNeko.py"]