import secrets
from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db

# In-memory peer storage: peers[info_hash_hex][(ip, port)] = {peer_id, ip, port, uploaded, downloaded, left, last_announce, user_id}
peers = {}


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    passkey = db.Column(db.String(32), unique=True, nullable=False, default=lambda: secrets.token_hex(16))
    bio = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    torrents = db.relationship('Torrent', backref='uploader', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def regenerate_passkey(self):
        self.passkey = secrets.token_hex(16)

    @property
    def friends(self):
        """Return list of accepted friends (bidirectional)."""
        sent = db.session.query(User).join(
            Friendship, Friendship.addressee_id == User.id
        ).filter(
            Friendship.requester_id == self.id,
            Friendship.status == 'accepted'
        ).all()
        received = db.session.query(User).join(
            Friendship, Friendship.requester_id == User.id
        ).filter(
            Friendship.addressee_id == self.id,
            Friendship.status == 'accepted'
        ).all()
        return sent + received

    def is_friend_of(self, other):
        """Check if this user is friends with other. Returns True for self."""
        if self.id == other.id:
            return True
        return Friendship.query.filter(
            db.or_(
                db.and_(Friendship.requester_id == self.id, Friendship.addressee_id == other.id),
                db.and_(Friendship.requester_id == other.id, Friendship.addressee_id == self.id),
            )
        ).first() is not None

    @property
    def pending_requests(self):
        """Incoming pending friend requests."""
        return Friendship.query.filter_by(
            addressee_id=self.id, status='pending'
        ).all()

    @property
    def pending_request_count(self):
        return Friendship.query.filter_by(
            addressee_id=self.id, status='pending'
        ).count()

    def __repr__(self):
        return f'<User {self.username}>'


class Friendship(db.Model):
    __tablename__ = 'friendships'

    id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    addressee_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')  # 'pending' or 'accepted'
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    requester = db.relationship('User', foreign_keys=[requester_id], backref='sent_requests')
    addressee = db.relationship('User', foreign_keys=[addressee_id], backref='received_requests')

    __table_args__ = (
        db.UniqueConstraint('requester_id', 'addressee_id', name='uq_friendship'),
    )

    def __repr__(self):
        return f'<Friendship {self.requester_id} -> {self.addressee_id} ({self.status})>'


class Torrent(db.Model):
    __tablename__ = 'torrents'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    info_hash = db.Column(db.String(40), unique=True, nullable=False, index=True)
    filename = db.Column(db.String(300), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    piece_length = db.Column(db.Integer, nullable=False)
    num_pieces = db.Column(db.Integer, nullable=False)
    uploader_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def seeders(self):
        from models import peers
        torrent_peers = peers.get(self.info_hash, {})
        return sum(1 for p in torrent_peers.values() if p['left'] == 0)

    def leechers(self):
        from models import peers
        torrent_peers = peers.get(self.info_hash, {})
        return sum(1 for p in torrent_peers.values() if p['left'] > 0)

    def __repr__(self):
        return f'<Torrent {self.name}>'
