# 

FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

HEALTHCHECK CMD curl --fail http://localhost:$PORT/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=$PORT", "--server.address=0.0.0.0"]
