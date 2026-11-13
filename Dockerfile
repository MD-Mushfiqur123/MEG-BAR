# ==============================================================================
# MEG-BAR: Universal Zero-Dependency Containerized Reproduction Engine
# Molecular Expert Grafting with Binding Affinity Router Re-anchoring
# Author: Md Mushfiqur Rahim | ORCID: 0009-0003-1021-685X
# Prior Zenodo Foundation DOI: 10.5281/zenodo.23841930
# ==============================================================================

FROM python:3.12-slim

LABEL maintainer="Md Mushfiqur Rahim <20mahin2020@gmail.com>"
LABEL description="MEG-BAR: PhD Dissertation & Nature Biotechnology Reproduction Container"
LABEL version="1.0.0"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install required Python scientific packages
RUN pip install --no-cache-dir \
    numpy>=1.26.0 \
    matplotlib>=3.8.0 \
    pytest>=8.0.0

# Copy all project source code, data, assets, and scripts
COPY . /app

# Ensure entrypoint and reproduction scripts are executable
RUN chmod +x /app/scripts/*.py

# Expose port for interactive visualizer and defense presentation server
EXPOSE 8080

# Healthcheck to verify HTTP server responsiveness
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/visualizer/index.html || exit 1

# Default execution: Run complete 8-stage one-click reproduction pipeline, then serve web UI
CMD ["sh", "-c", "python scripts/one_click_reproduce.py && echo '\n[SERVER] Serving MEG-BAR Visualizer & Slides at http://0.0.0.0:8080 ...' && python -m http.server 8080"]
