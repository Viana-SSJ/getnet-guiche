FROM python:3.12.15-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /usr/local/bin/uv

# Copy files with their owner: a later chown would copy every file into a new layer.
RUN useradd --create-home appuser && mkdir /app && chown appuser /app
USER appuser
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_NO_CACHE=1 PYTHONUNBUFFERED=1

# Runtime libraries only.
COPY --chown=appuser pyproject.toml uv.lock ./
RUN uv sync --frozen --no-default-groups

COPY --chown=appuser main.py ./
COPY --chown=appuser agents ./agents
COPY --chown=appuser data ./data
COPY --chown=appuser kb ./kb

# Build the search index now, so the container starts fast.
RUN uv run --no-sync python -c "from agents.getnet.tools.kb_search import load_index; load_index()"

ENV HOST=0.0.0.0 PORT=8000
EXPOSE 8000
CMD ["uv", "run", "--no-sync", "python", "main.py"]
