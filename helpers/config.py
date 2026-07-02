import os
from datetime import timedelta


class Config:
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    # ─── Data Directory Structure ───────────────────────────────────
    DATA_DIR = os.path.join(BASE_DIR, 'static', 'data')

    # --- Security: secret key MUST be set in production ---
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        if os.environ.get('FLASK_ENV') == 'production':
            raise ValueError(
                "SECRET_KEY must be set in production. "
                "Generate with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        SECRET_KEY = os.urandom(32).hex()

    # --- Database ---
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'instance', 'xlovebeats.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Sessions ---
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'

    # --- File uploads ---
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or \
        os.path.join(BASE_DIR, '../static', 'data')
    MAX_CONTENT_LENGTH = 1000 * 1024 * 1024  # 1 GB
    ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'flac', 'ogg'}
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    ALLOWED_ARCHIVE_EXTENSIONS = {'zip', 'rar'}

    # --- Razorpay (REQUIRED in production) ---
    RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', '')
    RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '')

    # --- Rate limiting ---
    RATELIMIT_DEFAULT = "200 per day, 50 per hour"
    RATELIMIT_STORAGE_URI = "memory://"

    # --- Pagination ---
    PRODUCTS_PER_PAGE = 12
    ORDERS_PER_PAGE = 20
    LOGS_PER_PAGE = 50

    # --- Display limits (no more magic numbers) ---
    HOMEPAGE_BEAT_LIMIT = 8
    ADMIN_RECENT_LIMIT = 10
    ADMIN_LOGS_LIMIT = 100
    ANALYTICS_PERIOD_DAYS = 180

