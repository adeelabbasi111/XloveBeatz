"""
Pure utility functions: slug generation, price formatting, validation,
file helpers, and auth decorators.
"""
import re
import os
import logging
from functools import wraps

from flask import session, flash, redirect, url_for

logger = logging.getLogger(__name__)

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

def send_reset_email(to_email, reset_url):
    """Send password reset email using SMTP."""
    smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_user = os.getenv('SMTP_USER', '')
    smtp_pass = os.getenv('SMTP_PASS', '')
    from_name = os.getenv('FROM_NAME', 'XLoveBeats')

    if not smtp_user or not smtp_pass:
        print(f"[DEV MODE] Password reset link for {to_email}: {reset_url}")
        return False

    msg = MIMEMultipart('alternative')
    msg['Subject'] = 'Reset Your XLoveBeats Password'
    msg['From'] = f'{from_name} <{smtp_user}>'
    msg['To'] = to_email

    text_body = f"""
Hi,

You requested a password reset for your XLoveBeats account.

Click the link below to reset your password:
{reset_url}

This link will expire in 1 hour.

If you didn't request this, ignore this email.

— XLoveBeats Team
"""

    html_body = f"""
<div style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto; background: #111; color: #fff; padding: 40px 30px; border-radius: 12px;">
    <h2 style="color: #7c8df0; margin-bottom: 20px;">Reset Your Password</h2>
    <p style="color: #ccc; line-height: 1.6;">You requested a password reset for your XLoveBeats account.</p>
    <a href="{reset_url}" style="display: inline-block; background: linear-gradient(135deg, #7c8df0, #9d7cec); color: #fff; text-decoration: none; padding: 14px 32px; border-radius: 12px; font-weight: 700; margin: 20px 0;">Reset Password</a>
    <p style="color: #888; font-size: 0.85rem;">This link will expire in 1 hour.</p>
    <p style="color: #888; font-size: 0.85rem;">If you didn't request this, ignore this email.</p>
    <hr style="border: 1px solid #333; margin: 24px 0;">
    <p style="color: #555; font-size: 0.75rem;">— XLoveBeats Team</p>
</div>
"""

    msg.attach(MIMEText(text_body, 'plain'))
    msg.attach(MIMEText(html_body, 'html'))

    try:
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Email send failed: {e}")
        return False

# =========================
# SLUG GENERATION (single source of truth)
# =========================



def slugify(text):
    """'Indian Beat Pack' -> 'indian-beat-pack'"""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text


def generate_unique_slug(name, model_class):
    """Generate a unique slug, appending -1, -2 etc. if needed."""
    base = slugify(name)
    slug = base
    counter = 1
    while model_class.query.filter_by(slug=slug).first():
        slug = f"{base}-{counter}"
        counter += 1
    return slug


# =========================
# PRICE FORMATTING
# =========================

def cents_to_rupees(cents):
    """10050 -> '₹100.50'"""
    return f"\u20b9{cents / 100:.2f}"


def rupees_to_cents(rupees):
    """100.50 -> 10050"""
    return int(round(rupees * 100))


# =========================
# SESSION / AUTH
# =========================

def get_current_user():
    """Retrieve logged-in user from session."""
    from helpers.models import User   # late import to avoid circular dependency
    user_id = session.get('user_id')
    return User.query.get(user_id) if user_id else None


def get_current_cart():
    """Get cart for current user or guest session."""
    import uuid
    from helpers.services import get_or_create_cart

    user = get_current_user()
    if user:
        return get_or_create_cart(user_id=user.id)
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return get_or_create_cart(session_id=session['session_id'])


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not get_current_user():
            flash('Please login first', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user or not user.is_admin:
            flash('Admin access required', 'error')
            return redirect(url_for('public.home'))
        return f(*args, **kwargs)
    return decorated


# =========================
# INPUT VALIDATION
# =========================

def validate_email(email):
    if not email:
        return False
    return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email))


def validate_password(password):
    """Returns (is_valid, error_message)."""
    if not password or len(password) < 6:
        return False, "Password must be at least 6 characters"
    return True, ""


# =========================
# FILE UPLOAD HELPERS
# =========================

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


def save_upload(file_field, prefix, upload_folder):
    """Save file and return filename, or None."""
    from werkzeug.utils import secure_filename
    if file_field and file_field.filename:
        filename = secure_filename(f"{prefix}_{file_field.filename}")
        file_field.save(os.path.join(upload_folder, filename))
        return filename
    return None


# =========================
# TEMPLATE FILTERS
# =========================

def register_template_filters(app):
    @app.template_filter('rupees')
    def rupees_filter(cents):
        return cents_to_rupees(cents)