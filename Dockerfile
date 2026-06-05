FROM python:3.12-slim

# git is needed to clone/pull wiki_source. gh is intentionally NOT installed:
# without it wiki_edit is disabled, making the remote server effectively read-only.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev

ENV PORT=8000
EXPOSE 8000

CMD ["uv", "run", "wiki-mcp-http"]
