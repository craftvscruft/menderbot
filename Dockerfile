
# syntax=docker/dockerfile:1.4
FROM --platform=$BUILDPLATFORM python:3.11-slim AS builder

WORKDIR /app
COPY pyproject.toml /app
RUN mkdir -p menderbot && echo "__version__ = '0.0.0'" >>  menderbot/__init__.py 

RUN apt-get update && \
    apt-get -y install gcc git && \
    rm -rf /var/lib/apt/lists/*

RUN --mount=type=cache,target=/root/.cache/pip \
    pip3 install -e . && python3 -c "import nltk; nltk.download('punkt')"

COPY setup.cfg /app
COPY menderbot/ /app/menderbot/

run pip3 install -e .

WORKDIR /target

ENTRYPOINT ["menderbot"]
