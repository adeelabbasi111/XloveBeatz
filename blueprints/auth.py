from flask import jsonify,Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from helpers.utils import validate_email, validate_password
from helpers.services import create_user, get_user_by_email, merge_guest_cart
from datetime import datetime
bp = Blueprint('auth', __name__)
import uuid
from datetime import datetime, timedelta
from helpers.utils import send_reset_email
from helpers.models import db,User
import os


# ── Forgot Password: Request Reset ──
@bp.route('/api/auth/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    email = data.get('email', '').strip().lower()

    if not email:
        return jsonify({'error': 'Email is required'}), 400

    user = User.query.filter(db.func.lower(User.email) == email).first()

    if user:
        token = uuid.uuid4().hex
        user.password_reset_token = token
        user.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
        db.session.commit()

        reset_url = f"{request.host_url}reset-password/{token}"
        send_reset_email(user.email, reset_url)

    return jsonify({
        'success': True,
        'message': 'If an account with that email exists, a reset link has been sent. Please note it may take a few minutes to arrive.'
    })


# ── Reset Password Page ──
@bp.route('/reset-password/<token>')
def reset_password_page(token):
    user = User.query.filter_by(password_reset_token=token).first()

    if not user or not user.password_reset_expires:
        flash('Invalid or expired reset link', 'error')
        return redirect(url_for('public.home'))

    if user.password_reset_expires < datetime.utcnow():
        flash('Reset link has expired. Please request a new one.', 'error')
        return redirect(url_for('public.home'))

    return render_template('partials/reset_password.html', token=token)


# ── Reset Password: Submit New Password ──
@bp.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()
    token = data.get('token', '').strip()
    new_password = data.get('new_password', '')

    if not token or not new_password:
        return jsonify({'error': 'Token and new password are required'}), 400

    if len(new_password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    user = User.query.filter_by(password_reset_token=token).first()

    if not user:
        return jsonify({'error': 'Invalid reset token'}), 400

    if not user.password_reset_expires or user.password_reset_expires < datetime.utcnow():
        return jsonify({'error': 'Reset link has expired'}), 400

    user.password_hash = generate_password_hash(new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Password reset successfully! You can now login.'
    })

@bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not username or not email or not password:
            flash('All fields are required', 'error')
            return redirect(url_for('public.home'))
        if len(username) < 3:
            flash('Username must be at least 3 characters', 'error')
            return redirect(url_for('public.home'))
        if not validate_email(email):
            flash('Please enter a valid email address', 'error')
            return redirect(url_for('public.home'))
        ok, msg = validate_password(password)
        if not ok:
            flash(msg, 'error')
            return redirect(url_for('public.home'))
        if get_user_by_email(email):
            flash('Email already registered', 'error')
            return redirect(url_for('public.home'))

        user = create_user(username, email, generate_password_hash(password))

        if 'session_id' in session:
            merge_guest_cart(session['session_id'], user.id)

        session.permanent = True


        session['user_id'] = user.id
        flash(f'Welcome to XLOVEBEATS, {username}!', 'success')
        return redirect(url_for('public.home'))

    return redirect(url_for('public.home'))


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Email and password are required', 'error')
            return redirect(url_for('public.home'))

        user = get_user_by_email(email)
        if user and check_password_hash(user.password_hash, password):
            user.last_login = datetime.utcnow()
            session.permanent = True

            session['user_id'] = user.id
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(url_for('public.home'))
        flash('Invalid email or password', 'error')

    return redirect(url_for('public.home'))


@bp.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('public.home'))