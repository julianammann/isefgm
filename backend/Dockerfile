ARG UV_VERSION=0.12.9
# No digest pin here: a digest overrides the tag, so UV_VERSION (passed from
# mise.toml by `mise run docker` and CI) would silently stop having any effect.
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM python:3.14-slim@sha256:51dafde81dbdb6ebde285137a295cf18a47ca95234fe388a343719cb97305b3d AS builder
COPY --from=uv /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0
WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project --frozen --no-dev

COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

FROM python:3.14-slim@sha256:51dafde81dbdb6ebde285137a295cf18a47ca95234fe388a343719cb97305b3d AS runtime
# /data/uploads exists in the image and belongs to app, so the named volume mounted
# there is initialised with that owner instead of root.
RUN groupadd --system app && useradd --system --gid app --home /app app \
    && mkdir -p /data/uploads && chown app:app /data/uploads
WORKDIR /app
COPY --from=builder --chown=app:app /app /app
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER app
EXPOSE 8000
CMD ["fastapi", "run", "src/giftmanager/main.py", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]