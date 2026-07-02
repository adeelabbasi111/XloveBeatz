"""
License Generation Service
Wraps BeatLicenseGenerator, integrates with database models,
saves PDFs to data/licenses/
"""
import os
import sys
from datetime import datetime

# Add project root to path so we can import beat_license_generator
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from helpers.beat_license_generator import BeatLicenseGenerator
from helpers.models import db, GeneratedLicense, OrderItem

# PDF output directory
LICENSE_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'licenses')


def generate_license_for_order_item(order_item: OrderItem) -> GeneratedLicense | None:
    """
    Generate a license PDF for a single order item and store it in the database.

    Args:
        order_item: An OrderItem instance (must have .order, .product, .license populated)

    Returns:
        GeneratedLicense instance if successful, None if skipped (e.g. Exclusive tier)
    """
    # Get the license tier name
    license_tier = order_item.license
    if not license_tier:
        return None

    tier_name = license_tier.name.lower()

    # Only Basic and Premium have auto-generated PDFs
    # Exclusive licenses are negotiated separately (handled manually)
    if tier_name not in ('basic', 'premium'):
        return None

    # Gather data for the generator
    order = order_item.order
    product = order_item.product

    # Determine buyer name: prefer user username, fallback to order email
    if order.user:
        buyer_name = order.user.username
    else:
        buyer_name = order.email.split('@')[0] if order.email else 'Customer'

    # Get beat price from the order item
    beat_price = str(order_item.price_paid_cents // 100)  # Convert cents to INR integer string

    # Build the license_data dict the generator expects
    license_data = {
        'licensee_legal_name': buyer_name,
        'artist_stage_name': '',  # Could be extended to collect from user profile
        'beat_name': product.name,
        'effective_date': datetime.utcnow().strftime('%d-%m-%Y'),
        'beat_price': beat_price,
    }

    # Generate PDF
    generator = BeatLicenseGenerator()

    if tier_name == 'basic':
        story = generator.generate_basic_license(license_data)
    else:  # premium
        story = generator.generate_premium_license(license_data)

    # Build filename: LicenseId_BuyerName_BeatName_Tier.pdf
    safe_buyer = buyer_name.replace(' ', '_').replace('/', '_')
    safe_beat = product.name.replace(' ', '_').replace('/', '_')
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    filename = f"{safe_buyer}_{safe_beat}_{tier_name.capitalize()}_{timestamp}"

    # Save PDF to data/licenses/
    pdf_full_path = generator.save_license(story, filename, LICENSE_OUTPUT_DIR)

    # The path to store in the database (relative to static/uploads or as a path)
    # Store relative path from project root
    pdf_relative_path = os.path.relpath(pdf_full_path, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # Create or update GeneratedLicense record in database
    existing = GeneratedLicense.query.filter_by(order_item_id=order_item.id).first()
    if existing:
        # Update existing record
        existing.buyer_name = buyer_name
        existing.beat_name = product.name
        existing.license_type = license_tier.name
        existing.pdf_path = pdf_relative_path
        existing.generated_at = datetime.utcnow()
        gen_license = existing
    else:
        gen_license = GeneratedLicense(
            order_item_id=order_item.id,
            buyer_name=buyer_name,
            beat_name=product.name,
            license_type=license_tier.name,
            pdf_path=pdf_relative_path,
            generated_at=datetime.utcnow(),
        )
        db.session.add(gen_license)

    db.session.commit()
    return gen_license


def generate_licenses_for_order(order) -> list:
    """
    Generate license PDFs for ALL items in an order.

    Args:
        order: An Order instance with .items populated

    Returns:
        List of GeneratedLicense instances that were created
    """
    generated = []

    for item in order.items:
        try:
            gen_license = generate_license_for_order_item(item)
            if gen_license:
                generated.append(gen_license)
        except Exception as e:
            # Log error but don't crash the payment flow
            print(f"[License Generator] Error generating license for OrderItem {item.id}: {e}")
            import traceback
            traceback.print_exc()

    return generated