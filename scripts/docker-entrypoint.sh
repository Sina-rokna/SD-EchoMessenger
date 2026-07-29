#!/bin/sh
set -eu

if [ "${DATABASE_ENGINE:-sqlite}" = "postgresql" ]; then
    python /app/scripts/wait-for-service.py \
        "${POSTGRES_HOST:-postgres}" "${POSTGRES_PORT:-5432}" PostgreSQL
fi

if [ "${CHANNEL_LAYER_BACKEND:-memory}" = "redis" ]; then
    python /app/scripts/wait-for-service.py redis 6379 Redis
fi

case " $* " in
    *" celery "*)
        python /app/scripts/wait-for-service.py rabbitmq 5672 RabbitMQ
        ;;
esac

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
    python manage.py migrate --noinput
fi

if [ "${COLLECT_STATIC:-0}" = "1" ]; then
    python manage.py collectstatic --noinput
fi

exec "$@"
