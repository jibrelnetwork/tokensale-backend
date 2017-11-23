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
```


## Create python virtual environment

```sh
virtualenv -p /usr/bin/python3.6 venv
source venv/bin/activate
```


## Install packages

```sh
pip install -r requirements.txt
```


## Configure

Fill in your db username, passwd, port, host etc


## Init database

```sh
python dj-manage.py migrate
```


### Launching Django server

```sh
python dj-manage.py runserver
```
