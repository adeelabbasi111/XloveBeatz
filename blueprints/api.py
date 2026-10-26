import logging
from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from helpers.utils import get_current_user, validate_email, validate_password
from helpers.services import create_user, get_user_by_email, get_user_by_email_or_username, merge_guest_cart, get_user_purchases
from helpers.models import User , db
from helpers.models import DiscountCode, Product, BeatDetail, Order, OrderItem
import uuid
from datetime import datetime
logger = logging.getLogger(__name__)
bp = Blueprint('api', __name__)


@bp.route('/api/health')
def health_check():
    from helpers.models import Product
    return jsonify({
        "status": "online",
        "service": "xlovebeats-api",
        "db": "sqlite",
        "products": Product.query.count(),
    })


@bp.route('/api/auth/me')
def auth_me():
    user = get_current_user()
    if user:
        return jsonify({
            'logged_in': True,
            'user': {'id': user.id, 'username': user.username,
                     'email': user.email, 'is_admin': user.is_admin},
        })
    return jsonify({'logged_in': False})



@bp.route('/api/auth/signup', methods=['POST'])
def api_signup():
    data = request.json or {}
    username = data.get('username', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    confirm = data.get('confirm_password', '')

    if not username or not email or not password:
        return jsonify(success=False, error='All fields are required'), 400
    if len(username) < 3:
        return jsonify(success=False, error='Username must be at least 3 characters'), 400
    if not validate_email(email):
        return jsonify(success=False, error='Please enter a valid email'), 400
    ok, msg = validate_password(password)
    if not ok:
        return jsonify(success=False, error=msg), 400
    if password != confirm:
        return jsonify(success=False, error='Passwords do not match'), 400
    if get_user_by_email(email):
        return jsonify(success=False, error='Email already registered'), 400
    if User.query.filter(db.func.lower(User.username) == username.lower()).first():
        return jsonify(success=False, error='Username is already taken'), 400

    user = create_user(username, email, generate_password_hash(password))

    try:
        from helpers.utils import send_promo_email
        send_promo_email(user.email)
    except Exception as e:
        print("Failed to send promo email:", e)

    if 'session_id' in session:
        merge_guest_cart(session['session_id'], user.id)

    session.permanent = True
    session['user_id'] = user.id
    return jsonify(success=True, message=f'Welcome to XLOVEBEATS, {username}!',
                   user={'id': user.id, 'username': user.username, 'email': user.email})

@bp.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.json or {}
    identifier = (data.get('email') or data.get('username') or '').strip()
    password = data.get('password', '').strip()

    if not identifier or not password:
        return jsonify(success=False, error='Email or username and password are required'), 400

    user = get_user_by_email_or_username(identifier)
    if user and check_password_hash(user.password_hash, password):
        user.last_login = datetime.utcnow()
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
        session.permanent = True
        session['user_id'] = user.id
        return jsonify(success=True, message=f'Welcome back, {user.username}!',
                       user={'id': user.id, 'username': user.username,
                             'email': user.email, 'is_admin': user.is_admin})
    return jsonify(success=False, error='Invalid email or password'), 401


@bp.route('/api/auth/logout', methods=['POST'])
def api_logout():
    session.pop('user_id', None)
    return jsonify(success=True, message='Logged out successfully')


@bp.route('/api/user/purchases')
def user_purchases():
    user = get_current_user()
    if not user:
        return jsonify(error='Not logged in'), 401
    return jsonify(purchases=get_user_purchases(user.id))



@bp.route('/api/validate-coupon', methods=['POST'])
def validate_coupon():
    data = request.json or {}
    code = (data.get('code') or '').strip().upper()
    subtotal_cents = int(float(data.get('subtotal', 0)) * 100)

    from helpers.geo import get_geo_pricing
    geo_info = get_geo_pricing()
    if geo_info['is_foreign']:
        rate = current_app.config.get('USD_INR_EXCHANGE_RATE', 85.0)
        mult = geo_info['multiplier']
        if mult > 0:
            subtotal_cents = int((subtotal_cents * rate) / mult)

    if not code:
        return jsonify(valid=False, error='Please enter a coupon code'), 400

    coupon = DiscountCode.query.filter_by(code=code).first()

    if not coupon:
        return jsonify(valid=False, error='Invalid coupon code'), 404

    if not coupon.is_active:
        return jsonify(valid=False, error='This coupon is no longer active'), 400

    if coupon.expires_at and coupon.expires_at < datetime.utcnow():
        return jsonify(valid=False, error='This coupon has expired'), 400

    if coupon.max_uses > 0 and coupon.used_count >= coupon.max_uses:
        return jsonify(valid=False, error='This coupon has reached its usage limit'), 400

    # Store original values
    res_discount_value = float(coupon.discount_value)
    res_max_discount = float(coupon.max_discount_cents / 100) if coupon.max_discount_cents > 0 else None
    res_min_order = float(coupon.min_order_cents / 100) if coupon.min_order_cents > 0 else None
    
    if coupon.discount_type == 'percentage':
        pass
    elif coupon.discount_type == 'bogo':
        pass
    else:
        if geo_info['is_foreign']:
            rate = current_app.config.get('USD_INR_EXCHANGE_RATE', 85.0)
            mult = geo_info['multiplier']
            res_discount_value = round((res_discount_value * mult) / rate, 2)
            if res_max_discount is not None:
                res_max_discount = round((res_max_discount * mult) / rate, 2)
            if res_min_order is not None:
                res_min_order = round((res_min_order * mult) / rate, 2)

    sym = geo_info['currency_symbol']

    if coupon.discount_type != 'bogo' and coupon.min_order_cents > 0 and subtotal_cents < coupon.min_order_cents:
        return jsonify(valid=False, error=f'Minimum order amount is {sym}{res_min_order:.2f}'), 400

    # Build description for frontend
    if coupon.discount_type == 'percentage':
        desc = f"{coupon.discount_value}% off"
        if res_max_discount:
            desc += f" (max {sym}{res_max_discount})"
    elif coupon.discount_type == 'bogo':
        res_min_order = coupon.min_order_cents
        res_discount_value = coupon.discount_value
        desc = f"Buy {res_min_order} Get {res_discount_value} Free"
    else:
        desc = f"{sym}{res_discount_value} off"

    return jsonify(
        valid=True,
        code=coupon.code,
        discount_type=coupon.discount_type,
        discount_value=res_discount_value,
        max_discount=res_max_discount,
        min_order=res_min_order,
        description=desc
    )

@bp.route('/api/beat/claim-free/<int:product_id>', methods=['POST'])
def claim_free_beat(product_id):
    user = get_current_user()
    if not user:
        return jsonify(success=False, error='Please log in to claim this free beat.', login_required=True), 401

    product = Product.query.get(product_id)
    if not product or product.product_type != 'beat':
        return jsonify(success=False, error='Invalid beat'), 404

    detail = BeatDetail.query.filter_by(product_id=product.id).first()
    if not detail or not detail.is_free:
        return jsonify(success=False, error='This beat is not available for free.'), 400

    # Check if user already claimed/purchased this product
    existing_item = (
        OrderItem.query.join(Order)
        .filter(Order.user_id == user.id, Order.payment_status == 'paid', OrderItem.product_id == product.id)
        .first()
    )
    if existing_item:
        return jsonify(
            success=True,
            already_claimed=True,
            message=f"'{product.name}' is already in your account! Check your dashboard to download.",
            dashboard_url='/dashboard'
        )

    # Create free order and order item
    order = Order(
        user_id=user.id,
        email=user.email,
        total_cents=0,
        payment_status='paid',
        payment_method='free',
        transaction_id=f"FREE-{uuid.uuid4().hex[:12].upper()}"
    )
    db.session.add(order)
    db.session.flush()

    order_item = OrderItem(
        order_id=order.id,
        product_id=product.id,
        license_id=None,
        price_paid_cents=0
    )
    db.session.add(order_item)
    db.session.commit()

    return jsonify(
        success=True,
        message=f"'{product.name}' added to your account! Check your dashboard to download.",
        dashboard_url='/dashboard'
    )
