#!/usr/bin/env python3
"""
Cloud Backup for Login Monitor PRO
====================================

Automatically backup captured images to Google Drive.
Also supports local backup to external drives.
"""

import os
import sys
import json
import shutil
import hashlib
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "config.json"
IMAGES_DIR = SCRIPT_DIR / "captured_images"
EVENTS_DIR = SCRIPT_DIR / "events"
BACKUP_LOG = SCRIPT_DIR / "backup_log.json"

# Try to import Google Drive API
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    HAS_GOOGLE_API = True
except ImportError:
    HAS_GOOGLE_API = False


def log(message):
    """Log message"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")


def load_backup_log():
    """Load backup log to track uploaded files"""
    if BACKUP_LOG.exists():
        with open(BACKUP_LOG, 'r') as f:
            return json.load(f)
    return {"uploaded_files": [], "last_backup": None}


def save_backup_log(log_data):
    """Save backup log"""
    with open(BACKUP_LOG, 'w') as f:
        json.dump(log_data, f, indent=2)


def get_file_hash(filepath):
    """Get MD5 hash of file"""
    md5 = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            md5.update(chunk)
    return md5.hexdigest()


class GoogleDriveBackup:
    """Backup to Google Drive"""

    SCOPES = ['https://www.googleapis.com/auth/drive.file']

    def __init__(self):
        self.creds = None
        self.service = None
        self.folder_id = None

    def authenticate(self):
        """Authenticate with Google Drive"""
        if not HAS_GOOGLE_API:
            log("Google Drive API not installed")
            log("Run: pip3 install google-auth google-auth-oauthlib google-api-python-client")
            return False

        token_file = SCRIPT_DIR / 'gdrive_token.json'
        credentials_file = SCRIPT_DIR / 'gdrive_credentials.json'

        if token_file.exists():
            self.creds = Credentials.from_authorized_user_file(str(token_file), self.SCOPES)

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                if not credentials_file.exists():
                    log("Missing gdrive_credentials.json")
                    log("Download from Google Cloud Console")
                    return False

                flow = InstalledAppFlow.from_client_secrets_file(
                    str(credentials_file), self.SCOPES)
                self.creds = flow.run_local_server(port=0)

            with open(token_file, 'w') as f:
                f.write(self.creds.to_json())

        self.service = build('drive', 'v3', credentials=self.creds)
        return True

    def get_or_create_folder(self, folder_name="LoginMonitor_Backup"):
        """Get or create backup folder in Drive"""
        # Search for existing folder
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = self.service.files().list(q=query, fields="files(id, name)").execute()
        folders = results.get('files', [])

        if folders:
            self.folder_id = folders[0]['id']
            log(f"Using existing folder: {folder_name}")
        else:
            # Create folder
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = self.service.files().create(body=folder_metadata, fields='id').execute()
            self.folder_id = folder.get('id')
            log(f"Created folder: {folder_name}")

        return self.folder_id

    def upload_file(self, filepath, custom_name=None):
        """Upload file to Google Drive"""
        if not self.service or not self.folder_id:
            return None

        filename = custom_name or os.path.basename(filepath)

        file_metadata = {
            'name': filename,
            'parents': [self.folder_id]
        }

        # Determine MIME type
        ext = os.path.splitext(filepath)[1].lower()
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.wav': 'audio/wav',
            '.json': 'application/json'
        }
        mime_type = mime_types.get(ext, 'application/octet-stream')

        media = MediaFileUpload(filepath, mimetype=mime_type, resumable=True)

        try:
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()

            log(f"Uploaded: {filename}")
            return file.get('webViewLink')

        except Exception as e:
            log(f"Upload failed: {e}")
            return None

    def backup_images(self):
        """Backup all images not yet uploaded"""
        backup_log = load_backup_log()
        uploaded = set(backup_log.get('uploaded_files', []))

        if not IMAGES_DIR.exists():
            log("No images directory found")
            return

        new_uploads = 0
        for image_file in IMAGES_DIR.glob("*.jpg"):
            file_hash = get_file_hash(image_file)

            if file_hash not in uploaded:
                link = self.upload_file(str(image_file))
                if link:
                    uploaded.add(file_hash)
                    new_uploads += 1

        backup_log['uploaded_files'] = list(uploaded)
        backup_log['last_backup'] = datetime.now().isoformat()
        save_backup_log(backup_log)

        log(f"Backup complete: {new_uploads} new files uploaded")


class LocalBackup:
    """Backup to local/external drive"""

    def __init__(self, backup_path):
        self.backup_path = Path(backup_path)

    def backup(self):
        """Perform local backup"""
        if not self.backup_path.exists():
            try:
                self.backup_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                log(f"Cannot create backup directory: {e}")
                return False

        # Create dated subfolder
        date_folder = self.backup_path / datetime.now().strftime('%Y-%m-%d')
        date_folder.mkdir(exist_ok=True)

        copied = 0

        # Copy images
        if IMAGES_DIR.exists():
            for image_file in IMAGES_DIR.glob("*.jpg"):
                dest = date_folder / image_file.name
                if not dest.exists():
                    shutil.copy2(image_file, dest)
                    copied += 1

        # Copy events
        if EVENTS_DIR.exists():
            events_backup = date_folder / "events"
            events_backup.mkdir(exist_ok=True)

            for event_file in EVENTS_DIR.glob("*.json"):
                dest = events_backup / event_file.name
                if not dest.exists():
                    shutil.copy2(event_file, dest)
                    copied += 1

        log(f"Local backup complete: {copied} files copied to {date_folder}")
        return True


def setup_google_drive():
    """Interactive setup for Google Drive"""
    print("""
╔═══════════════════════════════════════════════════════════════╗
║           GOOGLE DRIVE BACKUP SETUP                           ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  1. Go to Google Cloud Console:                               ║
║     https://console.cloud.google.com/                         ║
║                                                               ║
║  2. Create a new project                                      ║
║                                                               ║
║  3. Enable Google Drive API:                                  ║
║     APIs & Services > Enable APIs > Google Drive API          ║
║                                                               ║
║  4. Create OAuth credentials:                                 ║
║     APIs & Services > Credentials > Create Credentials        ║
║     > OAuth client ID > Desktop app                           ║
║                                                               ║
║  5. Download the JSON file and save as:                       ║
║     {credentials_file}
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
""".format(credentials_file=SCRIPT_DIR / 'gdrive_credentials.json'))

    credentials_file = SCRIPT_DIR / 'gdrive_credentials.json'

    if credentials_file.exists():
        print("✓ Credentials file found!")

        backup = GoogleDriveBackup()
        if backup.authenticate():
            print("✓ Authentication successful!")
            backup.get_or_create_folder()
            print("\nGoogle Drive backup is ready!")
            return True
    else:
        print("✗ Credentials file not found")
        print(f"  Please download and save to: {credentials_file}")

    return False


def main():
    print("="*60)
    print("LOGIN MONITOR PRO - Cloud Backup")
    print("="*60)

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "--setup":
            setup_google_drive()

        elif command == "--google":
            backup = GoogleDriveBackup()
            if backup.authenticate():
                backup.get_or_create_folder()
                backup.backup_images()

        elif command == "--local":
            if len(sys.argv) > 2:
                path = sys.argv[2]
            else:
                path = input("Backup path: ").strip()

            local = LocalBackup(path)
            local.backup()

        elif command == "--help":
            print("""
Usage:
  python3 cloud_backup.py --setup       Setup Google Drive
  python3 cloud_backup.py --google      Backup to Google Drive
  python3 cloud_backup.py --local PATH  Backup to local path
  python3 cloud_backup.py --help        Show this help
""")

    else:
        print("\nBackup options:")
        print("  1. Google Drive")
        print("  2. Local/External Drive")

        choice = input("\nSelect (1/2): ").strip()

        if choice == "1":
            backup = GoogleDriveBackup()
            if backup.authenticate():
                backup.get_or_create_folder()
                backup.backup_images()
            else:
                print("\nRun with --setup first to configure Google Drive")

        elif choice == "2":
            path = input("Backup path: ").strip()
            local = LocalBackup(path)
            local.backup()


if __name__ == "__main__":
    main()
