"""
Data-access and business-logic layer.
All database queries go through here -- routes never query the ORM directly.
"""
import logging
from datetime import datetime, timedelta

from helpers.models import (
    db, User, Product, BeatDetail, BeatPack, BeatLicensePrice, Cart, CartItem,
    Order, OrderItem, Download,
    SiteSettings, ActivityLog,
)

logger = logging.getLogger(__name__)


# =========================
# USER
# =========================

def create_user(username, email, password_hash):
    user = User(username=username, email=email, password_hash=password_hash)
    db.session.add(user)
    db.session.commit()
    logger.info("User created: %s", email)
    return user


def get_user_by_email(email):
    return User.query.filter_by(email=email).first()


# =========================
# PRODUCT (read)
# =========================

def get_homepage_products(limit=8):
    beat_packs = Product.query.filter_by(product_type='pack', is_active=True).all()
    beats = (
        Product.query
        .filter_by(product_type='beat', is_active=True)
        .order_by(Product.created_at.desc())
        .limit(limit)
        .all()
    )
    vocal_presets = Product.query.filter_by(product_type='preset', is_active=True).all()
    return beat_packs, beats, vocal_presets


def get_player_beats(pack_id=None):
    """Return (beats, pack_info_or_None, error_msg_or_None)."""
    if pack_id:
        pack_obj = BeatPack.query.get(pack_id)
        if not pack_obj:
            return None, None, "Pack not found"
        beats = (
            Product.query
            .options(db.joinedload(Product.beat_detail))
            .join(BeatDetail)
            .filter(BeatDetail.pack_id == pack_id, Product.is_active == True)
            .all()
        )
        return beats, pack_obj, None
    else:
        beats = (
            Product.query
            .options(db.joinedload(Product.beat_detail))
            .filter_by(product_type='beat', is_active=True)
            .all()
        )
        return beats, None, None


def build_beats_data(beats):
    """Batch-build beat data dicts -- eliminates N+1 on license prices."""
    beat_ids = [b.id for b in beats]

    all_prices = (
        BeatLicensePrice.query
        .options(db.joinedload(BeatLicensePrice.license))
        .filter(BeatLicensePrice.beat_id.in_(beat_ids))
        .all()
    )
    prices_by_beat = {}
    for lp in all_prices:
        prices_by_beat.setdefault(lp.beat_id, []).append(lp)

    result = []
    for beat in beats:
        detail = beat.beat_detail  # already eager-loaded
        license_tiers = {}
        for lp in prices_by_beat.get(beat.id, []):
            tier_name = lp.license.name.lower()
            license_tiers[tier_name] = {
                'price': lp.price_cents / 100 if lp.price_cents else 0,
                'files': lp.included_files,
                'tags': lp.tags,
            }
        result.append({
            'id': beat.id,
            'name': beat.name,
            'bpm': detail.bpm if detail else 0,
            'key': detail.musical_key if detail else '',
            'genre': detail.genre if detail else '',
            'duration': detail.duration if detail else '',
            'price': beat.price_cents / 100,
            'pack_id': detail.pack_id if detail else None,
            'license_tiers': license_tiers,
            'preview_audio': detail.preview_audio if detail else None,
        })
    return result


def get_beat_with_details(beat_id):
    product = Product.query.get(beat_id)
    if not product or product.product_type != 'beat':
        return None
    detail = BeatDetail.query.filter_by(product_id=beat_id).first()
    licenses = (
        BeatLicensePrice.query
        .options(db.joinedload(BeatLicensePrice.license))
        .filter_by(beat_id=beat_id)
        .all()
    )
    return {'product': product, 'detail': detail, 'licenses': licenses}


# =========================
# ORDER
# =========================

def create_order(user_id, total_cents, payment_method, email=None, transaction_id=None):
    order = Order(
        user_id=user_id, email=email, total_cents=total_cents,
        payment_method=payment_method, transaction_id=transaction_id,
        payment_status="pending",
    )
    db.session.add(order)
    db.session.commit()
    logger.info("Order #%s created for %s", order.id, email)
    return order


def mark_order_paid(order_id, transaction_id):
    order = Order.query.get(order_id)
    if order:
        order.payment_status = "paid"
        order.transaction_id = transaction_id
        db.session.commit()
        logger.info("Order #%s marked paid", order_id)
    return order


def add_order_item(order_id, product_id, price_paid_cents, license_id=None):
    item = OrderItem(
        order_id=order_id, product_id=product_id,
        license_id=license_id, price_paid_cents=price_paid_cents,
    )
    db.session.add(item)
    db.session.commit()
    return item


def get_user_orders(user_id):
    """Eagerly load items + product + license to avoid N+1."""
    return (
        Order.query
        .options(
            db.joinedload(Order.items).joinedload(OrderItem.product),
            db.joinedload(Order.items).joinedload(OrderItem.license),
        )
        .filter_by(user_id=user_id)
        .order_by(Order.created_at.desc())
        .all()
    )


# =========================
# CART
# =========================

def get_or_create_cart(user_id=None, session_id=None):
    if user_id:
        cart = Cart.query.filter_by(user_id=user_id).first()
        if not cart:
            cart = Cart(user_id=user_id)
            db.session.add(cart)
            db.session.commit()
    elif session_id:
        cart = Cart.query.filter_by(session_id=session_id).first()
        if not cart:
            cart = Cart(session_id=session_id)
            db.session.add(cart)
            db.session.commit()
    else:
        raise ValueError("Either user_id or session_id is required")
    return cart


def add_to_cart(cart_id, product_id, quantity=1, license_id=None, price_cents=0):
    existing = CartItem.query.filter_by(
        cart_id=cart_id, product_id=product_id, license_id=license_id,
    ).first()
    if existing:
        existing.quantity += quantity
        db.session.commit()
        return existing
    item = CartItem(
        cart_id=cart_id, product_id=product_id,
        quantity=quantity, license_id=license_id,
        price_cents_at_time=price_cents,
    )
    db.session.add(item)
    db.session.commit()
    return item


def remove_from_cart(cart_item_id):
    item = CartItem.query.get(cart_item_id)
    if item:
        db.session.delete(item)
        db.session.commit()
    return True


def get_cart_items(cart_id):
    """Eagerly load product and license."""
    return (
        CartItem.query
        .options(db.joinedload(CartItem.product), db.joinedload(CartItem.license))
        .filter_by(cart_id=cart_id)
        .all()
    )


def clear_cart(cart_id):
    CartItem.query.filter_by(cart_id=cart_id).delete()
    db.session.commit()


def merge_guest_cart(session_id, user_id):
    guest_cart = Cart.query.filter_by(session_id=session_id).first()
    if guest_cart:
        guest_cart.user_id = user_id
        guest_cart.session_id = None
        db.session.commit()


# =========================
# DOWNLOAD
# =========================

def track_download(user_id, product_id):
    dl = Download.query.filter_by(user_id=user_id, product_id=product_id).first()
    if not dl:
        dl = Download(user_id=user_id, product_id=product_id, download_count=0)
        db.session.add(dl)
    dl.download_count += 1
    dl.last_downloaded = datetime.utcnow()   # FIX: was func.now()
    db.session.commit()
    return dl


# =========================
# ADMIN HELPERS
# =========================

def log_activity(admin_id, action, entity_type, entity_id, details="", ip_address=""):
    log = ActivityLog(
        admin_id=admin_id, action=action, entity_type=entity_type,
        entity_id=entity_id, details=details, ip_address=ip_address,
    )
    db.session.add(log)
    db.session.commit()
    return log


def get_site_setting(key, default=""):
    setting = SiteSettings.query.filter_by(key=key).first()
    return setting.value if setting else default


def set_site_setting(key, value):
    setting = SiteSettings.query.filter_by(key=key).first()
    if setting:
        setting.value = value
    else:
        setting = SiteSettings(key=key, value=value)
        db.session.add(setting)
    db.session.commit()


def get_admin_stats():
    return {
        'total_products': Product.query.count(),
        'total_beats': Product.query.filter_by(product_type='beat').count(),
        'total_packs': Product.query.filter_by(product_type='pack').count(),
        'total_presets': Product.query.filter_by(product_type='preset').count(),
        'total_orders': Order.query.count(),
        'paid_orders': Order.query.filter_by(payment_status='paid').count(),
        'pending_orders': Order.query.filter_by(payment_status='pending').count(),
        'total_revenue_cents': (
            db.session.query(db.func.sum(Order.total_cents))
            .filter(Order.payment_status == 'paid').scalar() or 0
        ),
        'total_users': User.query.count(),
        'total_downloads': Download.query.count(),
    }


def get_monthly_revenue(days=180):
    cutoff = datetime.utcnow() - timedelta(days=days)
    return (
        db.session.query(
            db.func.strftime('%Y-%m', Order.created_at).label('month'),
            db.func.sum(Order.total_cents).label('total'),
        )
        .filter(Order.payment_status == 'paid', Order.created_at >= cutoff)
        .group_by('month').order_by('month')
        .all()
    )


def get_top_products(limit=10):
    return (
        db.session.query(Product.name, db.func.count(OrderItem.id).label('sold'))
        .join(OrderItem, Product.id == OrderItem.product_id)
        .join(Order, OrderItem.order_id == Order.id)
        .filter(Order.payment_status == 'paid')
        .group_by(Product.id, Product.name)
        .order_by(db.func.count(OrderItem.id).desc())
        .limit(limit).all()
    )


def get_genre_distribution():
    return (
        db.session.query(BeatDetail.genre, db.func.count(Product.id).label('count'))
        .join(Product, BeatDetail.product_id == Product.id)
        .filter(Product.product_type == 'beat')
        .group_by(BeatDetail.genre).all()
    )


def get_user_purchases(user_id):
    """Get all purchases with eager-loaded relationships."""
    orders = (
        Order.query
        .options(
            db.joinedload(Order.items).joinedload(OrderItem.product),
            db.joinedload(Order.items).joinedload(OrderItem.license),
        )
        .filter_by(user_id=user_id, payment_status='paid')
        .all()
    )
    purchases = []
    for order in orders:
        for item in order.items:
            dl = Download.query.filter_by(user_id=user_id, product_id=item.product_id).first()
            purchases.append({
                'order_id': order.id,
                'order_date': order.created_at.strftime('%d %b %Y'),
                'product_id': item.product.id,
                'product_name': item.product.name,
                'product_type': item.product.product_type,
                'license': item.license.name if item.license else 'N/A',
                'price_paid': item.price_paid_cents / 100,
                'download_count': dl.download_count if dl else 0,
                'slug': item.product.slug,
            })
    return purchases