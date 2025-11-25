# FILE: backend/scripts/backup_manager.py
# Trigger script for manual or scheduled backups.

import sys
import os

# Add parent dir to path so we can import app
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.services.backup_service import backup_service

if __name__ == "__main__":
    print("--- JURISTI AI BLACK BOX RECORDER ---")
    try:
        filename = backup_service.perform_full_backup()
        print(f"🎉 Backup Success! File secured: {filename}")
    except Exception as e:
        print(f"❌ Backup Failed: {e}")
        sys.exit(1)