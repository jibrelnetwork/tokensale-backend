#!/bin/sh

JCO_SERVICE=jco.service
JCO_CELERY_SERVICE=jco-dj-celery.service
ROOT="/home/jibrelnetwork/jco"

echo "Deploying $APPNAME"

# Stop services
echo "  Stopping services..."
sudo systemctl stop $JCO_SERVICE
sudo systemctl stop $JCO_CELERY_SERVICE

# Update git repository
echo "  Get last version..."
git pull

# Run django scripts
echo "  Running scripts..."
echo "    Migrating database..."
$ROOT/venv/bin/python $ROOT/jco/dj-manage.py migrate --noinput
echo "    Collecting static files..."
$ROOT/venv/bin/python $ROOT/jco/dj-manage.py collectstatic --noinput

echo "  Restarting services..."
sudo systemctl start $JCO_SERVICE
sudo systemctl start $JCO_CELERY_SERVICE
echo "Done deploying."
