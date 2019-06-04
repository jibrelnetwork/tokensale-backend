FROM python:3.6

RUN addgroup --system --gid 1000 app \
 && adduser --system -u 1000 --gid 1000 --shell /bin/sh --disabled-login app \
 && mkdir /app \
 && chmod -R ugo=rX /app
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN pip install --editable .

VOLUME ["/app/media"]
EXPOSE 8080

CMD python jco/dj-manage.py migrate --noinput \
 && python jco/dj-manage.py collectstatic --noinput \
 && uwsgi --yaml /app/uwsgi.yml
