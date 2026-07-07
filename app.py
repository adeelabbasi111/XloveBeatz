"""
XLOVEBEATS -- Application factory and entry point.
"""
import os
import logging

from flask import Flask
from flask_wtf import CSRFProtect
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from helpers.config import Config
from helpers.models import db, init_db
from helpers.utils import register_template_filters
from dotenv import load_dotenv

load_dotenv()  # ← Sirf YAHAN

# Extensions (initialized without app, bound in create_app)
csrf = CSRFProtect()
migrate = Migrate()
limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    from blueprints.admin import ALL_DATA_FOLDERS, get_data_path
    with app.app_context():
        for folder in ALL_DATA_FOLDERS:
            get_data_path(folder)

    # ---- Logging ----
    logging.basicConfig(
        level=logging.DEBUG if app.debug else logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    )

    # ---- Extensions ----
    db.init_app(app)
    init_db(app)               # creates tables + seeds default licenses
    csrf.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)



    # ---- Razorpay client ----
    import razorpay
    app.razorpay_key_id = app.config['RAZORPAY_KEY_ID']
    app.razorpay_key_secret = app.config['RAZORPAY_KEY_SECRET']
    app.razorpay_client = razorpay.Client(
        auth=(app.razorpay_key_id, app.razorpay_key_secret)
    )

    # ---- Jinja filters ----
    register_template_filters(app)

    # ---- Before-request: load current user into g ----
    @app.before_request
    def _load_user():
        from flask import g
        from helpers.utils import get_current_user
        g.user = get_current_user()

    # ---- Register blueprints ----
    from blueprints.public import bp as public_bp
    from blueprints.auth import bp as auth_bp
    from blueprints.cart import bp as cart_bp
    from blueprints.payment import bp as payment_bp
    from blueprints.dashboard import bp as dashboard_bp
    from blueprints.admin import bp as admin_bp
    from blueprints.api import bp as api_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(cart_bp)
    app.register_blueprint(payment_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    # ---- CSRF: exempt JSON-only API and payment blueprints ----
    csrf.exempt(payment_bp)     # Razorpay callbacks are JSON
    csrf.exempt(api_bp)         #AJAX endpoints use SameSite cookies

    # In app.py, inside create_app(), after registering blueprints:
    from helpers.services import get_site_setting
    app.jinja_env.globals['get_site_setting'] = get_site_setting

    # ---- Error handlers ----
    @app.errorhandler(404)
    def not_found(e):
        from flask import render_template
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        from flask import render_template
        db.session.rollback()      # FIX: reset broken session after DB error
        return render_template('500.html'), 500

    @app.errorhandler(429)
    def ratelimit_handler(e):
        from flask import jsonify
        return jsonify(error="Rate limit exceeded. Please try again later."), 429

    # ---- Seed data on first run ----
    with app.app_context():
        from helpers.seed import seed_initial_data
        seed_initial_data()

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)