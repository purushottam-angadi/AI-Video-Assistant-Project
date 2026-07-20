FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt ./
ARG CACHE_BUST=1
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

EXPOSE 8080

HEALTHCHECK CMD bash -c "curl --fail http://localhost:$PORT/_stcore/health || exit 1"

CMD streamlit run appui.py \
    --server.port=$PORT \
    --server.address=0.0.0.0 \
    --server.fileWatcherType=none \
    --server.maxUploadSize=500 \
    --browser.gatherUsageStats=false