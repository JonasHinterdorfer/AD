import flask
import flask_login

import models.notes_entry
# import routes.api

dashboard_blueprint = flask.Blueprint('dashboard', __name__)

@dashboard_blueprint.route("/dashboard")
@flask_login.login_required
def dashboard_route():
    notes = [
        [entry.note, entry.id, entry.user_id]
        for entry in models.notes_entry.NotesEntry.query.filter_by(
            user_id=flask_login.current_user.id
        ).filter_by(
            deleted=False
        ).all()
    ]
    return flask.render_template(
        "dashboard_notes.html",
        credentials=notes
    )


@dashboard_blueprint.route("/add_note", methods=["GET"])
@flask_login.login_required
def dashboard_add_password_get_route():
    return flask.render_template(
        "dashboard_add_note.html"
    )


@dashboard_blueprint.route("/add_note", methods=["POST"])
@flask_login.login_required
def dashboard_add_password_post_route():
    note = flask.request.form.get('note')
    models.notes_entry.NotesEntry.add(
        note=note,
        user_id=flask_login.current_user.id
    )
    return flask.redirect(flask.url_for('dashboard.dashboard_route'))


@dashboard_blueprint.route("/search_note", methods=["GET"])
@flask_login.login_required
def dashboard_search_password_get_route():
    return flask.render_template("dashboard_search_notes.html")


@dashboard_blueprint.route("/search_note", methods=["POST"])
@flask_login.login_required
def dashboard_search_password_post_route():
    search_text = flask.request.form.get('search')

    notes = [
        [entry.note, entry.id, entry.user_id]
        for entry in models.notes_entry.NotesEntry.query.filter(
            models.notes_entry.NotesEntry.note.like(f"%{search_text}%")
        ).filter_by(
            user_id=flask_login.current_user.id
        ).filter_by(
            deleted=False
        )
    ]

    return flask.render_template(
        "dashboard_search_notes.html",
        notes=notes
    )



@dashboard_blueprint.route("/delete/<int:note_id>", methods=["POST"])
@flask_login.login_required
def dashboard_delete_route(note_id):
    note = models.notes_entry.NotesEntry.get_note(
        user_id=flask_login.current_user.id,
        note_id=note_id
    )
    if note:
        models.notes_entry.NotesEntry.delete(note.id)

    return flask.redirect(flask.url_for('dashboard.dashboard_route'))


@dashboard_blueprint.route("/raw/<int:note_id>", methods=["GET"])
@flask_login.login_required
def dashboard_raw_get_route(note_id):
    note = models.notes_entry.NotesEntry.query.filter_by(
        id=note_id
    ).filter_by(
        user_id=flask_login.current_user.id
    ).filter_by(
        deleted=False
    ).first()

    if not note:
        return "Note not found!"
    
    return note.note