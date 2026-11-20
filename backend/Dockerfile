# Backend image: the API, the dashboard, the Celery worker and Celery beat.
#   target "prod": runtime libraries only, runs Gunicorn (staging and production)
#   target "dev":  adds the test and lint tools; docker-compose.yml mounts the source

FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/opt/venv/bin:$PATH"

# gettext: makemessages and compilemessages for the Arabic translations.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gettext \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /usr/local/bin/uv

RUN useradd --create-home --uid 1000 app
WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project --no-dev


FROM base AS dev
RUN uv sync --locked --no-install-project
USER app
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]


FROM base AS prod
COPY --chown=app:app . .
RUN DJANGO_SETTINGS_MODULE=config.settings.dev python manage.py compilemessages --ignore ".venv" \
    && DJANGO_SETTINGS_MODULE=config.settings.dev python manage.py collectstatic --noinput \
    && chown -R app:app /app
USER app
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-"]
