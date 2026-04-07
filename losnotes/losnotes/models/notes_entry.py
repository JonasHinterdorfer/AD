from __future__ import annotations

from . import db

class NotesEntry(db.Model):
    __tablename__ = 'notes_entry'

    id = db.Column(db.Integer, primary_key=True)
    note = db.Column(db.Text)
    deleted = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    user = db.relationship('User', back_populates='password_entries')

    @classmethod
    def add(cls, note: str, user_id: int):
        entry = cls(note=note, user_id=user_id)
        db.session.add(entry)
        db.session.commit()
        return entry
    
    @classmethod
    def _delete(cls, id: int):
        entry = cls.query.filter_by(id=id).first()
        if entry:
            db.session.delete(entry)
            db.session.commit()
            return True
        return False
    
    @classmethod
    def delete(cls, id: int):
        entry = cls.query.filter_by(id=id).first()
        if entry:
            entry.deleted = True
            db.session.add(entry)
            db.session.commit()
            return True
        return False

    @classmethod
    def get_note(cls, user_id: int, note_id: int):
        entry = cls.query.filter_by(
            user_id=user_id,
            id=note_id
        ).filter_by(
            deleted=False
        ).first()
        return entry
