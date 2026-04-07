from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

from extensions import db
from models import User, Friendship

friends_bp = Blueprint('friends', __name__)


@friends_bp.route('/friends')
@login_required
def list_friends():
    friends = current_user.friends
    return render_template('friends/list.html', friends=friends)


@friends_bp.route('/friends/requests')
@login_required
def friend_requests():
    incoming = Friendship.query.filter_by(
        addressee_id=current_user.id, status='pending'
    ).all()
    outgoing = Friendship.query.filter_by(
        requester_id=current_user.id, status='pending'
    ).all()
    return render_template('friends/requests.html', incoming=incoming, outgoing=outgoing)


@friends_bp.route('/friends/add/<int:user_id>', methods=['POST'])
@login_required
def add_friend(user_id):
    if user_id == current_user.id:
        flash('You cannot befriend yourself.', 'warning')
        return redirect(url_for('friends.list_friends'))

    target = db.session.get(User, user_id)
    if not target:
        flash('User not found.', 'danger')
        return redirect(url_for('friends.list_friends'))

    # Check for existing friendship in either direction
    existing = Friendship.query.filter(
        db.or_(
            db.and_(Friendship.requester_id == current_user.id, Friendship.addressee_id == user_id),
            db.and_(Friendship.requester_id == user_id, Friendship.addressee_id == current_user.id),
        )
    ).first()

    if existing:
        if existing.status == 'accepted':
            flash(f'You are already friends with {target.username}.', 'info')
        else:
            flash(f'A friend request already exists with {target.username}.', 'info')
        return redirect(url_for('auth.user_profile', username=target.username))

    friendship = Friendship(requester_id=current_user.id, addressee_id=user_id)
    db.session.add(friendship)
    db.session.commit()
    flash(f'Friend request sent to {target.username}.', 'success')
    return redirect(url_for('auth.user_profile', username=target.username))


@friends_bp.route('/friends/accept/<int:id>', methods=['POST'])
@login_required
def accept_friend(id):
    friendship = Friendship.query.get_or_404(id)
    if friendship.addressee_id != current_user.id:
        flash('Not authorized.', 'danger')
        return redirect(url_for('friends.friend_requests'))

    friendship.status = 'accepted'
    db.session.commit()
    flash(f'You are now friends with {friendship.requester.username}!', 'success')
    return redirect(url_for('friends.friend_requests'))


@friends_bp.route('/friends/reject/<int:id>', methods=['POST'])
@login_required
def reject_friend(id):
    friendship = Friendship.query.get_or_404(id)
    if friendship.addressee_id != current_user.id:
        flash('Not authorized.', 'danger')
        return redirect(url_for('friends.friend_requests'))

    username = friendship.requester.username
    db.session.delete(friendship)
    db.session.commit()
    flash(f'Friend request from {username} rejected.', 'info')
    return redirect(url_for('friends.friend_requests'))


@friends_bp.route('/friends/unfriend/<int:user_id>', methods=['POST'])
@login_required
def unfriend(user_id):
    target = db.session.get(User, user_id)
    if not target:
        flash('User not found.', 'danger')
        return redirect(url_for('friends.list_friends'))

    friendship = Friendship.query.filter(
        db.or_(
            db.and_(Friendship.requester_id == current_user.id, Friendship.addressee_id == user_id),
            db.and_(Friendship.requester_id == user_id, Friendship.addressee_id == current_user.id),
        )
    ).first()

    if friendship:
        db.session.delete(friendship)
        db.session.commit()
        flash(f'You are no longer friends with {target.username}.', 'info')
    else:
        flash('No friendship found.', 'warning')

    return redirect(url_for('friends.list_friends'))
