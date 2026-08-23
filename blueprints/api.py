import logging
from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from helpers.utils import get_current_user, validate_email, validate_password
from helpers.services import create_user, get_user_by_email, merge_guest_cart, get_user_purchases
from helpers.models import User , db
from helpers.models import DiscountCode
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

    if 'session_id' in session:
        merge_guest_cart(session['session_id'], user.id)

    session['user_id'] = user.id
    return jsonify(success=True, message=f'Welcome to XLOVEBEATS, {username}!',
                   user={'id': user.id, 'username': user.username, 'email': user.email})

@bp.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.json or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify(success=False, error='Email and password are required'), 400

    user = get_user_by_email(email)
    if user and check_password_hash(user.password_hash, password):
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
    
    if geo_info['is_foreign']:
        rate = current_app.config.get('USD_INR_EXCHANGE_RATE', 85.0)
        mult = geo_info['multiplier']
        # For percentage, discount_value is the %, so it stays the same!
        # Only transform if it's a fixed amount
        if coupon.discount_type == 'fixed':
            res_discount_value = round((res_discount_value * mult) / rate, 2)
        if res_max_discount is not None:
            res_max_discount = round((res_max_discount * mult) / rate, 2)
        if res_min_order is not None:
            res_min_order = round((res_min_order * mult) / rate, 2)

    sym = geo_info['currency_symbol']

    if coupon.min_order_cents > 0 and subtotal_cents < coupon.min_order_cents:
        return jsonify(valid=False, error=f'Minimum order amount is {sym}{res_min_order:.2f}'), 400
    # Build description for frontend
    if coupon.discount_type == 'percentage':
        desc = f"{coupon.discount_value}% off"
        if res_max_discount:
            desc += f" (max {sym}{res_max_discount})"
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