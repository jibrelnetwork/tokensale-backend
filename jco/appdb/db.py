from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker

from jco.commonconfig.config import SQLALCHEMY_DATABASE_URI

db = SQLAlchemy()
Session = sessionmaker(autocommit=False,
                       autoflush=False,
                       bind=create_engine(SQLALCHEMY_DATABASE_URI))
session = scoped_session(Session)
