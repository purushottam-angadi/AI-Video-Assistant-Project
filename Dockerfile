FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 user

RUN mkdir -p /app/downloads && chown -R user:user /app/downloads
RUN mkdir -p /app/vector_db && chown -R user:user /app/vector_db

USER user
ENV PATH="/home/user/.local/bin:$PATH"

COPY --chown=user requirements.txt ./
COPY --chown=user . .

RUN pip3 install --user -r requirements.txt

EXPOSE 7860

HEALTHCHECK CMD curl --fail http://localhost:7860/_stcore/health

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=7860", "--server.address=0.0.0.0"]