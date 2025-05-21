ARG PYTHON_VERSION=3.12.3

FROM python:$PYTHON_VERSION-slim

ENV \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential gcc curl && \
    rm -rf /var/lib/apt/lists/*

RUN useradd --create-home appuser
USER appuser

WORKDIR /home/appuser/bot

ENV PYTHONPATH=/home/appuser

COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install --require-hashes -r requirements.txt

COPY res/ ./res/
COPY *.py ./

CMD ["python", "bot.py"]

