import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app
from helpers.models import db, Product, BeatDetail, BeatLicensePrice, License
from blueprints.admin import convert_wav_to_full_preview
from helpers.utils import generate_unique_slug
import csv
import re
import shutil
from difflib import SequenceMatcher

def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()

app = create_app()

def main():
    with app.app_context():
        csv_path = 'New Beats/FL links.csv'
        csv_links = {}
        with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.reader(f)
            try:
                next(reader)
            except StopIteration:
                pass
            for row in reader:
                if len(row) >= 2:
                    name = row[0].replace('.rar', '').replace(' - Copy', '').strip()
                    link = row[1]
                    m = re.search(r'\[Link\]\((.*?)\)', link)
                    if m:
                        link = m.group(1)
                    csv_links[name.lower()] = link
                    
        beats_dir = 'New Beats'
        dest_wav_dir = 'static/data/wav'
        os.makedirs(dest_wav_dir, exist_ok=True)
        
        basic_lic = License.query.filter_by(name='Basic').first()
        premium_lic = License.query.filter_by(name='Premium').first()
        
        stats = {'added': 0, 'skipped': 0, 'details': []}
        
        for file in os.listdir(beats_dir):
            if file.lower().endswith(('.wav', '.mp3')):
                filepath = os.path.join(beats_dir, file)
                base_name = os.path.splitext(file)[0]
                ext = os.path.splitext(file)[1].lower()
                
                bpm = None
                bpm_match = re.search(r'\b(\d{2,3})\b', base_name)
                if bpm_match:
                    bpm = int(bpm_match.group(1))
                    
                key_match = re.search(r'\b([A-G][#b]?\s*(?:MINOR|MAJ|minor|major|maj|min))\b', base_name, re.IGNORECASE)
                key = key_match.group(1).upper() if key_match else ''
                
                clean_name = base_name
                if key:
                    clean_name = re.sub(re.escape(key_match.group(1)), '', clean_name, flags=re.IGNORECASE)
                if bpm:
                    clean_name = re.sub(r'\b' + str(bpm) + r'\b', '', clean_name)
                    
                clean_name = re.sub(r'(?i)\bBEAT\b', '', clean_name)
                clean_name = re.sub(r'(?i)\bTYPE\b', '', clean_name)
                
                genre = ''
                common_genres = ['DRILL', 'TRAP', 'OLD SKOOL', 'OLD', 'LOFI', 'AFRO', 'CHILL', 'SAD', 'INDIAN']
                for g in common_genres:
                    if clean_name.upper().startswith(g):
                        genre = g
                        break
                        
                clean_name = clean_name.strip(' _-')
                clean_name = re.sub(r'\s+', ' ', clean_name).strip()
                if not clean_name:
                    clean_name = base_name.strip()
                    
                if Product.query.filter_by(name=clean_name).first():
                    stats['skipped'] += 1
                    stats['details'].append(f"Skipped (already exists): {clean_name}")
                    continue
                    
                best_match = None
                best_score = 0
                for csv_name in csv_links:
                    score = similar(clean_name.lower(), csv_name)
                    if csv_name in clean_name.lower() or clean_name.lower() in csv_name:
                        score = max(score, 0.8)
                    if score > best_score:
                        best_score = score
                        best_match = csv_name
                
                project_link = ''
                has_stems = False
                if best_score > 0.6 and best_match:
                    project_link = csv_links[best_match]
                    has_stems = True
                    
                slug = generate_unique_slug(clean_name, Product)
                dest_filename = f"{slug}_beat{ext}"
                dest_path = os.path.join(dest_wav_dir, dest_filename)
                shutil.move(filepath, dest_path)
                
                wav_db_path = f"data/wav/{dest_filename}"
                preview_db_path = wav_db_path
                
                if ext == '.wav':
                    abs_wav = os.path.abspath(dest_path)
                    try:
                        p_path = convert_wav_to_full_preview(abs_wav, slug)
                        if p_path:
                            preview_db_path = p_path
                    except Exception as e:
                        print(f"Preview gen failed for {clean_name}: {e}")
                
                prod = Product(
                    product_type='beat',
                    name=clean_name,
                    slug=slug,
                    description='',
                    price_cents=49900,
                    is_active=True,
                    sort_order=0
                )
                db.session.add(prod)
                db.session.flush()
                
                beat_det = BeatDetail(
                    product_id=prod.id,
                    bpm=bpm,
                    musical_key=key.strip(),
                    genre=genre.strip(),
                    genre_sort_order=0,
                    preview_audio=preview_db_path,
                    wav_file=wav_db_path,
                    project_file=project_link,
                    has_stems=has_stems
                )
                db.session.add(beat_det)
                db.session.flush()
                
                lic_basic = BeatLicensePrice(
                    beat_id=prod.id,
                    license_id=basic_lic.id,
                    price_cents=49900,
                    included_files='MP3, WAV',
                    tags='Standard'
                )
                db.session.add(lic_basic)
                
                if has_stems:
                    lic_prem = BeatLicensePrice(
                        beat_id=prod.id,
                        license_id=premium_lic.id,
                        price_cents=149900,
                        included_files='MP3, WAV, STEMS/PROJECT',
                        tags='Premium'
                    )
                    db.session.add(lic_prem)
                    
                db.session.commit()
                stats['added'] += 1
                stats['details'].append(f"Added: {clean_name} | Genre: {genre} | Key: {key} | BPM: {bpm} | Premium/Stems: {has_stems} | CSV Match: {best_match} ({best_score:.2f})")
                
                print(stats['details'][-1])

        with open('bulk_upload_report.txt', 'w', encoding='utf-8') as f:
            f.write(f"Added: {stats['added']}, Skipped: {stats['skipped']}\n\n")
            for d in stats['details']:
                f.write(d + "\n")
                
if __name__ == '__main__':
    main()
