FROM python:3.6

RUN mkdir -p /app
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN pip install --editable .

VOLUME ["/app/media"]
EXPOSE 8080

CMD python jco/dj-manage.py migrate --noinput \
 && python jco/dj-manage.py collectstatic --noinput \
 && gunicorn --access-logfile - --workers 4 --bind 0.0.0.0:8080 jco.wsgi:application
