# Stage 1: Build Rust native module (vibe_engine)
FROM rust:1.85-slim-bookworm AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-dev python3-pip python3-numpy patchelf && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir maturin numpy

COPY vibe_engine_rs/ ./vibe_engine_rs/
WORKDIR /build/vibe_engine_rs
RUN maturin build --release --out /build/wheels

# Stage 2: Python runtime
FROM python:3.13-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-numpy curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --from=builder /build/wheels /tmp/wheels
RUN pip install --no-cache-dir /tmp/wheels/*.whl && rm -rf /tmp/wheels

COPY . .

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
