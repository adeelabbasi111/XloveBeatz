from flask import Blueprint, request, redirect, url_for, flash, jsonify
from helpers.models import Product, BeatLicensePrice, Offer
from helpers.utils import get_current_cart
from helpers.services import add_to_cart, remove_from_cart, clear_cart

bp = Blueprint('cart', __name__)


# ─────────────────────────────────────────────
#  OFFER ENGINE  (auto-applies active offers)
# ─────────────────────────────────────────────

def compute_offer_discounts(enriched_items):
    """
    Apply all active Offers to the cart.
    Returns (discount_cents, offer_summary_list, blocks_coupons).

    enriched_items — list of dicts:
        { 'item': CartItem, 'product': Product, 'subtotal': int (cents) }
    """
    active_offers = Offer.query.filter_by(is_active=True).all()
    total_discount = 0
    offer_summary = []          # [{'label': str, 'saving_cents': int}]
    blocks_coupons = False

    for offer in active_offers:
        apt = offer.applicable_product_type   # 'all'|'beat'|'pack'|'preset'

        # Filter items that qualify for this offer
        qualifying = [
            e for e in enriched_items
            if apt == 'all' or e['product'].product_type == apt
        ]
        if not qualifying:
            continue

        saving = 0

        # ── BOGO: Buy X Get Y Free ──────────────────────────────
        if offer.offer_type == 'bogo':
            buy_qty = offer.buy_quantity or 1
            get_qty = offer.get_quantity or 1
            group   = buy_qty + get_qty

            # Sort qualifying items by unit price ascending (cheapest go free)
            all_units = []
            for e in qualifying:
                for _ in range(e['item'].quantity):
                    all_units.append(e['item'].price_cents_at_time)
            all_units.sort()

            total_units = len(all_units)
            num_groups  = total_units // group
            if num_groups > 0:
                # Cheapest items in each group are free; collect them
                free_prices = []
                for g in range(num_groups):
                    # In each group of `group` items, the cheapest `get_qty` are free.
                    # Our list is sorted ascending: position 0..get_qty-1 in each group are cheapest.
                    start = g * group
                    free_prices += all_units[start: start + get_qty]
                saving = sum(free_prices)
                if saving > 0:
                    offer_summary.append({
                        'label': f"🎁 {offer.name} — {num_groups * get_qty} item(s) FREE",
                        'saving_cents': saving,
                    })

        # ── BULK %: Buy ≥X items, get % off qualifying ─────────
        elif offer.offer_type == 'bulk_percent':
            min_qty = offer.buy_quantity or 2
            pct     = offer.discount_percentage or 0
            total_qualifying_units = sum(e['item'].quantity for e in qualifying)
            if total_qualifying_units >= min_qty and pct > 0:
                subtotal_qualifying = sum(e['subtotal'] for e in qualifying)
                saving = int(subtotal_qualifying * pct / 100)
                if saving > 0:
                    offer_summary.append({
                        'label': f"📦 {offer.name} — {pct}% off ({total_qualifying_units} items)",
                        'saving_cents': saving,
                    })

        # ── SPEND & SAVE: Spend ≥X, get fixed amount off ───────
        elif offer.offer_type == 'spend_amount_off':
            subtotal_qualifying = sum(e['subtotal'] for e in qualifying)
            if (subtotal_qualifying >= offer.min_spend_cents and
                    offer.discount_fixed_cents > 0):
                saving = min(offer.discount_fixed_cents, subtotal_qualifying)
                if saving > 0:
                    offer_summary.append({
                        'label': f"💸 {offer.name} — ₹{saving / 100:.0f} off",
                        'saving_cents': saving,
                    })

        total_discount += saving

        # Track coupon-stacking restriction
        if saving > 0 and not offer.stacks_with_coupons:
            blocks_coupons = True

    return total_discount, offer_summary, blocks_coupons


@bp.route('/cart')
def view_cart():
    # Deprecated: Cart is now handled via UI drawer
    return redirect(url_for('public.home'))


@bp.route('/cart/add', methods=['POST'])
def add():
    product_id = request.form.get('product_id', type=int)
    license_id = request.form.get('license_id', type=int)
    quantity = request.form.get('quantity', 1, type=int)

    if not product_id:
        flash('Invalid product', 'error')
        return redirect(request.referrer or url_for('public.home'))

    product = Product.query.get(product_id)
    if not product:
        flash('Product not found', 'error')
        return redirect(request.referrer or url_for('public.home'))

    price_cents = product.price_cents
    if license_id and product.product_type == 'beat':
        lp = BeatLicensePrice.query.filter_by(beat_id=product_id, license_id=license_id).first()
        if lp and lp.price_cents > 0:
            price_cents = lp.price_cents

    cart_obj = get_current_cart()
    add_to_cart(cart_obj.id, product_id, quantity, license_id, price_cents)

    flash(f'{product.name} added to cart!', 'success')
    return redirect(request.referrer or url_for('cart.view_cart'))


@bp.route('/cart/remove/<int:item_id>')
def remove(item_id):
    remove_from_cart(item_id)
    flash('Item removed', 'info')
    return redirect(url_for('cart.view_cart'))


@bp.route('/cart/clear')
def clear():
    cart_obj = get_current_cart()
    clear_cart(cart_obj.id)
    flash('Cart cleared', 'info')
    return redirect(url_for('cart.view_cart'))


@bp.route('/api/cart/offer-check', methods=['POST'])
def offer_check():
    data = request.get_json() or {}
    items = data.get('items', [])

    if not items:
        return jsonify({'discount_cents': 0, 'blocks_coupons': False, 'offer_summary': []})

    from helpers.models import Offer
    active_offers = Offer.query.filter_by(is_active=True).all()

    total_discount = 0
    blocks_coupons = False
    summaries = []

    for offer in active_offers:
        # Filter items by applicable product type
        if offer.applicable_product_type == 'all':
            eligible = items
        else:
            eligible = [i for i in items if i.get('type') == offer.applicable_product_type]

        if not eligible:
            continue

        if offer.offer_type == 'bogo':
            # BOGO: buy N get M free
            qty = len(eligible)
            group_size = (offer.buy_quantity or 1) + (offer.get_quantity or 1)
            groups = qty // group_size
            if groups > 0:
                # Sort by price, cheapest items are free
                sorted_items = sorted(eligible, key=lambda x: x.get('price', 0))
                free_count = groups * (offer.get_quantity or 1)
                free_items = sorted_items[:free_count]
                discount = sum(f.get('price', 0) for f in free_items)
                total_discount += int(discount * 100)
                summaries.append({
                    'label': offer.name or f'BOGO: Buy {offer.buy_quantity} Get {offer.get_quantity} Free',
                    'saving_cents': int(discount * 100)
                })

        elif offer.offer_type == 'bulk_percent':
            # Bulk discount: buy N items, get X% off
            if len(eligible) >= (offer.buy_quantity or 1):
                subtotal = sum(i.get('price', 0) for i in eligible)
                discount = subtotal * ((offer.discount_percentage or 0) / 100)
                total_discount += int(discount * 100)
                summaries.append({
                    'label': offer.name or f'{offer.discount_percentage}% Off {len(eligible)}+ Items',
                    'saving_cents': int(discount * 100)
                })

        elif offer.offer_type == 'spend_amount_off':
            # Spend threshold: spend ₹X, get ₹Y off
            subtotal = sum(i.get('price', 0) for i in eligible)
            min_spend = (offer.min_spend_cents or 0) / 100
            if subtotal >= min_spend:
                discount_cents = offer.discount_fixed_cents or 0
                total_discount += discount_cents
                summaries.append({
                    'label': offer.name or f'Spend ₹{int(min_spend)}+ Get ₹{int(discount_cents/100)} Off',
                    'saving_cents': discount_cents
                })

        if not offer.stacks_with_coupons and total_discount > 0:
            blocks_coupons = True

    return jsonify({
        'discount_cents': total_discount,
        'blocks_coupons': blocks_coupons,
        'offer_summary': summaries
    })
