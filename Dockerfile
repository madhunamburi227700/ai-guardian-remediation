FROM ubuntu:24.04

ARG GO_VERSION=1.24.6
ARG TARGETARCH=amd64

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1

# ---------------- OS packages ----------------
RUN apt-get update && apt-get install -y \
    software-properties-common \
    curl \
    gnupg \
    ca-certificates \
    git \
    gcc \
    libpq-dev \
    procps \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y \
        python3.13 \
        python3.13-venv \
        python3.13-dev \
    && rm -rf /var/lib/apt/lists/*

# Set python 3.13 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.13 1

# ---------------- Node.js ----------------
RUN curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g @anthropic-ai/claude-code@1.0.105 \
    && rm -rf /var/lib/apt/lists/*

# ---------------- Go ----------------
RUN curl -L -s https://go.dev/dl/go${GO_VERSION}.linux-${TARGETARCH}.tar.gz \
    | tar -C /usr/local -xz

ENV PATH=$PATH:/usr/local/go/bin

# ---------------- Python tooling ----------------
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python \
    && pip install --no-cache-dir uv

# ---------------- Non-root user ----------------
RUN groupadd -r appuser && useradd -r -g appuser -m appuser

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY src/ ./src/
COPY README.md .

RUN chown -R appuser:appuser /app

USER appuser

# Create venv and install dependencies
RUN uv venv && uv pip install -r pyproject.toml

CMD ["uv", "run", "uvicorn", "ai_guardian_remediation.main:app", "--host", "0.0.0.0", "--port", "8588"]
