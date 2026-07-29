FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install --yes --no-install-recommends curl libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend

COPY backend/requirements.txt backend/requirements-dev.txt /tmp/requirements/
ARG INSTALL_DEV=0
RUN python -m pip install --upgrade pip \
    && if [ "$INSTALL_DEV" = "1" ]; then \
        python -m pip install -r /tmp/requirements/requirements-dev.txt; \
    else \
        python -m pip install -r /tmp/requirements/requirements.txt; \
    fi

RUN addgroup --system --gid 1000 app \
    && adduser --system --uid 1000 --ingroup app --home /app app

COPY --chown=app:app backend/ /app/backend/
COPY --chown=app:app scripts/ /app/scripts/

RUN chmod +x /app/scripts/docker-entrypoint.sh \
    && mkdir -p /app/backend/media /app/backend/staticfiles \
    && chown -R app:app /app

USER app

ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]
CMD ["daphne", "--bind", "0.0.0.0", "--port", "8000", "config.asgi:application"]
