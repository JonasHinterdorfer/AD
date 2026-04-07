import base64
import hashlib
import hmac
import os

from flask import (
    Blueprint, render_template, redirect, url_for, flash,
    request, current_app, send_file, abort, jsonify
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from extensions import db
from models import Torrent
from forms import UploadForm
from torrent_utils import create_torrent, personalize_torrent
from sqlalchemy import text

torrents_bp = Blueprint('torrents', __name__)


@torrents_bp.route('/')
@torrents_bp.route('/torrents')
@login_required
def browse():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    sort = request.args.get('sort', 'newest', type=str)

    query = Torrent.query

    if search:
        query = query.filter(Torrent.name.ilike(f'%{search}%'))

    if sort == 'oldest':
        query = query.order_by(Torrent.created_at.asc())
    elif sort == 'name':
        query = query.order_by(Torrent.name.asc())
    elif sort == 'size':
        query = query.order_by(Torrent.file_size.desc())
    else:  # newest
        query = query.order_by(Torrent.created_at.desc())

    pagination = query.paginate(page=page, per_page=20, error_out=False)
    return render_template(
        'torrents/browse.html',
        torrents=pagination.items,
        pagination=pagination,
        search=search,
        sort=sort,
    )


@torrents_bp.route('/torrents/<int:id>')
@login_required
def detail(id):
    torrent = Torrent.query.get_or_404(id)
    can_download = current_user.is_friend_of(torrent.uploader)
    return render_template('torrents/detail.html', torrent=torrent, can_download=can_download)


@torrents_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    form = UploadForm()
    if form.validate_on_submit():
        f = form.file.data
        filename = secure_filename(f.filename)

        # Handle filename collisions
        upload_folder = current_app.config['UPLOAD_FOLDER']
        filepath = os.path.join(upload_folder, filename)
        base, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(filepath):
            filename = f'{base}_{counter}{ext}'
            filepath = os.path.join(upload_folder, filename)
            counter += 1

        f.save(filepath)
        file_size = os.path.getsize(filepath)

        # Generate tracker URL
        tracker_url = current_app.config['TRACKER_ANNOUNCE_URL']
        if not tracker_url:
            tracker_host = current_app.config['TRACKER_HOST']
            tracker_port = current_app.config['TRACKER_PORT']
            tracker_url = f'http://{tracker_host}:{tracker_port}/announce'

        info_hash, torrent_bytes, num_pieces, piece_length = create_torrent(
            filepath, tracker_url
        )

        # Save .torrent file
        torrent_path = filepath + '.torrent'
        with open(torrent_path, 'wb') as tf:
            tf.write(torrent_bytes)

        description = form.description.data
        if not description:
            try:
                with open(filepath, 'r', errors='replace') as pf:
                    description = pf.read(512).strip()
            except Exception:
                description = ''

        torrent = Torrent(
            name=form.name.data,
            description=description,
            info_hash=info_hash,
            filename=filename,
            file_size=file_size,
            piece_length=piece_length,
            num_pieces=num_pieces,
            uploader_id=current_user.id,
        )
        db.session.add(torrent)
        db.session.commit()

        flash('Torrent uploaded successfully!', 'success')
        return redirect(url_for('torrents.detail', id=torrent.id))

    return render_template('torrents/upload.html', form=form)


@torrents_bp.route('/download/<int:id>')
@login_required
def download(id):
    torrent = Torrent.query.get_or_404(id)

    # Friendship gate
    if not current_user.is_friend_of(torrent.uploader):
        flash('You must be friends with the uploader to download this torrent.', 'danger')
        return redirect(url_for('torrents.detail', id=id))

    # Read .torrent file
    torrent_path = os.path.join(current_app.config['UPLOAD_FOLDER'], torrent.filename + '.torrent')
    if not os.path.exists(torrent_path):
        abort(404)

    with open(torrent_path, 'rb') as f:
        torrent_bytes = f.read()

    # Personalize with user's passkey
    personalized = personalize_torrent(torrent_bytes, current_user.passkey)

    from io import BytesIO
    return send_file(
        BytesIO(personalized),
        as_attachment=True,
        download_name=f'{torrent.name}.torrent',
        mimetype='application/x-bittorrent',
    )


@torrents_bp.route('/torrents/my-uploads')
@login_required
def my_uploads():
    torrents = Torrent.query.filter_by(uploader_id=current_user.id).order_by(
        Torrent.created_at.desc()
    ).all()
    return render_template('torrents/my_uploads.html', torrents=torrents)


# --- API endpoints ---

@torrents_bp.route('/api/torrents')
@login_required
def api_search():
    """Search torrents by name (API endpoint)."""
    q = request.args.get('q', '')
    sql = text(
        "SELECT id, name, file_size, created_at FROM torrents "
        "WHERE name LIKE :name ORDER BY created_at DESC LIMIT 50"
    )
    result = db.session.execute(sql, {"name": f"%{q}%"})
    rows = [dict(row._mapping) for row in result]
    return jsonify(rows)


@torrents_bp.route('/api/torrent/<int:id>')
@login_required
def api_torrent_detail(id):
    """Get torrent details as JSON."""
    torrent = Torrent.query.get_or_404(id)

    if not current_user.is_friend_of(torrent.uploader):
        return jsonify({'error': 'Friendship required'}), 403

    return jsonify({
        'id': torrent.id,
        'name': torrent.name,
        'description': torrent.description,
        'info_hash': torrent.info_hash,
        'file_size': torrent.file_size,
        'uploader': torrent.uploader.username,
        'created_at': torrent.created_at.isoformat(),
    })


@torrents_bp.route('/api/torrent/<int:id>/export')
@login_required
def api_torrent_export(id):
    """Export torrent file for external tools."""
    torrent = Torrent.query.get_or_404(id)

    if not current_user.is_friend_of(torrent.uploader):
        return jsonify({'error': 'Friendship required'}), 403

    token = request.args.get('token', '')
    secret = current_app.config['SECRET_KEY']
    expected = hmac.new(
        secret.encode('utf-8'),
        torrent.info_hash.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(token, expected):
        return jsonify({'error': 'Invalid or missing token'}), 403

    torrent_path = os.path.join(
        current_app.config['UPLOAD_FOLDER'], torrent.filename + '.torrent'
    )
    if not os.path.exists(torrent_path):
        abort(404)

    with open(torrent_path, 'rb') as f:
        torrent_data = base64.b64encode(f.read()).decode()

    return jsonify({
        'id': torrent.id,
        'name': torrent.name,
        'torrent_file': torrent_data,
    })


@torrents_bp.route('/preview/<path:filename>')
@login_required
def preview(filename):
    """Preview file contents."""
    # Only allow previewing registered original files (not arbitrary paths / .torrent files)
    torrent = Torrent.query.filter_by(filename=filename).first()
    if not torrent:
        abort(404)

    if not current_user.is_friend_of(torrent.uploader):
        abort(403)

    upload_folder = os.path.abspath(current_app.config['UPLOAD_FOLDER'])
    filepath = os.path.abspath(os.path.join(upload_folder, torrent.filename))
    if not filepath.startswith(upload_folder + os.sep):
        abort(403)
    if not os.path.isfile(filepath):
        abort(404)

    try:
        with open(filepath, 'r', errors='replace') as f:
            content = f.read(4096)
    except Exception:
        content = '(binary file — cannot preview)'
    return render_template('torrents/preview.html', filename=filename, content=content)
