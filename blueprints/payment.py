import logging
import os
import time
from datetime import datetime

from flask import Blueprint, request, jsonify, render_template, session, current_app, redirect, url_for, flash, send_file
from helpers.models import Product, License, BeatLicensePrice, Cart, db, Order, OrderItem, User, GeneratedLicense, BeatDetail
from helpers.utils import get_current_user, login_required
from helpers.services import create_order, add_order_item, mark_order_paid, clear_cart
from helpers.license_generator import BeatLicenseGenerator
from helpers.models import DiscountCode


logger = logging.getLogger(__name__)
bp = Blueprint('payment', __name__)

# ⚠️ Set to True to bypass Cashfree and approve all orders instantly
TEST_MODE_PAYMENT = True


# ═══════════════════════════════════════════════════════════════
#  LICENSE GENERATION
# ═══════════════════════════════════════════════════════════════

def _generate_licenses_for_order(order):
    """DEPRECATED: Generate license PDFs for each beat item in the order."""

    generator = BeatLicenseGenerator()
    user = User.query.get(order.user_id) if order.user_id else None
    effective_date = order.created_at.strftime('%d-%m-%Y') if order.created_at else datetime.now().strftime('%d-%m-%Y')

    for item in order.items:
        product = item.product
        if not product or product.product_type != 'beat':
            continue

        if not item.license:
            continue

        license_type = item.license.name.lower()
        if license_type not in ('basic', 'premium', 'exclusive'):
            continue

        licensee_name = user.username if user else (order.email or 'Customer')
        beat_name = product.name
        price_paid = item.price_paid_cents / 100 if item.price_paid_cents else 0

        # Get beat details for specs
        beat_detail = BeatDetail.query.filter_by(product_id=product.id).first()

        license_data = {
            'licensee_legal_name': licensee_name,
            'artist_stage_name': '',
            'beat_name': beat_name,
            'effective_date': effective_date,
            'beat_price': str(int(price_paid)),
            'order_id': str(order.id),
            'transaction_id': order.transaction_id or '',
            'buyer_email': user.email if user else (order.email or ''),
            'bpm': beat_detail.bpm if beat_detail else None,
            'musical_key': beat_detail.musical_key if beat_detail else None,
            'genre': beat_detail.genre if beat_detail else None,
            'duration': beat_detail.duration if beat_detail else None,
        }

        try:
            if license_type == 'basic':
                story = generator.generate_basic_license(license_data)
            elif license_type == 'premium':
                story = generator.generate_premium_license(license_data)
            elif license_type == 'exclusive':
                story = generator.generate_exclusive_license(license_data)
            else:
                continue

            output_dir = os.path.join(current_app.root_path, 'static', 'data', 'licenses')
            os.makedirs(output_dir, exist_ok=True)

            safe_name = licensee_name.replace(' ', '_').replace('/', '_')
            safe_beat = beat_name.replace(' ', '_').replace('/', '_')
            filename = f"{safe_name}_{item.license.name}_{safe_beat}"

            generator.save_license(story, filename, output_dir)
            db_path = f"data/licenses/{filename}.pdf"

            gen_lic = GeneratedLicense(
                order_item_id=item.id,
                buyer_name=licensee_name,
                beat_name=beat_name,
                license_type=item.license.name,
                pdf_path=db_path,
            )
            db.session.add(gen_lic)
            logger.info("License generated: %s (%s) for order %s", filename, license_type, order.id)

        except Exception as e:
            logger.error("License generation failed for %s - %s: %s", licensee_name, beat_name, e)

    db.session.commit()


# ═══════════════════════════════════════════════════════════════
#  CASHFREE ORDER CREATION
# ═══════════════════════════════════════════════════════════════

@bp.route('/api/create-cashfree-order', methods=['POST'])
def create_cashfree_order():
    data = request.json or {}
    cart_items = data.get('items', [])
    coupon_code = (data.get('coupon_code') or '').strip().upper()

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

    # ── Apply coupon discount server-side ──
    discount_cents = 0
    applied_coupon = None

    if coupon_code:
        coupon = DiscountCode.query.filter_by(code=coupon_code).first()
        if coupon and coupon.is_active:
            # Re-validate
            expired = coupon.expires_at and coupon.expires_at < datetime.utcnow()
            maxed = coupon.max_uses > 0 and coupon.used_count >= coupon.max_uses
            min_not_met = coupon.min_order_cents > 0 and total_cents < coupon.min_order_cents

            if not expired and not maxed and not min_not_met:
                if coupon.discount_type == 'percentage':
                    raw_discount = int(total_cents * coupon.discount_value / 100)
                    cap = coupon.max_discount_cents if coupon.max_discount_cents > 0 else raw_discount
                    discount_cents = min(raw_discount, cap)
                elif coupon.discount_type == 'fixed':
                    discount_cents = min(coupon.discount_value * 100, total_cents)

                applied_coupon = coupon

    final_cents = max(100, total_cents - discount_cents)  # Cashfree min is ₹1
    final_inr = final_cents / 100.0

    user = get_current_user()
    email = user.email if user else (data.get('email') or '').strip()
    if not user and not email:
        return jsonify({"error": "Email is required for guest checkout"}), 400

    try:
        order = create_order(
            user_id=user.id if user else None,
            total_cents=final_cents,
            payment_method='cashfree',
            email=email,
        )

        # Store coupon info on the order
        if applied_coupon:
            order.coupon_code = applied_coupon.code
            order.discount_cents = discount_cents
            applied_coupon.used_count += 1

        for li in line_items:
            lic_id = None
            if li['license_type']:
                lic = License.query.filter_by(name=li['license_type'].capitalize()).first()
                if lic:
                    lic_id = lic.id
            add_order_item(order.id, li['product_id'], li['price_cents'], lic_id)

        db.session.commit()

        # Create Cashfree Order
        if TEST_MODE_PAYMENT:
            cf_test_id = f"test_cf_{int(time.time())}"
            mark_order_paid(order.id, cf_test_id)
            return jsonify({
                "test_mode_success": True,
                "db_order_id": order.id,
                "cashfree_order_id": cf_test_id
            })

        headers = {
            "x-client-id": current_app.cashfree_app_id,
            "x-client-secret": current_app.cashfree_secret_key,
            "x-api-version": "2023-08-01",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        customer_id = f"cust_{user.id}" if user else f"guest_{int(time.time())}"

        payload = {
            "order_amount": final_inr,
            "order_currency": "INR",
            "order_id": f"order_xlb_{order.id}",
            "customer_details": {
                "customer_id": customer_id,
                "customer_email": email,
                "customer_phone": "9999999999"  # Dummy if not captured
            },
            "order_meta": {
                "return_url": request.host_url.rstrip('/') + "/payment-success?order_id={order_id}"
            }
        }
        
        import urllib.request
        import json
        
        req = urllib.request.Request("https://api.cashfree.com/pg/orders", data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
        
        try:
            with urllib.request.urlopen(req) as response:
                resp_data = json.loads(response.read().decode('utf-8'))
                
            if 'payment_session_id' in resp_data:
                return jsonify({
                    "payment_session_id": resp_data['payment_session_id'],
                    "db_order_id": order.id,
                    "cashfree_order_id": payload["order_id"]
                })
            else:
                logger.error("Cashfree API error (No session ID): %s", resp_data)
                return jsonify({"error": "Failed to create payment session"}), 500
                
        except urllib.error.URLError as e:
            error_msg = e.read().decode('utf-8') if hasattr(e, 'read') else str(e)
            logger.error("Cashfree API HTTP error: %s", error_msg)
            return jsonify({"error": f"Cashfree API Error: {error_msg}"}), 500

    except Exception as e:
        logger.error("Order creation failed: %s", e)
        db.session.rollback()
        return jsonify({"error": "Order creation error"}), 500


# ═══════════════════════════════════════════════════════════════
#  PAYMENT VERIFICATION
# ═══════════════════════════════════════════════════════════════

@bp.route('/api/verify-cashfree-payment', methods=['POST'])
def verify_payment():
    data = request.json or {}
    db_order_id = data.get('db_order_id')
    cf_order_id = data.get('order_id')

    if not db_order_id or not cf_order_id:
        return jsonify({"status": "failed", "message": "Missing order ID"}), 400

    import urllib.request
    import json
    import urllib.error
    
    headers = {
        "x-client-id": current_app.cashfree_app_id,
        "x-client-secret": current_app.cashfree_secret_key,
        "x-api-version": "2023-08-01",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        req = urllib.request.Request(f"https://api.cashfree.com/pg/orders/{cf_order_id}", headers=headers, method='GET')
        with urllib.request.urlopen(req) as response:
            resp_data = json.loads(response.read().decode('utf-8'))

        if resp_data.get("order_status") == "PAID":
            mark_order_paid(db_order_id, cf_order_id)
            _clear_user_cart()
        # Generate licenses
        order = Order.query.get(db_order_id)
        if order:
            # License PDFs are now generated on-demand when downloaded
            # _generate_licenses_for_order(order)
            pass

        return jsonify({"status": "success", "message": "Payment verified!", "order_id": db_order_id})
    except Exception as e:
        logger.error("Payment verification DB error: %s", e)
        db.session.rollback()
        return jsonify({"status": "failed", "message": "Verification error"}), 500


# ═══════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════
#  SUCCESS PAGE
# ═══════════════════════════════════════════════════════════════

@bp.route('/payment/success/<int:order_id>')
@login_required
def payment_success(order_id):
    user = get_current_user()

    order = (
        Order.query
        .options(
            db.joinedload(Order.items).joinedload(OrderItem.product),
            db.joinedload(Order.items).joinedload(OrderItem.license),
        )
        .filter_by(id=order_id, user_id=user.id)
        .first_or_404()
    )

    if order.payment_status != 'paid':
        flash('This order has not been paid yet', 'error')
        return redirect(url_for('dashboard.dashboard'))

    return render_template('payment_success.html', order=order, user=user)


# ═══════════════════════════════════════════════════════════════
#  DOWNLOAD ALL FILES (ZIP)
# ═══════════════════════════════════════════════════════════════

import zipfile
import io
from helpers.models import BeatDetail, VocalPreset, BeatPack

@bp.route('/download/order/<int:order_id>')
@login_required
def download_order_files(order_id):
    user = get_current_user()

    order = Order.query.filter_by(id=order_id, user_id=user.id).first_or_404()

    if order.payment_status != 'paid':
        flash('Order not paid', 'error')
        return redirect(url_for('dashboard.dashboard'))

    files_to_zip = []

    for item in order.items:
        product = item.product
        if not product:
            continue

        file_path = None

        if product.product_type == 'beat':
            detail = BeatDetail.query.filter_by(product_id=product.id).first()
            if detail:
                file_path = detail.wav_file or detail.mp3_file

        elif product.product_type == 'preset':
            preset = VocalPreset.query.filter_by(product_id=product.id).first()
            if preset:
                file_path = preset.preset_zip

        elif product.product_type == 'pack':
            pack = BeatPack.query.filter_by(product_id=product.id).first()
            if pack:
                file_path = pack.zip_path

        if file_path:
            abs_path = os.path.join(current_app.root_path, 'static', file_path)
            if os.path.exists(abs_path):
                display_name = os.path.basename(file_path)
                files_to_zip.append((abs_path, display_name))

    if not files_to_zip:
        flash('No downloadable files found for this order', 'error')
        return redirect(url_for('payment.payment_success', order_id=order_id))

    # Single file → serve directly
    if len(files_to_zip) == 1:
        return send_file(files_to_zip[0][0], as_attachment=True)

    # Multiple files → ZIP
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for abs_path, display_name in files_to_zip:
            zf.write(abs_path, display_name)

    zip_buffer.seek(0)

    return send_file(
        zip_buffer,
        as_attachment=True,
        download_name=f'XLoveBeats_Order_{order.id}.zip',
        mimetype='application/zip'
    )