
from flask import Flask, render_template, request, flash, redirect, url_for, Response, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Profile, Transaction
from crypto_utils import aes_encrypt, fallback_encrypt, rsa_encrypt, ecc_encrypt, otp_encrypt, LCG
from Crypto.Util.number import bytes_to_long
import secrets
import time
import os
import subprocess
from datetime import datetime

KEY = secrets.token_bytes(32)
NONCE = b"\x13\37\x13\37"*2

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(32)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URI', 'sqlite:////app/data/cryze.db'
)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

with app.app_context():
    db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, user_id)


def encrypt_value(value, enc_method):
    match enc_method:
        case "AES":
            return aes_encrypt(value, KEY, NONCE)
        case "RSA":
            return rsa_encrypt(value)
        case "ECC":
            return ecc_encrypt(value)
        case "OTP":
            return otp_encrypt(value)
        case _:
            return fallback_encrypt(value)


@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    # very secure login, checks for everything
    access = True
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = db.session.get(User, username)

        if user is None:
            flash('No such account!', 'error')
            return render_template('login.html')

        if len(password) != len(user.password):
            flash('Password length mismatch!', 'error')
            return render_template('login.html')

        for i, char in enumerate(password):
            if char == user.password[i]:
                time.sleep(0.02)
            else:
                access = False
                break

        if access:
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Incorrect password, access denied!', 'error')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('Username and password are required!', 'error')
            return redirect(url_for('login'))

        if db.session.get(User, username) is not None:
            flash('Username already exists!', 'error')
            return redirect(url_for('login'))

        db.session.add(User(username=username, password=password))
        db.session.commit()

        flash('Registration successful!', 'success')
        return redirect(url_for('login'))

    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    all_transactions = Transaction.query.order_by(Transaction.id.desc()).all()
    return render_template('dashboard.html', all_transactions=all_transactions)


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    username = current_user.username
    user_profile = Profile.query.filter_by(username=username).first()
    if user_profile is None:
        user_profile = Profile(username=username, full_name=username, email='', phone='', bio='')
        db.session.add(user_profile)
        db.session.commit()

    if request.method == 'POST':
        user_profile.full_name = request.form.get('full_name', '').strip()
        user_profile.email = request.form.get('email', '').strip()
        user_profile.phone = request.form.get('phone', '').strip()
        user_profile.bio = request.form.get('bio', '').strip()

        if not user_profile.full_name:
            flash('Full name is required.', 'error')
            return render_template('profile.html', profile=user_profile)

        db.session.commit()
        flash('Profile saved successfully.', 'success')

    return render_template('profile.html', profile=user_profile)


@app.route('/transactions')
@login_required
def recent_transactions():
    user_transactions = Transaction.query.filter_by(username=current_user.username).all()
    return render_template(
        'transactions.html',
        recent_transactions=list(reversed(user_transactions)),
        export_mode=False,
    )


@app.route('/transactions/export', methods=['POST'])
@login_required
def export_transactions_pdf():
    user_transactions = Transaction.query.filter_by(username=current_user.username).all()
    if not user_transactions:
        flash('Cannot export an empty transactions page.', 'error')
        return redirect(url_for('recent_transactions'))

    transactions_html = render_template(
        'transactions.html',
        recent_transactions=list(reversed(user_transactions)),
        export_mode=True,
    )

    try:
        pdf_process = subprocess.run(
            [
                'wkhtmltopdf',
                '--quiet',
                '-',
                '-',
            ],
            input=transactions_html.encode('utf-8'),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
    except subprocess.CalledProcessError as spe:
        return 'Failed to generate PDF export.', 500

    return Response(
        pdf_process.stdout,
        mimetype='application/pdf',
        headers={
            'Content-Disposition': 'attachment; filename="recent-transactions.pdf"',
        },
    )


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))


@app.route('/api/v1/debug/lcg')
@login_required
def lcg_route():
    lcg_gen = LCG()
    random_bytes = lcg_gen(8)
    return [bytes_to_long(random_bytes[:4]), bytes_to_long(random_bytes[4:])]


@app.route('/transaction/<int:id>', methods=['GET', 'POST'])
@login_required
def view_transaction(id):
    txn = db.session.get(Transaction, id)
    if txn is None:
        flash('Transaction not found.', 'error')
        return redirect(url_for('recent_transactions'))

    selected_method = request.form.get('method', 'AES') if request.method == 'POST' else 'AES'

    try:
        encrypted_note = encrypt_value(txn.encrypted_message, selected_method)
    except Exception:
        encrypted_note = None
        flash('Encryption failed.', 'error')

    return render_template('transaction.html',
        txn=txn, encrypted_note=encrypted_note, selected_method=selected_method)


@app.route('/transfer', methods=["GET", "POST"])
@login_required
def transfer_funds():
    if request.method == "GET":
        return render_template('transfer.html')

    recipient = request.form.get("recipient", "").strip()
    amount = request.form.get("amount", "").strip()
    enc_method = request.form.get("method")
    message = request.form.get("message", "").strip()

    if not amount.isnumeric():
        flash('Amount must be a number.', 'error')
        return render_template('transfer.html')

    if not recipient or not amount:
        flash('Recipient and amount are required.', 'error')
        return render_template('transfer.html')

    txn = Transaction(
        username=current_user.username,
        created_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        recipient=recipient,
        amount=amount,
        method=enc_method,
        encrypted_message=message,
    )
    db.session.add(txn)
    db.session.commit()

    try:
        display_encrypted = encrypt_value(message, enc_method)
    except Exception:
        display_encrypted = message

    flash('Transfer created successfully.', 'success')
    return render_template(
        'transfer.html',
        transfer_result={
            'recipient': recipient,
            'amount': amount,
            'encrypted_message': display_encrypted,
        },
    )


@app.route('/api/v1/user/<username>/transactions')
@login_required
def api_user_transactions(username):
    user = db.session.get(User, username)
    if user is None:
        return jsonify({"error": "User not found"}), 404

    transactions = Transaction.query.filter_by(username=username).all()
    return jsonify([
        {
            "id": t.id,
            "created_at": t.created_at,
            "recipient": t.recipient,
            "amount": t.amount,
            "method": t.method,
            "message": t.encrypted_message,
        }
        for t in transactions
    ])


@app.route('/api/v1/transactions/search')
@login_required
def search_transactions():
    q = request.args.get('q', '')
    if not q:
        return jsonify({"results": []})

    query = f"SELECT id, username, created_at, recipient, amount, method, encrypted_message FROM transactions WHERE username = '{current_user.username}' AND recipient LIKE '%{q}%'"
    try:
        results = db.session.execute(db.text(query))
        return jsonify({"results": [
            {"id": r[0], "username": r[1], "created_at": r[2], "recipient": r[3], "amount": r[4], "method": r[5], "message": r[6]}
            for r in results
        ]})
    except Exception:
        return jsonify({"error": "Search failed"}), 400


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
