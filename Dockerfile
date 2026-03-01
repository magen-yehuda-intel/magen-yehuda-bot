FROM python:3.12-slim

# System deps: curl for Oref/API calls, fonts for PIL map generation
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    fonts-dejavu-core \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY scripts/ scripts/
COPY references/ references/
COPY config.example.json config.example.json
COPY ctl.sh ctl.sh

# Create state and docs dirs (mounted as volumes in production)
RUN mkdir -p state docs secrets

# Entrypoint: bootstrap config from env vars if needed, then run command
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh
ENTRYPOINT ["/docker-entrypoint.sh"]

# Default: run watcher in foreground
CMD ["bash", "ctl.sh", "start-foreground"]
