# syntax=docker/dockerfile:1
#
#     docker compose up --build     first time
#     docker compose up             every time after
#
# Two stages. The first resolves dependencies; the second is the image that
# runs. Nothing is installed at run time, so a run needs no network.

FROM python:3.12-slim AS build

ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build

# Manifests before source, so a code change does not rebuild the dependencies.
COPY requirements.txt pyproject.toml ./
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install -r requirements.txt

COPY src/ ./src/
COPY README.md ./
RUN /opt/venv/bin/pip install --no-deps .


FROM python:3.12-slim

LABEL org.opencontainers.image.title="dataflywheel-selection" \
      org.opencontainers.image.version="1.0.0"

ENV PATH="/opt/venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY --from=build /opt/venv /opt/venv

WORKDIR /app
COPY data/example_input.jsonl ./data/

ENTRYPOINT ["select-data"]
