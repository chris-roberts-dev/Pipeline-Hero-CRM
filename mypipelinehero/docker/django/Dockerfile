# syntax=docker/dockerfile:1.7
#
# Django application image.
#
# Two build targets:
#   - dev  : installs dev + test requirements, runs as non-root `app` user,
#            suitable for `docker compose up`.
#   - prod : installs only prod requirements, runs under gunicorn.
#
# Build:
#   docker build --target dev  -t mph-django:dev  -f docker/django/Dockerfile .
#   docker build --target prod -t mph-django:prod -f docker/django/Dockerfile .

# ---------------------------------------------------------------------------
# Stage 1 — base
# ---------------------------------------------------------------------------
FROM python:3.13-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Postgres client libs for psycopg; build-essential for any wheels that need
# to compile (argon2-cffi, cffi). Slim image is minimal so we add what we need.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Non-root user. UID/GID 1000 matches most Linux dev hosts so bind-mounted
# volumes don't come back owned by root.
RUN groupadd --system --gid 1000 app \
    && useradd  --system --uid 1000 --gid 1000 --home /home/app --create-home app

WORKDIR /app

# ---------------------------------------------------------------------------
# Stage 2 — dev
# ---------------------------------------------------------------------------
FROM base AS dev

COPY requirements/ /tmp/requirements/
RUN pip install -r /tmp/requirements/dev.txt -r /tmp/requirements/test.txt

# Source is bind-mounted in compose, but copy it here so the image also runs
# standalone (for CI).
COPY --chown=app:app . /app

USER app

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# ---------------------------------------------------------------------------
# Stage 3 — prod
# ---------------------------------------------------------------------------
FROM base AS prod

COPY requirements/ /tmp/requirements/
RUN pip install -r /tmp/requirements/prod.txt

COPY --chown=app:app . /app

# collectstatic at build time so the image is self-contained. Needs a
# throwaway SECRET_KEY because base.py reads it at import.
RUN DJANGO_SECRET_KEY=build-time-placeholder \
    DJANGO_SETTINGS_MODULE=config.settings.prod \
    DJANGO_ALLOWED_HOSTS=placeholder \
    DJANGO_CSRF_TRUSTED_ORIGINS=https://placeholder \
    AWS_STORAGE_BUCKET_NAME=placeholder \
    AWS_ACCESS_KEY_ID=placeholder \
    AWS_SECRET_ACCESS_KEY=placeholder \
    python manage.py collectstatic --noinput || true

USER app

EXPOSE 8000

# 2 workers per CPU is a reasonable starting point. Tune during M6 load work.
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
