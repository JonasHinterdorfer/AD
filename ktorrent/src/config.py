import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'SQLALCHEMY_DATABASE_URI', 'sqlite:///ktorrent.db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', os.path.join(os.path.dirname(__file__), 'uploads'))
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 500 * 1024 * 1024))  # 500MB
    TRACKER_HOST = os.environ.get('TRACKER_HOST', '127.0.0.1')
    TRACKER_PORT = int(os.environ.get('TRACKER_PORT', 5000))
    TRACKER_ANNOUNCE_URL = os.environ.get('TRACKER_ANNOUNCE_URL', '')  # e.g. http://192.168.1.50:5001/announce
    SEEDER_PORT = int(os.environ.get('SEEDER_PORT', 6881))
    SEEDER_EXTERNAL_HOST = os.environ.get('SEEDER_EXTERNAL_HOST', '')  # IP that external peers use to reach the seeder
    SEEDER_ENABLED = os.environ.get('SEEDER_ENABLED', '1') == '1'
    TRACKER_ANNOUNCE_INTERVAL = int(os.environ.get('TRACKER_ANNOUNCE_INTERVAL', 60))
    TRACKER_PEER_TIMEOUT = int(os.environ.get('TRACKER_PEER_TIMEOUT', 120))
