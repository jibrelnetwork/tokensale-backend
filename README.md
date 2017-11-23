# jco
jco(Jibrel ICO) - Token Sale Support Site, backend


Тестовый стенд развернут на http://37.59.55.6:8080

Юзер admin:123qwerty

Документация АПИ http://37.59.55.6:8080/docs/

Авторизация в API - заголовок "Authorization: Token as56da6sd(токен)". Получить токен можно тут: `POST /auth/login/`


# Installation

## Install system packages

```sh
sudo apt-get update
sudo apt-get install gcc build-essential autoconf libtool pkg-config libssl-dev libffi-dev python3-dev virtualenv
sudo apt-get install git nginx
sudo apt-get install postgresql postgresql-contrib
```


## Install RabbitMQ (Celery`s dependency)

https://linoxide.com/ubuntu-how-to/install-setup-rabbitmq-ubuntu-16-04/
```sh
sudo apt-get update
sudo apt-get install rabbitmq-server
sudo systemctl enable rabbitmq-server
sudo systemctl start rabbitmq-server
sudo systemctl status rabbitmq-server
sudo rabbitmqctl add_user rabbituser rabbitpassword
sudo rabbitmqctl add_vhost rabbitvhost
sudo rabbitmqctl set_permissions -p rabbitvhost rabbituser ".*" ".*" ".*"
```


## Set up database

```
sudo -u postgres psql
postgres=# CREATE DATABASE mysaleuser;
postgres=# CREATE USER mysaleuser WITH PASSWORD 'password';
postgres=# ALTER ROLE mysaleuser SET client_encoding TO 'utf8';
postgres=# ALTER ROLE mysaleuser SET default_transaction_isolation TO 'read committed';
postgres=# ALTER ROLE mysaleuser SET timezone TO 'UTC';
postgres=# GRANT ALL PRIVILEGES ON DATABASE mysaledb TO mysaleuser;
postgres=# \q
```


## Clone project and create workdir

```
cd /home/jibrelnetwork
git clone https://github.com/jibrelnetwork/jco
cd jco
```


## Create python virtual environment

```sh
virtualenv -p /usr/bin/python3.6 venv
source venv/bin/activate
```


## Install packages

```sh
pip install -r requirements.txt
pip install --editable ./
```


## Configure

Copy settings file:
`cp ./jco/settings.py ./jco/settings_local.py`

Fill in your settings:
```
DATABASE_HOST
DATABASE_NAME
DATABASE_USER
DATABASE_PASS

CRAWLER_PROXY__USER
CRAWLER_PROXY__PASS
CRAWLER_PROXY__URLS
```

```
export JCO_DATABASE_URI="postgresql://jcouser:password@localhost:5432/jcodb"
export ONFIDO_API_KEY="xxxxx"
export RECAPTCHA_PRIVATE_KEY="xxxxx"
```


## Init database

```sh
python jco/dj-manage.py migrate
```


## Launching Django server in dev mode

```sh
python jco/dj-manage.py runserver
```

## Deploying (Gunicorn)

### Testing Gunicorn's Ability to Serve the Project

```sh
cd ~/jco
source venv/bin/activate
gunicorn --bind 0.0.0.0:8000 -w 4 jco.wsgi
```

### Create a Gunicorn systemd Service File

```sh
sudo nano /etc/systemd/system/jco.service
```

```
[Unit]
Description=jco daemon
After=network.target

[Service]
User=jibrelnetwork
Group=www-data
WorkingDirectory=/home/jibrelnetwork/jco/
ExecStart=/home/jibrelnetwork/jco/venv/bin/gunicorn --access-logfile - --workers 4 --bind unix:/home/jibrelnetwork/jco/jco.sock jco.wsgi:application

[Install]
WantedBy=multi-user.target
```

Commands

sudo systemctl start jco
sudo systemctl restart jco
sudo systemctl stop jco

### Check response of web server

```
curl -H "Content-Type: application/json" -X POST -d '{"email":"test1@local","password":"password"}' http://localhost:8080/auth/login/
```

# Launch celery tasks

## Launch Django celery tasks in dev mode

```
mkdir -p ./celery-sys/
mkdir -p ./celery-log/

source venv/bin/activate

celery -A jco worker \
    --pidfile="./celery-sys/%n.pid" \
    --logfile="./celery-log/%n-%i.log" \
    --loglevel=INFO
```

## Launch SQLAlchemy celery tasks in dev mode

```
mkdir -p ./celery-sys/
mkdir -p ./celery-log/

source venv/bin/activate

celery worker \
  --app=jco.celery_tasks \
  --pidfile="./celery-sys/%n.pid" \
  --logfile="./celery-log/%n-%i.log" \
  --loglevel=INFO
```
