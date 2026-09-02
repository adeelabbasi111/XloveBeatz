from app import create_app, db
from helpers.models import BeatDetail, BeatPack, Genre

def run():
    app = create_app()
    with app.app_context():
        # 1. Normalize BeatDetail genres
        for bd in BeatDetail.query.filter(BeatDetail.genre != None).all():
            if bd.genre:
                bd.genre = bd.genre.title()
        
        # 2. Normalize BeatPack genres
        for bp in BeatPack.query.filter(BeatPack.genre != None).all():
            if bp.genre:
                bp.genre = bp.genre.title()
                
        # 3. Clean up Genres table to remove duplicates
        genres = Genre.query.all()
        for g in genres:
            title_name = g.name.title()
            if g.name != title_name:
                existing = Genre.query.filter_by(name=title_name).first()
                if existing:
                    db.session.delete(g)
                else:
                    g.name = title_name
                    
        db.session.commit()
        print("Database genres successfully normalized to Title Case!")

if __name__ == '__main__':
    run()
