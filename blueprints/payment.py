import logging
import hmac
import hashlib

from flask import Blueprint, request, jsonify, render_template, session, current_app
from helpers.models import Product, License, BeatLicensePrice, Cart, db, Order
from helpers.utils import get_current_user
from helpers.services import create_order, add_order_item, mark_order_paid, clear_cart

logger = logging.getLogger(__name__)
bp = Blueprint('payment', __name__)

# ⚠️ TEMP: Set to True to bypass Razorpay for testing
BYPASS_RAZORPAY = True


@bp.route('/api/create-razorpay-order', methods=['POST'])
def create_razorpay_order():
    data = request.json or {}
    cart_items = data.get('items', [])
    if not cart_items:
        return jsonify({"error": "Cart is empty"}), 400

    total_cents, line_items = 0, []

    for item in cart_items:
        product = Product.query.get(item.get('id'))
        if not product:
            continue

        item_type = item.get('type')
        license_type = item.get('license', 'basic')
        price_cents, name = 0, ""

        if item_type == 'beat':
            lic = License.query.filter_by(name=license_type.capitalize()).first()
            if lic:
                lp = BeatLicensePrice.query.filter_by(beat_id=product.id, license_id=lic.id).first()
                if lp:
                    price_cents = lp.price_cents
                    name = f"{product.name} ({lic.name} License)"
            if price_cents == 0:
                price_cents = product.price_cents
                name = product.name
        elif item_type in ('pack', 'preset'):
            price_cents = product.price_cents
            name = product.name

        if price_cents > 0:
            total_cents += price_cents
            line_items.append({
                'product_id': product.id, 'name': name,
                'price_cents': price_cents,
                'license_type': license_type if item_type == 'beat' else None,
            })

    if total_cents <= 0:
        return jsonify({"error": "Invalid items"}), 400

    user = get_current_user()
    email = user.email if user else (data.get('email') or '').strip()
    if not user and not email:
        return jsonify({"error": "Email is required for guest checkout"}), 400

    try:
        order = create_order(
            user_id=user.id if user else None,
            total_cents=total_cents, payment_method='razorpay', email=email,
        )
        for li in line_items:
            lic_id = None
            if li['license_type']:
                lic = License.query.filter_by(name=li['license_type'].capitalize()).first()
                if lic:
                    lic_id = lic.id
            add_order_item(order.id, li['product_id'], li['price_cents'], lic_id)

        # ── BYPASS MODE: Skip Razorpay, return fake order data ──
        if BYPASS_RAZORPAY:
            logger.info("[TEST] Bypassing Razorpay for order %s (₹%.2f)", order.id, total_cents / 100)
            return jsonify({
                "order_id": "order_test_" + str(order.id),
                "db_order_id": order.id,
                "amount": total_cents,
                "currency": "INR",
                "key_id": "rzp_test_bypass",
                "bypass": True,
            })

        # ── NORMAL MODE: Create real Razorpay order ──
        rzp = current_app.razorpay_client.order.create({
            "amount": total_cents,
            "currency": "INR",
            "receipt": f"order_xlb_{order.id}",
            "notes": {"db_order_id": str(order.id)},
        })

        return jsonify({
            "order_id": rzp['id'], "db_order_id": order.id,
            "amount": rzp['amount'], "currency": rzp['currency'],
            "key_id": current_app.razorpay_key_id,
        })
    except Exception as e:
        logger.error("Order creation failed: %s", e)
        db.session.rollback()
        return jsonify({"error": "Order creation error"}), 500


@bp.route('/api/verify-razorpay-payment', methods=['POST'])
def verify_payment():
    data = request.json or {}
    db_order_id = data.get('db_order_id')

    if not db_order_id:
        return jsonify({"status": "failed", "message": "Missing order ID"}), 400

    # ── BYPASS MODE: Directly mark as paid ──
    if BYPASS_RAZORPAY:
        try:
            mark_order_paid(db_order_id, "test_payment_" + str(db_order_id))
            _clear_user_cart()
            logger.info("[TEST] Order %s marked as paid (bypass)", db_order_id)
            return jsonify({
                "status": "success",
                "message": "Payment verified (test mode)!",
                "order_id": db_order_id,
            })
        except Exception as e:
            logger.error("Test payment error: %s", e)
            db.session.rollback()
            return jsonify({"status": "failed", "message": "Verification error"}), 500

    # ── NORMAL MODE: Verify Razorpay signature ──
    rzp_pay_id = data.get('razorpay_payment_id')
    rzp_order_id = data.get('razorpay_order_id')
    rzp_sig = data.get('razorpay_signature')

    if not all([rzp_pay_id, rzp_order_id, rzp_sig]):
        return jsonify({"status": "failed", "message": "Missing payment data"}), 400

    expected = hmac.new(
        current_app.razorpay_key_secret.encode(),
        f"{rzp_order_id}|{rzp_pay_id}".encode(),
        hashlib.sha256,
    ).hexdigest()

    if expected != rzp_sig:
        logger.warning("Invalid Razorpay signature for order %s", db_order_id)
        return jsonify({"status": "failed", "message": "Invalid signature"}), 400

    try:
        mark_order_paid(db_order_id, rzp_pay_id)
        _clear_user_cart()
        return jsonify({"status": "success", "message": "Payment verified!", "order_id": db_order_id})
    except Exception as e:
        logger.error("Payment verification DB error: %s", e)
        db.session.rollback()
        return jsonify({"status": "failed", "message": "Verification error"}), 500


def _clear_user_cart():
    """Clear cart after successful payment."""
    user = get_current_user()
    if user:
        cart = Cart.query.filter_by(user_id=user.id).first()
    elif 'session_id' in session:
        cart = Cart.query.filter_by(session_id=session['session_id']).first()
    else:
        cart = None
    if cart:
        clear_cart(cart.id)


@bp.route('/checkout/success')
def checkout_success():
    order_id = request.args.get('order_id')
    order = Order.query.get(order_id) if order_id else None

    user = get_current_user()
    if order and user and order.user_id and order.user_id != user.id:
        order = None

    return render_template('success.html', order=order, site_title="XLOVEBEATZ")