ARG PYTHON_VERSION=3.10.6
ARG POETRY_VERSION=1.1.15

FROM python:$PYTHON_VERSION-slim AS builder
ENV \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1
ENV \
    POETRY_VERSION=$POETRY_VERSION \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential gcc curl && \
    rm -rf /var/lib/apt/lists/*

RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python -
ENV PATH="$POETRY_HOME/bin:$PATH"

ENV VIRTUAL_ENV=/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN python -m venv $VIRTUAL_ENV && \
    /venv/bin/python -m pip install --upgrade pip

COPY pyproject.toml poetry.lock ./
# Needs `export DOCKER_BUILDKIT=1` and have Docker buildkit installed to work
RUN --mount=type=cache,target=/root/.cache poetry export -f requirements.txt | /venv/bin/pip install -r /dev/stdin --no-deps


FROM python:$PYTHON_VERSION-slim AS runner

ENV \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1

RUN useradd --create-home appuser
USER appuser

COPY --from=builder /venv /venv

WORKDIR /home/appuser/bot
ENV PATH="/venv/bin:$PATH"
ENV PYTHONPATH=/home/appuser

COPY res/ ./res/
COPY bot.py .
CMD python bot.py