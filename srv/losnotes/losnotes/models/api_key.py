from __future__ import annotations

import secrets
from datetime import datetime

from . import db


class ApiKey(db.Model):
    __tablename__ = 'api_keys'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='api_keys')

    @classmethod
    def add(cls, user_id: int):
        api_key = cls(key=secrets.token_hex(32), user_id=user_id)
        db.session.add(api_key)
        db.session.commit()
        return api_key

    @classmethod
    def get_by_key(cls, key: str):
        return cls.query.filter_by(key=key).first()

    @classmethod
    def get_user_keys(cls, user_id: int):
        return cls.query.filter_by(user_id=user_id).all()

    @classmethod
    def delete_key(cls, key_id: int, user_id: int):
        entry = cls.query.filter_by(id=key_id, user_id=user_id).first()
        if entry:
            db.session.delete(entry)
            db.session.commit()
            return True
        return False
