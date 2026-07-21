FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD streamlit run appui.py \
    --server.port=$PORT \
    --server.address=0.0.0.0 \
    --server.fileWatcherType=none \
    --server.maxUploadSize=500 \
    --browser.gatherUsageStats=false