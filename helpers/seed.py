import logging
from werkzeug.security import generate_password_hash
from helpers.models import db,User
logger = logging.getLogger(__name__)
import os

ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')


def seed_initial_data():
    # ---- DEFAULT ADMIN ----
    if not User.query.filter_by(email=ADMIN_EMAIL).first():
        db.session.add(User(
            username='admin', email=ADMIN_EMAIL,
            password_hash=generate_password_hash(ADMIN_PASSWORD), is_admin=True,
        ))

    db.session.commit()
    logger.info("Seeding complete!")