FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    ca-certificates \
    git \
    gcc \
    libpq-dev \
&& curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - \
&& apt-get install -y nodejs \
&& npm install -g @anthropic-ai/claude-code \
&& rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY src/ ./src/
COPY README.md .

RUN uv venv && uv pip install -r pyproject.toml

# RUN useradd -m -u 1000 appuser
# RUN chown -R appuser:appuser /app

# USER 1000

CMD ["uv", "run", "uvicorn", "ai_guardian_remediation.main:app", "--host", "0.0.0.0", "--port", "8588"]
