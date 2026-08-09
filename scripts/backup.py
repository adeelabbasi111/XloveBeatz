"""
Automated Database Backup Script for Xlovebeats.
This script copies the SQLite database into a `backups/` folder with a timestamp.
You can set this up to run via a cron job (Linux) or Task Scheduler (Windows).
"""

import os
import sys
import shutil
import datetime

# Setup paths based on the project root
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DB_PATH = os.path.join(PROJECT_ROOT, 'instance', 'app.db')
BACKUP_DIR = os.path.join(PROJECT_ROOT, 'backups')

def backup_database():
    print("Starting automated database backup...")
    
    # 1. Create backups directory if it doesn't exist
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        print(f"Created backup directory at {BACKUP_DIR}")
    
    # 2. Check if DB exists
    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database not found at {DB_PATH}")
        sys.exit(1)
        
    # 3. Create timestamped backup filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(BACKUP_DIR, f"app_backup_{timestamp}.db")
    
    # 4. Copy the file safely
    try:
        shutil.copy2(DB_PATH, backup_file)
        print(f"SUCCESS: Database backed up successfully to {backup_file}")
    except Exception as e:
        print(f"ERROR: Failed to backup database: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    backup_database()
