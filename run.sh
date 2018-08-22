#!/bin/bash -e

RUNMODE="${1:-app}"

export APP_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

if [ "${RUNMODE}" = "app" ]; then
    echo "Starting jco-backend service, version: `cat /app/version.txt` on node `hostname`"
    python jco/dj-manage.py migrate --noinput
    python jco/dj-manage.py collectstatic --noinput --verbosity 0
    cat firstrun.py | python jco/dj-manage.py shell
    uwsgi --yaml /app/uwsgi.yml
elif [ "${RUNMODE}" = "celerybeat" ]; then
    echo "Starting jco-backend-celery-beat service, version: `cat /app/version.txt` on node `hostname`"
    celery -A jco.dj_celery_tasks beat -l info
elif [ "${RUNMODE}" = "celeryworker" ]; then
    echo "Starting jco-backend-celery-worker service, version: `cat /app/version.txt` on node `hostname`"
    celery -A jco worker -l info
else
    echo "Wrong RUNMODE supplied, exiting"
    exit 1
fi
