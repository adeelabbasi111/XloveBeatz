import logging
import os
import time
import hashlib
from datetime import datetime

from flask import Blueprint, request, jsonify, render_template, session, current_app, redirect, url_for, flash, send_file
from helpers.models import Product, License, BeatLicensePrice, Cart, db, Order, OrderItem, User, GeneratedLicense, BeatDetail
from helpers.utils import get_current_user, login_required
from helpers.services import create_order, add_order_item, mark_order_paid, clear_cart
from helpers.license_generator import BeatLicenseGenerator
from helpers.models import DiscountCode


logger = logging.getLogger(__name__)
bp = Blueprint('payment', __name__)

# ⚠️ Set to True to bypass PayU and approve all orders instantly
TEST_MODE_PAYMENT = False


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
#  PAYU ORDER CREATION
# ═══════════════════════════════════════════════════════════════

@bp.route('/api/create-payu-order', methods=['POST'])
def create_payu_order():
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

        # PayU Hash Generation
        payu_key = current_app.config.get('PAYU_MERCHANT_KEY', '')
        payu_salt = current_app.config.get('PAYU_MERCHANT_SALT', '')
        
        txnid = f"order_xlb_{order.id}"
        amount = f"{final_inr:.2f}"
        productinfo = "Xlovebeats Order"
        firstname = user.username if user else "Guest"
        
        # Sequence: key|txnid|amount|productinfo|firstname|email|udf1|udf2|udf3|udf4|udf5||||||SALT
        hash_string = f"{payu_key}|{txnid}|{amount}|{productinfo}|{firstname}|{email}|||||||||||{payu_salt}"
        payu_hash = hashlib.sha512(hash_string.encode('utf-8')).hexdigest()
        
        surl = request.host_url.rstrip('/') + url_for('payment.payu_success')
        furl = request.host_url.rstrip('/') + url_for('payment.payu_failure')
        
        action_url = "https://secure.payu.in/_payment" if current_app.config.get('PAYU_ENV', 'production') == 'production' else "https://test.payu.in/_payment"
        
        return jsonify({
            "action": action_url,
            "key": payu_key,
            "txnid": txnid,
            "amount": amount,
            "productinfo": productinfo,
            "firstname": firstname,
            "email": email,
            "phone": "9999999999",
            "surl": surl,
            "furl": furl,
            "hash": payu_hash,
            "db_order_id": order.id
        })

    except Exception as e:
        logger.error("Order creation failed: %s", e)
        db.session.rollback()
        return jsonify({"error": "Order creation error"}), 500


# ═══════════════════════════════════════════════════════════════
#  PAYMENT VERIFICATION
# ═══════════════════════════════════════════════════════════════

@bp.route('/payment/payu-success', methods=['POST'])
def payu_success():
    data = request.form
    status = data.get('status', '')
    firstname = data.get('firstname', '')
    amount = data.get('amount', '')
    txnid = data.get('txnid', '')
    posted_hash = data.get('hash', '')
    key = data.get('key', '')
    productinfo = data.get('productinfo', '')
    email = data.get('email', '')
    udf1 = data.get('udf1', '')
    udf2 = data.get('udf2', '')
    udf3 = data.get('udf3', '')
    udf4 = data.get('udf4', '')
    udf5 = data.get('udf5', '')
    
    payu_salt = current_app.config.get('PAYU_MERCHANT_SALT', '')
    
    # Reverse hash: SALT|status||||||udf5|udf4|udf3|udf2|udf1|email|firstname|productinfo|amount|txnid|key
    hash_str = f"{payu_salt}|{status}||||||{udf5}|{udf4}|{udf3}|{udf2}|{udf1}|{email}|{firstname}|{productinfo}|{amount}|{txnid}|{key}"
    
    # Sometimes PayU includes additional fields depending on the integration (like additionalCharges), 
    # but the standard reverse hash is exactly as above if additionalCharges is not present.
    additional_charges = data.get('additionalCharges')
    if additional_charges:
        hash_str = f"{additional_charges}|{hash_str}"
        
    calc_hash = hashlib.sha512(hash_str.encode('utf-8')).hexdigest()
    
    if calc_hash == posted_hash and status == "success":
        db_order_id = txnid.replace("order_xlb_", "")
        payu_id = data.get('mihpayid', txnid)
        mark_order_paid(db_order_id, payu_id)
        
        # Clear cart using session workaround since we don't have access to current_user inside a webhook easily if cookies aren't passed
        _clear_user_cart()
        
        return redirect(url_for('payment.payment_success', order_id=db_order_id))
    else:
        logger.error("PayU Hash Mismatch or Failed Status. Calc: %s, Posted: %s", calc_hash, posted_hash)
        flash("Payment verification failed. If money was deducted, it will be refunded automatically.", "error")
        return redirect(url_for('public.home'))

@bp.route('/payment/payu-failure', methods=['POST'])
def payu_failure():
    logger.error("PayU Payment Failed")
    flash("Your payment was declined or cancelled. Please try again.", "error")
    return redirect(url_for('public.home'))


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