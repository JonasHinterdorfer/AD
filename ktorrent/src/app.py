import os
import click
from flask import Flask, render_template, request as flask_request

from config import Config
from extensions import db, login_manager, csrf


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Init extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # User loader
    from models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Register blueprints
    from blueprints.auth import auth_bp
    from blueprints.friends import friends_bp
    from blueprints.torrents import torrents_bp
    from blueprints.tracker import tracker_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(friends_bp)
    app.register_blueprint(torrents_bp)
    app.register_blueprint(tracker_bp)

    # Register Jinja2 filters
    from torrent_utils import human_size, time_ago
    app.jinja_env.filters['human_size'] = human_size
    app.jinja_env.filters['time_ago'] = time_ago

    # Custom error page
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html', path=flask_request.path), 404

    # Create tables on first request
    with app.app_context():
        db.create_all()

    # CLI commands
    @app.cli.command('init-db')
    def init_db():
        """Create all database tables."""
        db.create_all()
        click.echo('Database initialized.')

    @app.cli.command('seed')
    def seed():
        """Seed database with test data."""
        from seed_data import seed_database
        seed_database(app)
        click.echo('Database seeded.')

    # Start seeder thread
    if app.config.get('SEEDER_ENABLED', True):
        from seeder import start_seeder_thread
        start_seeder_thread(app)

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=os.environ.get('FLASK_DEBUG', '0') == '1',
        use_reloader=False,
    )
