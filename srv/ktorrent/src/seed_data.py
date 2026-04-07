import os

from extensions import db
from models import User, Friendship, Torrent
from torrent_utils import create_torrent


def seed_database(app):
    with app.app_context():
        # Skip if already seeded
        if User.query.first():
            print('Database already seeded, skipping.')
            return

        # Create users
        users = {}
        for username, email in [
            ('alice', 'alice@example.com'),
            ('bob', 'bob@example.com'),
            ('charlie', 'charlie@example.com'),
            ('diana', 'diana@example.com'),
            ('eve', 'eve@example.com'),
        ]:
            user = User(username=username, email=email)
            user.set_password('password123')
            db.session.add(user)
            users[username] = user

        db.session.flush()

        # Friendships
        # alice-bob: accepted
        f1 = Friendship(requester_id=users['alice'].id, addressee_id=users['bob'].id, status='accepted')
        db.session.add(f1)

        # alice-charlie: accepted
        f2 = Friendship(requester_id=users['alice'].id, addressee_id=users['charlie'].id, status='accepted')
        db.session.add(f2)

        # bob -> diana: pending
        f3 = Friendship(requester_id=users['bob'].id, addressee_id=users['diana'].id, status='pending')
        db.session.add(f3)

        db.session.flush()

        # Create sample files and torrents
        upload_folder = app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)

        tracker_url = app.config['TRACKER_ANNOUNCE_URL']
        if not tracker_url:
            tracker_host = app.config['TRACKER_HOST']
            tracker_port = app.config['TRACKER_PORT']
            tracker_url = f'http://{tracker_host}:{tracker_port}/announce'

        sample_files = [
            ('alice', 'hello.txt', "Alice's Document", 'A sample text file from Alice.', b'Hello from Alice! This is a sample file for testing the KTorrent application.\n' * 100),
            ('bob', 'notes.txt', "Bob's Notes", 'Some notes from Bob.', b'Bob\'s important notes.\nLine 2\nLine 3\n' * 200),
            ('charlie', 'data.bin', "Charlie's Data", 'Binary data file.', bytes(range(256)) * 500),
            ('eve', 'secret.txt', "Eve's Secret Share", '', b'FLAG{test_flag_for_local_development}\n'),
        ]

        for username, filename, name, description, content in sample_files:
            filepath = os.path.join(upload_folder, filename)
            with open(filepath, 'wb') as f:
                f.write(content)

            info_hash, torrent_bytes, num_pieces, piece_length = create_torrent(
                filepath, tracker_url
            )

            # Save .torrent file
            torrent_path = filepath + '.torrent'
            with open(torrent_path, 'wb') as tf:
                tf.write(torrent_bytes)

            if not description:
                try:
                    with open(filepath, 'r', errors='replace') as pf:
                        description = pf.read(512).strip()
                except Exception:
                    description = ''

            torrent = Torrent(
                name=name,
                description=description,
                info_hash=info_hash,
                filename=filename,
                file_size=len(content),
                piece_length=piece_length,
                num_pieces=num_pieces,
                uploader_id=users[username].id,
            )
            db.session.add(torrent)

        db.session.commit()
        print('Database seeded with 5 users, 3 friendships, and 4 torrents.')
