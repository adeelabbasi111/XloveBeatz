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