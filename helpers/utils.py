"""
Pure utility functions: slug generation, price formatting, validation,
file helpers, and auth decorators.
"""
import re
import os
import logging
from functools import wraps

from flask import session, flash, redirect, url_for

logger = logging.getLogger(__name__)

import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

def send_reset_email(to_email, reset_url):
    """Send password reset email using SMTP."""
    smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_user = os.getenv('SMTP_USER', '')
    smtp_pass = os.getenv('SMTP_PASS', '')
    from_name = os.getenv('FROM_NAME', 'XLoveBeats')

    if not smtp_user or not smtp_pass:
        print(f"[DEV MODE] Password reset link for {to_email}: {reset_url}")
        return False

    msg = MIMEMultipart('alternative')
    msg['Subject'] = 'Reset Your XLoveBeats Password'
    msg['From'] = f'{from_name} <{smtp_user}>'
    msg['To'] = to_email

    text_body = f"""
Hi,

You requested a password reset for your XLoveBeats account.

Click the link below to reset your password:
{reset_url}

This link will expire in 1 hour.

If you didn't request this, ignore this email.

— XLoveBeats Team
"""

    html_body = f"""
<div style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto; background: #111; color: #fff; padding: 40px 30px; border-radius: 12px;">
    <h2 style="color: #7c8df0; margin-bottom: 20px;">Reset Your Password</h2>
    <p style="color: #ccc; line-height: 1.6;">You requested a password reset for your XLoveBeats account.</p>
    <a href="{reset_url}" style="display: inline-block; background: linear-gradient(135deg, #7c8df0, #9d7cec); color: #fff; text-decoration: none; padding: 14px 32px; border-radius: 12px; font-weight: 700; margin: 20px 0;">Reset Password</a>
    <p style="color: #888; font-size: 0.85rem;">This link will expire in 1 hour.</p>
    <p style="color: #888; font-size: 0.85rem;">If you didn't request this, ignore this email.</p>
    <hr style="border: 1px solid #333; margin: 24px 0;">
    <p style="color: #555; font-size: 0.75rem;">— XLoveBeats Team</p>
</div>
"""

    msg.attach(MIMEText(text_body, 'plain'))
    msg.attach(MIMEText(html_body, 'html'))

    def send_async():
        try:
            if int(smtp_port) == 465:
                server = smtplib.SMTP_SSL(smtp_host, smtp_port)
            else:
                server = smtplib.SMTP(smtp_host, smtp_port)
                server.starttls()
                
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, to_email, msg.as_string())
            server.quit()
        except Exception as e:
            print(f"Email send failed: {e}")

    thread = threading.Thread(target=send_async)
    thread.daemon = True
    thread.start()
    return True

# =========================
# SLUG GENERATION (single source of truth)
# =========================



def slugify(text):
    """'Indian Beat Pack' -> 'indian-beat-pack'"""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text


def generate_unique_slug(name, model_class):
    """Generate a unique slug, appending -1, -2 etc. if needed."""
    base = slugify(name)
    slug = base
    counter = 1
    while model_class.query.filter_by(slug=slug).first():
        slug = f"{base}-{counter}"
        counter += 1
    return slug


# =========================
# PRICE FORMATTING
# =========================

def cents_to_rupees(cents):
    try:
        from flask import current_app, has_request_context
        if has_request_context():
            from helpers.geo import get_geo_pricing
            geo_info = get_geo_pricing()
            sym = geo_info.get('currency_symbol', '\u20b9')
            if geo_info.get('is_foreign'):
                rate = current_app.config.get('USD_INR_EXCHANGE_RATE', 85.0)
                mult = geo_info.get('multiplier', 1.0)
                usd = ((cents / 100) * mult) / rate
                return f"{sym}{usd:.2f}"
            return f"{sym}{cents / 100:.2f}"
    except Exception:
        pass
    return f"\u20b9{cents / 100:.2f}"

def cents_to_geo_val(cents):
    try:
        from flask import current_app, has_request_context
        if has_request_context():
            from helpers.geo import get_geo_pricing
            geo_info = get_geo_pricing()
            if geo_info.get('is_foreign'):
                rate = current_app.config.get('USD_INR_EXCHANGE_RATE', 85.0)
                mult = geo_info.get('multiplier', 1.0)
                usd = ((cents / 100) * mult) / rate
                return float(f"{usd:.2f}")
    except Exception:
        pass
    return float(f"{cents / 100:.2f}")


def rupees_to_cents(rupees):
    """100.50 -> 10050"""
    return int(round(rupees * 100))


# =========================
# SESSION / AUTH
# =========================

def get_current_user():
    """Retrieve logged-in user from session."""
    from helpers.models import User   # late import to avoid circular dependency
    user_id = session.get('user_id')
    return User.query.get(user_id) if user_id else None


def get_current_cart():
    """Get cart for current user or guest session."""
    import uuid
    from helpers.services import get_or_create_cart

    user = get_current_user()
    if user:
        return get_or_create_cart(user_id=user.id)
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return get_or_create_cart(session_id=session['session_id'])


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not get_current_user():
            flash('Please login first', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user or not user.is_admin:
            flash('Admin access required', 'error')
            return redirect(url_for('public.home'))
        return f(*args, **kwargs)
    return decorated


# =========================
# INPUT VALIDATION
# =========================

def validate_email(email):
    if not email:
        return False
    return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email))


def validate_password(password):
    """Returns (is_valid, error_message)."""
    if not password or len(password) < 6:
        return False, "Password must be at least 6 characters"
    return True, ""


# =========================
# FILE UPLOAD HELPERS
# =========================

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


def save_upload(file_field, prefix, upload_folder):
    """Save file and return filename, or None."""
    from werkzeug.utils import secure_filename
    if file_field and file_field.filename:
        filename = secure_filename(f"{prefix}_{file_field.filename}")
        file_field.save(os.path.join(upload_folder, filename))
        return filename
    return None


# =========================
# TEMPLATE FILTERS
# =========================

def register_template_filters(app):
    @app.template_filter('rupees')
    def rupees_filter(cents):
        return cents_to_rupees(cents)
        
    @app.template_filter('geo_price_val')
    def geo_price_val_filter(cents):
        return cents_to_geo_val(cents)

def send_promo_email(to_email):
    """Send a promotional welcome email containing the latest active discount."""
    import datetime
    from helpers.models import DiscountCode
    
    # Get the latest active discount
    discount = DiscountCode.query.filter(
        (DiscountCode.expires_at == None) | (DiscountCode.expires_at > datetime.datetime.utcnow())
    ).order_by(DiscountCode.created_at.desc()).first()
    
    if discount:
        print(f"Sending latest active discount ({discount.code}) as welcome email to {to_email}")
        send_discount_emails(discount, [to_email])
    else:
        print(f"No active discounts to send to new user: {to_email}")

def send_discount_emails(discount, user_emails):
    """Send an email to a list of users about a new discount."""
    import os
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    import threading

    smtp_host = os.environ.get('SMTP_HOST', '')
    smtp_port = int(os.environ.get('SMTP_PORT', 587))
    smtp_user = os.environ.get('SMTP_USER', '')
    smtp_pass = os.environ.get('SMTP_PASS', '')
    from_name = os.environ.get('SMTP_FROM_NAME', 'XLoveBeats')

    if not all([smtp_host, smtp_user, smtp_pass]):
        print("SMTP not fully configured. Skipping discount emails.")
        return

    # Prepare message details based on discount type
    if discount.discount_type == 'percentage':
        offer_desc = f"{discount.discount_value}% OFF"
    elif discount.discount_type == 'bogo':
        offer_desc = f"Buy {int(discount.min_order_cents / 100)} Get {discount.discount_value} Free"
    else:
        offer_desc = f"₹{discount.discount_value} OFF"

    subject = f"Exclusive Offer: {offer_desc} at XLoveBeats!"
    
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #ff4444; margin-bottom: 5px;">Special Offer Unlocked!</h1>
            <p style="font-size: 1.2em; color: #555;">Grab your favorite beats with this exclusive deal.</p>
        </div>
        
        <div style="background: #1a1a1a; color: white; padding: 30px; border-radius: 12px; text-align: center; margin-bottom: 30px;">
            <h2 style="margin-top: 0; color: #ffaa00; font-size: 1.8em;">{offer_desc}</h2>
            <p style="font-size: 1.1em; margin-bottom: 25px;">Use this code at checkout:</p>
            <div style="background: #333; display: inline-block; padding: 15px 30px; font-size: 28px; font-weight: bold; letter-spacing: 3px; border: 2px dashed #ffaa00; border-radius: 8px; color: #fff;">
                {discount.code}
            </div>
        </div>
        
        <div style="background: #f9f9f9; padding: 20px; border-radius: 8px; margin-bottom: 30px;">
            <h3 style="margin-top: 0; border-bottom: 2px solid #ddd; padding-bottom: 10px;">Offer Details:</h3>
            <ul style="padding-left: 20px;">
                {'<li>Expires on: ' + discount.expires_at.strftime('%B %d, %Y') + '</li>' if discount.expires_at else '<li>Never expires!</li>'}
                {'<li>Minimum Order: ₹' + str(int(discount.min_order_cents / 100)) + '</li>' if discount.min_order_cents > 0 and discount.discount_type != 'bogo' else ''}
                {'<li>Hurry, limited uses available!</li>' if discount.max_uses > 0 else ''}
            </ul>
        </div>
        
        <div style="text-align: center; margin-top: 40px;">
            <a href="https://xlovebeatz.com" style="background: #ff4444; color: white; text-decoration: none; padding: 15px 35px; font-size: 1.2em; font-weight: bold; border-radius: 30px; display: inline-block;">Visit XLoveBeats</a>
        </div>
        
        <p style="text-align: center; margin-top: 50px; font-size: 0.9em; color: #888;">
            Thank you for being a valued part of the XLoveBeats community!<br>
            If you have any questions, feel free to reply to this email.
        </p>
    </body>
    </html>
    """

    text_body = f"""Special Offer Unlocked!
Grab your favorite beats with this exclusive deal: {offer_desc}

Use this code at checkout: {discount.code}

Offer Details:
- {'Expires on: ' + discount.expires_at.strftime('%B %d, %Y') if discount.expires_at else 'Never expires!'}
- {'Minimum Order: ₹' + str(int(discount.min_order_cents / 100)) if discount.min_order_cents > 0 and discount.discount_type != 'bogo' else ''}

Visit https://xlovebeatz.com to claim your offer!

Thank you for being part of XLoveBeats!
"""

    def send_async():
        try:
            if smtp_port == 465:
                server = smtplib.SMTP_SSL(smtp_host, smtp_port)
            else:
                server = smtplib.SMTP(smtp_host, smtp_port)
                server.starttls()
            server.login(smtp_user, smtp_pass)
            
            # Send individual emails to avoid exposing all emails in BCC and avoid spam flags
            for to_email in user_emails:
                try:
                    msg = MIMEMultipart('alternative')
                    msg['Subject'] = subject
                    msg['From'] = f'{from_name} <{smtp_user}>'
                    msg['To'] = to_email
                    msg.attach(MIMEText(text_body, 'plain'))
                    msg.attach(MIMEText(html_body, 'html'))
                    server.sendmail(smtp_user, to_email, msg.as_string())
                except Exception as e:
                    print(f"Failed to send to {to_email}: {e}")
                    
            server.quit()
            print(f"Sent discount email to {len(user_emails)} users.")
        except Exception as e:
            print(f"Failed to send bulk discount emails: {e}")

    thread = threading.Thread(target=send_async)
    thread.daemon = True
    thread.start()