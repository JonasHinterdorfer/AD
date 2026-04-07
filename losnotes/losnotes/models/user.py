from __future__ import annotations

import flask_login

from . import db


class User(flask_login.UserMixin, db.Model):
    __tablename__ = 'users'

    # primary keys, required by sql alchemy
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    # relationships
    password_entries = db.relationship('NotesEntry', back_populates='user', lazy=True)

    @classmethod
    def add(cls, email: str, password: str):
        if not cls.query.filter_by(email=email).first():
            user = cls(email=email, password=password)
            db.session.add(user)
            db.session.commit()
            return user
        return None

    @classmethod
    def does_exist(cls, email: str) -> bool:
        return db.session.query(
            cls.id
        ).filter_by(
            email=email
        ).first() is not None
