# FROM python:3.10-slim

# WORKDIR /app

# RUN apt-get update && apt-get install -y \
#     build-essential \
#     curl \
#     git \
#     && rm -rf /var/lib/apt/lists/*

# RUN useradd -m -u 1000 user

# RUN mkdir -p /app/downloads && chown -R user:user /app/downloads
# RUN mkdir -p /app/vector_db && chown -R user:user /app/vector_db

# USER user
# ENV PATH="/home/user/.local/bin:$PATH"

# COPY --chown=user requirements.txt ./
# COPY --chown=user . .

# RUN pip3 install --user -r requirements.txt

# EXPOSE 7860

# HEALTHCHECK CMD curl --fail http://localhost:7860/_stcore/health

# ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=7860", "--server.address=0.0.0.0"]


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
