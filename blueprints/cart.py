from flask import Blueprint, render_template, request, redirect, url_for, flash
from helpers.models import Product, BeatLicensePrice
from helpers.utils import get_current_cart
from helpers.services import add_to_cart, remove_from_cart, get_cart_items, clear_cart

bp = Blueprint('cart', __name__)


@bp.route('/cart')
def view_cart():
    cart_obj = get_current_cart()
    items = get_cart_items(cart_obj.id)   # eagerly loaded

    enriched, total_cents = [], 0
    for item in items:
        subtotal = item.price_cents_at_time * item.quantity
        enriched.append({
            'item': item, 'product': item.product,
            'license': item.license, 'subtotal': subtotal,
        })
        total_cents += subtotal

    return render_template('cart.html', items=enriched, total_cents=total_cents)


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