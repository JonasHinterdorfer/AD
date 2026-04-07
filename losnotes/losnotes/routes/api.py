import flask
import flask_login

import models.api_key
import models.notes_entry
import models.user

api_blueprint = flask.Blueprint('api', __name__)


@api_blueprint.route("/api_keys", methods=["GET"])
@flask_login.login_required
def api_keys_page():
    keys = models.api_key.ApiKey.get_user_keys(flask_login.current_user.id)
    return flask.render_template(
        "dashboard_api_keys.html",
        api_keys=keys
    )


@api_blueprint.route("/api/keys", methods=["POST"])
@flask_login.login_required
def create_api_key():
    user_id = flask_login.current_user.id

    api_key = models.api_key.ApiKey.add(user_id=user_id)
    return flask.jsonify({
        'id': api_key.id,
        'key': api_key.key,
        'user_id': api_key.user_id,
        'created_at': api_key.created_at.isoformat()
    }), 201


@api_blueprint.route("/api/keys", methods=["GET"])
@flask_login.login_required
def list_api_keys():
    keys = models.api_key.ApiKey.get_user_keys(flask_login.current_user.id)
    return flask.jsonify([
        {
            'id': k.id,
            'key': k.key,
            'created_at': k.created_at.isoformat()
        }
        for k in keys
    ])


@api_blueprint.route("/api/keys/<int:key_id>", methods=["DELETE"])
@flask_login.login_required
def delete_api_key(key_id):
    deleted = models.api_key.ApiKey.delete_key(
        key_id=key_id,
        user_id=flask_login.current_user.id
    )
    if deleted:
        return flask.jsonify({'status': 'deleted'}), 200
    return flask.jsonify({'error': 'Key not found'}), 404


@api_blueprint.route("/api/me", methods=["GET"])
@flask_login.login_required
def get_me():
    user = models.user.User.query.get(flask_login.current_user.id)
    return flask.jsonify({
        'id': user.id,
        'email': user.email,
    })


@api_blueprint.route("/api/notes", methods=["GET"])
def get_notes():
    api_key_header = flask.request.headers.get('X-API-Key')
    if not api_key_header:
        return flask.jsonify({'error': 'Missing X-API-Key header'}), 401

    api_key = models.api_key.ApiKey.get_by_key(api_key_header)
    if not api_key:
        return flask.jsonify({'error': 'Invalid API key'}), 401

    notes = models.notes_entry.NotesEntry.query.filter_by(
        user_id=api_key.user_id
    ).filter_by(
        deleted=False
    ).all()

    return flask.jsonify([
        {
            'id': n.id,
            'note': n.note
        }
        for n in notes
    ])
