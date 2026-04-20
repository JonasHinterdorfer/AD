import os

import flask
import flask_login

import models.user
import routes.api
import routes.auth
import routes.dashboard
from models import db

app = flask.Flask(__name__)


@app.route('/static/<path:path>')
def send_static_file(path):
    return flask.send_from_directory('static', path)


@app.route('/')
def index():
    return flask.redirect(flask.url_for('dashboard.dashboard_route'))


if __name__ == "__main__":
    app.config['SECRET_KEY'] = os.urandom(32).hex()
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'SQLALCHEMY_DATABASE_URI',
        'sqlite:///project.db'
    )
    # app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///project.db'

    db.init_app(app)

    with app.app_context():
        db.create_all()

    # Register Routes
    app.register_blueprint(routes.auth.auth_blueprint)
    app.register_blueprint(routes.dashboard.dashboard_blueprint)
    app.register_blueprint(routes.api.api_blueprint)

    # import sys
    # print(app.url_map, file=sys.stderr)

    login_manager = flask_login.LoginManager()
    login_manager.login_view = 'auth.login_get_route'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return models.user.User.query.get(int(user_id))

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get('PORT', '8080')),
        debug=os.environ.get('FLASK_DEBUG', '0') == '1'
    )
