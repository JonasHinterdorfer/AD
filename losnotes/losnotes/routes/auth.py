import flask
import flask_login

import models.user

auth_blueprint = flask.Blueprint('auth', __name__)


@auth_blueprint.route("/login")
def login_get_route():
    return flask.render_template(
        "login.html",
        error_msg=None
    )


@auth_blueprint.route("/login", methods=["POST"])
def login_post_route():
    email = flask.request.form.get('email')
    password = flask.request.form.get('password')

    user = models.user.User.authenticate(email=email, password=password)
    if not user:
        return flask.render_template(
            "login.html",
            error_msg="Invalid email or password!"
        )

    flask_login.login_user(user, remember=False)
    return flask.redirect(flask.url_for('dashboard.dashboard_route'))


@auth_blueprint.route('/register', methods=["POST"])
def register_post_route():
    email = flask.request.form.get('email')
    password = flask.request.form.get('password')

    if models.user.User.does_exist(email=email):
        return flask.render_template(
            "register.html",
            error_msg="This Email has already been used!"
        )

    user = models.user.User.add(email=email, password=password)
    flask_login.login_user(user, remember=False)

    return flask.redirect(flask.url_for('dashboard.dashboard_route'))


@auth_blueprint.route('/register', methods=["GET"])
def register_get_route():
    return flask.render_template(
        "register.html",
        error_msg=None
    )


@auth_blueprint.route('/logout')
@flask_login.login_required
def logout():
    flask_login.logout_user()
    return flask.redirect(flask.url_for('auth.login_get_route'))
