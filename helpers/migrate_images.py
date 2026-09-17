"""
Database Image Extension Migration Tool
Scans all Genre, Product, and BeatDetail records in the database.
If the recorded image path does not exist on disk, it checks for alternative
extensions (.webp, .jpg, .jpeg, .png, .jfif) and updates the database record.
"""
import os
import logging

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = ['.webp', '.jpg', '.jpeg', '.png', '.jfif']

def migrate_db_image_paths(app=None):
    from flask import current_app
    from helpers.models import db, Genre, Product, BeatDetail

    target_app = app or current_app
    static_dir = os.path.join(target_app.root_path, 'static')
    updates_count = 0

    def resolve_path(rel_path):
        if not rel_path:
            return None
        abs_path = os.path.join(static_dir, rel_path)
        if os.path.exists(abs_path):
            return rel_path  # Already exists as-is
        
        base_no_ext, _ = os.path.splitext(rel_path)
        for ext in SUPPORTED_EXTENSIONS:
            candidate_rel = base_no_ext + ext
            if os.path.exists(os.path.join(static_dir, candidate_rel)):
                return candidate_rel
        return None

    # 1. Genres
    for g in Genre.query.all():
        if g.image_path:
            resolved = resolve_path(g.image_path)
            if resolved and resolved != g.image_path:
                logger.info("Migrated Genre '%s' image: %s -> %s", g.name, g.image_path, resolved)
                g.image_path = resolved
                updates_count += 1

    # 2. Products
    for p in Product.query.all():
        if p.cover_image:
            resolved = resolve_path(p.cover_image)
            if resolved and resolved != p.cover_image:
                logger.info("Migrated Product '%s' cover: %s -> %s", p.name, p.cover_image, resolved)
                p.cover_image = resolved
                updates_count += 1

    # 3. Beat Details
    for b in BeatDetail.query.all():
        if b.beat_image:
            resolved = resolve_path(b.beat_image)
            if resolved and resolved != b.beat_image:
                logger.info("Migrated BeatDetail %s image: %s -> %s", b.id, b.beat_image, resolved)
                b.beat_image = resolved
                updates_count += 1

    if updates_count > 0:
        db.session.commit()
        logger.info("Successfully updated %d image path(s) in database to match disk files.", updates_count)
    else:
        logger.info("All database image paths are up-to-date with files on disk.")

    return updates_count


if __name__ == '__main__':
    from app import create_app
    app = create_app()
    with app.app_context():
        count = migrate_db_image_paths(app)
        print(f"Migration finished. Updated {count} record(s).")
