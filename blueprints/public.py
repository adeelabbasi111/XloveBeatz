from flask import Blueprint, render_template, flash, redirect, url_for, current_app
from helpers.models import Product, Genre
from helpers.services import get_homepage_products, get_player_beats, build_beats_data, get_beat_with_details

bp = Blueprint('public', __name__)


@bp.route('/')
def home():
    # We still fetch these so we can show counts or featured items if needed
    limit = current_app.config['HOMEPAGE_BEAT_LIMIT']
    beat_packs, beats, vocal_presets = get_homepage_products(limit)
    genres = Genre.query.filter_by(is_active=True).order_by(Genre.sort_order).all()
    return render_template(
        'index.html',
        beat_packs=beat_packs, beats=beats, vocal_presets=vocal_presets,
        genres=genres,
        site_title="XLOVEBEATZ",
        slogan="Crafted for artists who move the world",
    )

@bp.route('/beat-packs')
def beat_packs_page():
    beat_packs = Product.query.filter_by(product_type='pack', is_active=True).all()
    return render_template('beat_packs.html', beat_packs=beat_packs, site_title="XLOVEBEATZ")

@bp.route('/vocal-presets')
def vocal_presets_page():
    vocal_presets = Product.query.filter_by(product_type='preset', is_active=True).all()
    return render_template('vocal_presets.html', vocal_presets=vocal_presets, site_title="XLOVEBEATZ")

@bp.route('/about')
def about_page():
    return render_template('about.html', site_title="XLOVEBEATZ")

@bp.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    if product.product_type == 'beat':
        return redirect(url_for('public.player_page'))
    return render_template('product_detail.html', product=product, site_title="XLOVEBEATZ")

@bp.route('/player')
@bp.route('/player/pack/<int:pack_id>')
def player_page(pack_id=None):
    beats, pack_info, error = get_player_beats(pack_id)
    if error:
        flash(error, 'error')
        return redirect(url_for('public.home'))

    page_title = f"Playing: {pack_info.product.name}" if pack_info else "All Beats & Singles"
    beats_data = build_beats_data(beats)   # batch: 2 queries total

    return render_template(
        'player.html', beats=beats_data, pack_info=pack_info,
        site_title="XLOVEBEATZ", page_title=page_title,
    )


@bp.route('/beat/<slug>')
def beat_detail_page(slug):
    product = Product.query.filter_by(slug=slug, product_type='beat').first()
    if not product:
        flash('Beat not found', 'error')
        return redirect(url_for('public.home'))
    data = get_beat_with_details(product.id)
    return render_template('beat_detail.html', **data)

@bp.route('/presets/<int:preset_id>')
def preset_detail(preset_id):
    preset = Product.query.get_or_404(preset_id)
    return render_template('preset_detail.html', preset=preset)