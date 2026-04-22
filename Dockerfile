FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        chromium \
        chromium-driver \
        fonts-nanum \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /app

RUN python -m pip install --upgrade pip \
    && pip install --no-cache-dir \
        discord.py==2.7.1 \
        pymysql \
        selenium \
        pillow \
        requests

CMD ["python", "kbo.py"]
