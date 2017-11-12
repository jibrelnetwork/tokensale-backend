#!/usr/bin/env python

from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
from run import flask_app

from jco.appdb.db import db

migrate = Migrate(flask_app, db)

manager = Manager(flask_app)
manager.add_command('db', MigrateCommand)

if __name__ == '__main__':
    manager.run()
