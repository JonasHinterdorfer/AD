from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    username = db.Column(db.String, primary_key=True)
    password = db.Column(db.String, nullable=False)

    profile = db.relationship('Profile', backref='user', uselist=False, lazy=True)
    transactions = db.relationship('Transaction', backref='user', lazy=True)

    def get_id(self):
        return self.username


class Profile(db.Model):
    __tablename__ = 'profiles'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String, db.ForeignKey('users.username'), unique=True, nullable=False)
    full_name = db.Column(db.String, default='')
    email = db.Column(db.String, default='')
    phone = db.Column(db.String, default='')
    bio = db.Column(db.String, default='')


class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String, db.ForeignKey('users.username'), nullable=False)
    created_at = db.Column(db.String, nullable=False)
    recipient = db.Column(db.String, nullable=False)
    amount = db.Column(db.String, nullable=False)
    method = db.Column(db.String)
    encrypted_message = db.Column(db.Text)
