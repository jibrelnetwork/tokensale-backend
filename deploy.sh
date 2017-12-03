#!/bin/sh

JCO_SERVICE=jco.service
JCO_CELERY_SERVICE=jco-dj-celery.service
ROOT="/home/jibrelnetwork/jco"

echo "Start deploying"
cd $ROOT

# Stop services
echo "  Stopping services..."
sudo systemctl stop $JCO_SERVICE
sudo systemctl stop $JCO_CELERY_SERVICE

# Update git repository
echo "  Get last version..."
git pull

# Install Python packages
echo "    Install Python packages..."
$ROOT/venv/bin/pip install -r requirements.txt

# Run django scripts
echo "  Running scripts..."
echo "    Migrating database..."
$ROOT/venv/bin/python $ROOT/jco/dj-manage.py migrate --noinput
echo "    Collecting static files..."
$ROOT/venv/bin/python $ROOT/jco/dj-manage.py collectstatic --noinput

# Starting services
echo "  Restarting services..."
sudo systemctl start $JCO_SERVICE
sudo systemctl start $JCO_CELERY_SERVICE

echo "Done deploying."
