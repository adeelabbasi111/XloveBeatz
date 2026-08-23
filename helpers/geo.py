"""
Geo-location helper for detecting foreign users and applying geo-pricing.
Uses MaxMind GeoLite2-Country database for IP-based country detection.
"""

import os
import geoip2.database
import geoip2.errors
from flask import session, request as flask_request
from helpers.services import get_site_setting

# Path to the GeoLite2-Country database
GEOIP_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'GeoLite2-Country.mmdb')

# Singleton reader (loaded once, reused across requests)
_reader = None


def _get_reader():
    """Lazy-load the GeoIP2 reader singleton."""
    global _reader
    if _reader is None:
        if os.path.exists(GEOIP_DB_PATH):
            try:
                _reader = geoip2.database.Reader(GEOIP_DB_PATH)
            except Exception as e:
                print(f"[GeoIP] Failed to load database: {e}")
                return None
        else:
            print(f"[GeoIP] Database not found at {GEOIP_DB_PATH}")
            return None
    return _reader


def _get_client_ip():
    """Extract the real client IP, respecting proxy headers."""
    # Check Cloudflare IP first if the site uses it
    cf_ip = flask_request.headers.get('CF-Connecting-IP', '')
    if cf_ip:
        return cf_ip.strip()

    # Check common proxy headers
    forwarded_for = flask_request.headers.get('X-Forwarded-For', '')
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs; the first is the client
        return forwarded_for.split(',')[0].strip()

    real_ip = flask_request.headers.get('X-Real-IP', '')
    if real_ip:
        return real_ip.strip()

    return flask_request.remote_addr or '127.0.0.1'


def detect_country(req=None):
    """
    Detect the user's country code (ISO 3166-1 alpha-2, e.g. 'IN', 'US').
    Returns 'IN' as default if detection fails.
    """
    # Allow testing via URL parameter (e.g. ?force_country=US)
    force_country = flask_request.args.get('force_country')
    if force_country:
        return force_country.upper()

    # If Cloudflare IP Geolocation is enabled
    cf_country = flask_request.headers.get('CF-IPCountry')
    if cf_country and cf_country != 'XX':
        return cf_country.upper()

    reader = _get_reader()
    if not reader:
        return 'IN'  # Default to India if DB not available

    ip = _get_client_ip()

    # Skip localhost / private IPs
    if ip in ('127.0.0.1', '::1', 'localhost') or ip.startswith('192.168.') or ip.startswith('10.'):
        return 'IN'

    try:
        response = reader.country(ip)
        country = response.country.iso_code or 'IN'
    except (geoip2.errors.AddressNotFoundError, ValueError):
        country = 'IN'
    except Exception as e:
        print(f"[GeoIP] Lookup failed for {ip}: {e}")
        country = 'IN'

    return country


def is_foreign_user(req=None):
    """Returns True if the user is detected as being outside India."""
    return detect_country(req) != 'IN'


def get_geo_pricing():
    """
    Returns geo-pricing configuration dict based on user's location and admin settings.

    Returns:
        {
            'is_foreign': bool,
            'multiplier': float,
            'currency_symbol': str ('$' or '₹'),
            'currency_code': str ('USD' or 'INR'),
            'geo_pricing_enabled': bool
        }
    """
    enabled = get_site_setting('geo_pricing_enabled', 'false').lower() == 'true'
    multiplier = 1.0
    try:
        multiplier = float(get_site_setting('geo_pricing_multiplier', '3'))
    except (ValueError, TypeError):
        multiplier = 3.0

    if not enabled:
        return {
            'is_foreign': False,
            'multiplier': 1.0,
            'currency_symbol': '₹',
            'currency_code': 'INR',
            'geo_pricing_enabled': False
        }

    foreign = is_foreign_user()

    if foreign:
        return {
            'is_foreign': True,
            'multiplier': multiplier,
            'currency_symbol': '$',
            'currency_code': 'USD',
            'geo_pricing_enabled': True
        }
    else:
        return {
            'is_foreign': False,
            'multiplier': 1.0,
            'currency_symbol': '₹',
            'currency_code': 'INR',
            'geo_pricing_enabled': True
        }


def apply_geo_pricing_to_beats(beats_data, geo_info):
    """
    Transform beat prices in-place if user is foreign.
    Multiplies INR price by multiplier, then converts to USD using exchange rate.

    Args:
        beats_data: list of beat dicts from build_beats_data()
        geo_info: dict from get_geo_pricing()
    """
    if not geo_info['is_foreign']:
        return beats_data

    from flask import current_app
    exchange_rate = current_app.config.get('USD_INR_EXCHANGE_RATE', 85.0)
    multiplier = geo_info['multiplier']

    for beat in beats_data:
        # Transform base price: (INR_price * multiplier) / exchange_rate = USD
        if beat.get('price'):
            inr_price = float(beat['price'])
            beat['price'] = round((inr_price * multiplier) / exchange_rate, 2)

        # Transform license tier prices
        if beat.get('license_tiers'):
            for tier_name, tier_data in beat['license_tiers'].items():
                if tier_data.get('price') and tier_data['price'] not in ('', '0', '0.0', 'Negotiable', 'negotiable'):
                    try:
                        inr_price = float(tier_data['price'])
                        tier_data['price'] = round((inr_price * multiplier) / exchange_rate, 2)
                    except (ValueError, TypeError):
                        pass  # Keep original if not a number (e.g. 'Negotiable')

    return beats_data
