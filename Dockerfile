FROM python:3.13-slim
ARG GO_VERSION=1.24.6
ARG TARGETARCH=amd64

ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    ca-certificates \
    git \
    gcc \
    libpq-dev \
    procps \
&& curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - \
&& apt-get install -y nodejs \
&& npm install -g @anthropic-ai/claude-code@1.0.90 \
&& rm -rf /var/lib/apt/lists/*

RUN curl -L -s https://go.dev/dl/go${GO_VERSION}.linux-${TARGETARCH}.tar.gz | tar -C /usr/local -xz
ENV PATH=$PATH:/root/go/bin:/usr/local/go/bin

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY src/ ./src/
COPY README.md .

RUN uv venv && uv pip install -r pyproject.toml

CMD ["uv", "run", "uvicorn", "ai_guardian_remediation.main:app", "--host", "0.0.0.0", "--port", "8588"]
