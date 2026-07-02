"""
Database models only. No business logic, no service functions.
"""
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, UniqueConstraint

db = SQLAlchemy()


# =========================
# MODELS
# =========================

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, server_default=func.now())
    last_login = db.Column(db.DateTime)

    carts = db.relationship("Cart", backref="user", lazy=True)
    orders = db.relationship("Order", backref="user", lazy=True)


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    product_type = db.Column(db.String(20), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, index=True)
    description = db.Column(db.Text)
    price_cents = db.Column(db.Integer, nullable=False)  # stored in paise (INR)
    cover_image = db.Column(db.String(500))
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, server_default=func.now())


class BeatPack(db.Model):
    __tablename__ = "beat_packs"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), unique=True)
    genre = db.Column(db.String(100), index=True)
    total_beats = db.Column(db.Integer, default=0)
    zip_path = db.Column(db.String(500), default='')

    product = db.relationship("Product", backref=db.backref("beat_pack", uselist=False))


class BeatDetail(db.Model):
    __tablename__ = "beat_details"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), unique=True)
    bpm = db.Column(db.Integer)
    musical_key = db.Column(db.String(20))
    genre = db.Column(db.String(100), index=True)
    duration = db.Column(db.String(20))

    preview_audio = db.Column(db.String(500))
    wav_file = db.Column(db.String(500))
    mp3_file = db.Column(db.String(500))
    project_file = db.Column(db.String(500))

    pack_id = db.Column(db.Integer, db.ForeignKey("beat_packs.id"), nullable=True, index=True)

    product = db.relationship("Product", backref=db.backref("beat_detail", uselist=False))


class VocalPreset(db.Model):
    __tablename__ = "vocal_presets"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), unique=True)
    supported_daw = db.Column(db.String(255))
    preset_zip = db.Column(db.String(500))

    product = db.relationship("Product", backref=db.backref("vocal_preset", uselist=False))


class License(db.Model):
    __tablename__ = "licenses"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)
    description = db.Column(db.Text)


class BeatLicensePrice(db.Model):
    __tablename__ = "beat_license_prices"
    __table_args__ = (
        UniqueConstraint('beat_id', 'license_id', name='uq_beat_license'),
    )

    id = db.Column(db.Integer, primary_key=True)
    beat_id = db.Column(db.Integer, db.ForeignKey("products.id"), index=True)
    license_id = db.Column(db.Integer, db.ForeignKey("licenses.id"), index=True)
    price_cents = db.Column(db.Integer)
    included_files = db.Column(db.String(255))
    tags = db.Column(db.String(255))

    beat = db.relationship("Product")
    license = db.relationship("License")


class Cart(db.Model):
    __tablename__ = "carts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    session_id = db.Column(db.String(100), index=True)
    created_at = db.Column(db.DateTime, server_default=func.now())
    updated_at = db.Column(db.DateTime, server_default=func.now(), onupdate=func.now())


class CartItem(db.Model):
    __tablename__ = "cart_items"

    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey("carts.id"), index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), index=True)
    license_id = db.Column(db.Integer, db.ForeignKey("licenses.id"), nullable=True)
    quantity = db.Column(db.Integer, default=1)
    price_cents_at_time = db.Column(db.Integer)

    cart = db.relationship("Cart", backref="items")
    product = db.relationship("Product")
    license = db.relationship("License")


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    email = db.Column(db.String(255))
    total_cents = db.Column(db.Integer)
    payment_status = db.Column(db.String(50), default="pending", index=True)
    payment_method = db.Column(db.String(50))
    transaction_id = db.Column(db.String(255), index=True)
    created_at = db.Column(db.DateTime, server_default=func.now())


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), index=True)
    license_id = db.Column(db.Integer, db.ForeignKey("licenses.id"), nullable=True)
    price_paid_cents = db.Column(db.Integer)

    order = db.relationship("Order", backref="items")
    product = db.relationship("Product")
    license = db.relationship("License")


class GeneratedLicense(db.Model):
    __tablename__ = "generated_licenses"

    id = db.Column(db.Integer, primary_key=True)
    order_item_id = db.Column(db.Integer, db.ForeignKey("order_items.id"), index=True)
    buyer_name = db.Column(db.String(255))
    beat_name = db.Column(db.String(255))
    license_type = db.Column(db.String(100))
    pdf_path = db.Column(db.String(500))
    generated_at = db.Column(db.DateTime, server_default=func.now())

    order_item = db.relationship("OrderItem")


class Download(db.Model):
    __tablename__ = "downloads"
    __table_args__ = (
        UniqueConstraint('user_id', 'product_id', name='uq_user_product'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), index=True)
    download_count = db.Column(db.Integer, default=0)
    last_downloaded = db.Column(db.DateTime)

    user = db.relationship("User")
    product = db.relationship("Product")


class SiteSettings(db.Model):
    __tablename__ = "site_settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, server_default=func.now(), onupdate=func.now())


class DiscountCode(db.Model):
    __tablename__ = "discount_codes"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    discount_type = db.Column(db.String(20))
    discount_value = db.Column(db.Integer)
    min_order_cents = db.Column(db.Integer, default=0)
    max_uses = db.Column(db.Integer, default=0)
    used_count = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    expires_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, server_default=func.now())


class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    action = db.Column(db.String(100))
    entity_type = db.Column(db.String(50))
    entity_id = db.Column(db.Integer)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, server_default=func.now())

    admin = db.relationship("User")


class Newsletter(db.Model):
    __tablename__ = "newsletters"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    subscribed_at = db.Column(db.DateTime, server_default=func.now())
    is_active = db.Column(db.Boolean, default=True)


# =========================
# DATABASE INITIALIZATION
# =========================

def init_db(app):
    """Create tables and seed default license tiers."""
    with app.app_context():
        db.create_all()

        if License.query.count() == 0:
            db.session.add_all([
                License(name="Basic", description="MP3 + WAV"),
                License(name="Premium", description="MP3 + WAV + Stems"),
                License(name="Exclusive", description="Full ownership"),
            ])
            db.session.commit()