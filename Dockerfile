
# FROM python:3.10-slim

# WORKDIR /app

# # Install system dependencies (FFmpeg needed for yt-dlp conversions)
# RUN apt-get update && apt-get install -y \
#     build-essential \
#     curl \
#     git \
#     ffmpeg \
#     && rm -rf /var/lib/apt/lists/*

# # Copy requirements and install
# COPY requirements.txt ./
# RUN pip3 install --no-cache-dir -r requirements.txt

# # Copy app code
# COPY . .

# EXPOSE 8080

# # Healthcheck using $PORT
# HEALTHCHECK CMD curl --fail http://localhost:$PORT/_stcore/health || exit 1

# # Use shell form so $PORT expands correctly
# ENTRYPOINT streamlit run app.py --server.port=$PORT --server.address=0.0.0.0


# RAILWAY:
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies (FFmpeg needed for yt-dlp conversions)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Expose the port (Railway will map $PORT)
EXPOSE 8080

# Healthcheck (shell form so $PORT expands)
HEALTHCHECK CMD bash -c "curl --fail http://localhost:$PORT/_stcore/health || exit 1"

# Use CMD so Railway can override if needed
CMD streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
