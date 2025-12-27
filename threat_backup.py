#!/usr/bin/env python3
"""
Threat Backup for Login Monitor PRO
Automatically backs up important files when security threats are detected.
"""

import json
import os
import shutil
import subprocess
import tarfile
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List

MAX_BACKUP_SIZE_MB = 500  # Maximum backup size


def get_base_dir() -> Path:
    """Get base directory for data files"""
    return Path.home() / ".login-monitor"


def log(message: str):
    """Write timestamped log message"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] [ThreatBackup] {message}"
    print(log_msg, flush=True)

    try:
        log_file = Path("/tmp/loginmonitor-backup.log")
        with open(log_file, "a") as f:
            f.write(log_msg + "\n")
    except:
        pass


class ThreatBackup:
    """Handles automatic and manual backups"""

    # Event types that trigger automatic backup
    TRIGGER_EVENTS = [
        "Intruder",
        "UnknownUSB",
        "GeofenceExit",
        "UnknownFace",
        "Movement"
    ]

    def __init__(self):
        self.base_dir = get_base_dir()
        self.config = self._load_config()
        self.backup_dir = self.base_dir / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def _load_config(self) -> dict:
        """Load configuration from file"""
        config_file = self.base_dir / "config.json"
        if config_file.exists():
            try:
                with open(config_file) as f:
                    return json.load(f)
            except Exception as e:
                log(f"Error loading config: {e}")
        return {}

    def _save_config(self):
        """Save configuration to file"""
        try:
            config_file = self.base_dir / "config.json"
            with open(config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            log(f"Error saving config: {e}")

    def get_backup_paths(self) -> List[Path]:
        """Get list of paths to backup"""
        backup_config = self.config.get("threat_backup", {})
        paths_config = backup_config.get("backup_paths", [
            "~/Documents",
            "~/Desktop"
        ])

        paths = []
        for path_str in paths_config:
            path = Path(path_str).expanduser()
            if path.exists():
                paths.append(path)
            else:
                log(f"Backup path not found: {path}")

        return paths

    def calculate_backup_size(self, paths: List[Path]) -> int:
        """Calculate total size of files to backup in bytes"""
        total_size = 0
        max_size = MAX_BACKUP_SIZE_MB * 1024 * 1024

        for path in paths:
            if path.is_file():
                total_size += path.stat().st_size
            elif path.is_dir():
                for file in path.rglob("*"):
                    if file.is_file():
                        total_size += file.stat().st_size
                        if total_size > max_size:
                            return total_size

        return total_size

    def create_backup(self, trigger_event: str = "Manual", event_id: str = None) -> Optional[Dict]:
        """Create a backup of configured paths"""
        paths = self.get_backup_paths()

        if not paths:
            log("No valid paths to backup")
            return None

        total_size = self.calculate_backup_size(paths)
        max_size = MAX_BACKUP_SIZE_MB * 1024 * 1024

        if total_size > max_size:
            log(f"Backup too large ({total_size / 1024 / 1024:.0f}MB > {MAX_BACKUP_SIZE_MB}MB)")
            log("Backing up most important files only...")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{trigger_event.lower()}_{timestamp}.tar.gz"
        backup_path = self.backup_dir / backup_name

        log(f"Creating backup: {backup_name}")

        try:
            file_count = 0
            actual_size = 0

            with tarfile.open(backup_path, "w:gz") as tar:
                for path in paths:
                    if path.is_file():
                        tar.add(path, arcname=path.name)
                        file_count += 1
                        actual_size += path.stat().st_size
                    elif path.is_dir():
                        for file in path.rglob("*"):
                            if file.is_file():
                                # Skip large files if approaching limit
                                if actual_size + file.stat().st_size > max_size:
                                    continue

                                # Skip hidden/system files
                                if any(part.startswith('.') for part in file.parts):
                                    continue

                                try:
                                    arcname = str(file.relative_to(path.parent))
                                    tar.add(file, arcname=arcname)
                                    file_count += 1
                                    actual_size += file.stat().st_size
                                except Exception as e:
                                    pass  # Skip files we can't access

            log(f"Backup created: {file_count} files, {actual_size / 1024 / 1024:.1f}MB")

            # Upload to Supabase Storage
            storage_url = self._upload_backup(backup_path)

            # Record backup in database
            backup_record = self._record_backup(
                backup_type="threat" if trigger_event != "Manual" else "manual",
                trigger_event_id=event_id,
                file_count=file_count,
                total_size=actual_size,
                storage_url=storage_url
            )

            return {
                "success": True,
                "backup_path": str(backup_path),
                "file_count": file_count,
                "total_size_bytes": actual_size,
                "storage_url": storage_url,
                "trigger_event": trigger_event
            }

        except Exception as e:
            log(f"Error creating backup: {e}")
            return {"success": False, "error": str(e)}

    def _upload_backup(self, backup_path: Path) -> Optional[str]:
        """Upload backup to Supabase Storage"""
        try:
            from supabase_client import SupabaseClient

            config = self._load_config()
            supabase_config = config.get("supabase", {})

            if not supabase_config.get("url") or not supabase_config.get("device_id"):
                return None

            # Check file size (Supabase has a 50MB limit for free tier)
            if backup_path.stat().st_size > 50 * 1024 * 1024:
                log("Backup too large for cloud upload (>50MB)")
                return None

            client = SupabaseClient(
                url=supabase_config["url"],
                anon_key=supabase_config.get("anon_key", ""),
                service_key=supabase_config.get("service_key", supabase_config.get("anon_key", ""))
            )

            # Create backups bucket if it doesn't exist (done via Supabase dashboard)
            # Upload to photos bucket for now (or create a backups bucket)
            url = client.upload_file(
                supabase_config["device_id"],
                str(backup_path),
                "photos"  # Using photos bucket, could create separate backups bucket
            )

            if url:
                log(f"Backup uploaded to cloud")
                return url

        except Exception as e:
            log(f"Error uploading backup: {e}")

        return None

    def _record_backup(self, backup_type: str, trigger_event_id: str = None,
                      file_count: int = 0, total_size: int = 0,
                      storage_url: str = None) -> Optional[Dict]:
        """Record backup in Supabase database"""
        try:
            from supabase_client import SupabaseClient

            config = self._load_config()
            supabase_config = config.get("supabase", {})

            if not supabase_config.get("url") or not supabase_config.get("device_id"):
                return None

            client = SupabaseClient(
                url=supabase_config["url"],
                anon_key=supabase_config.get("anon_key", ""),
                service_key=supabase_config.get("service_key", supabase_config.get("anon_key", ""))
            )

            data = {
                "device_id": supabase_config["device_id"],
                "backup_type": backup_type,
                "file_count": file_count,
                "total_size_bytes": total_size,
                "storage_url": storage_url,
                "status": "completed"
            }

            if trigger_event_id:
                data["trigger_event_id"] = trigger_event_id

            result = client._request(
                "POST",
                "/rest/v1/backups",
                data,
                use_service_key=True
            )

            return result[0] if result else None

        except Exception as e:
            log(f"Error recording backup: {e}")
            return None

    def handle_threat_event(self, event_type: str, event_id: str = None) -> Optional[Dict]:
        """Handle an incoming threat event and trigger backup if configured"""
        backup_config = self.config.get("threat_backup", {})

        if not backup_config.get("enabled", True):
            log("Threat backup is disabled")
            return None

        trigger_events = backup_config.get("trigger_events", self.TRIGGER_EVENTS)

        if event_type not in trigger_events:
            log(f"Event type '{event_type}' not in trigger list")
            return None

        log(f"THREAT DETECTED: {event_type} - Initiating backup...")

        return self.create_backup(trigger_event=event_type, event_id=event_id)

    def list_backups(self) -> List[Dict]:
        """List all local backups"""
        backups = []

        for backup_file in self.backup_dir.glob("backup_*.tar.gz"):
            try:
                stat = backup_file.stat()
                backups.append({
                    "filename": backup_file.name,
                    "size_bytes": stat.st_size,
                    "size_formatted": f"{stat.st_size / 1024 / 1024:.1f}MB",
                    "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat()
                })
            except:
                pass

        return sorted(backups, key=lambda x: x.get("created_at", ""), reverse=True)

    def cleanup_old_backups(self, keep_count: int = 5):
        """Remove old backups, keeping only the most recent ones"""
        backups = sorted(
            self.backup_dir.glob("backup_*.tar.gz"),
            key=lambda x: x.stat().st_ctime,
            reverse=True
        )

        for backup in backups[keep_count:]:
            try:
                backup.unlink()
                log(f"Removed old backup: {backup.name}")
            except Exception as e:
                log(f"Error removing backup: {e}")


def main():
    import sys

    backup = ThreatBackup()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "manual":
            result = backup.create_backup(trigger_event="Manual")
            print(json.dumps(result, indent=2))

        elif command == "list":
            backups = backup.list_backups()
            for b in backups:
                print(f"{b['filename']} - {b['size_formatted']} - {b['created_at']}")

        elif command == "cleanup":
            backup.cleanup_old_backups()
            print("Cleanup complete")

        else:
            print(f"Unknown command: {command}")
            print("Usage: threat_backup.py [manual|list|cleanup]")
    else:
        # Default: create manual backup
        result = backup.create_backup(trigger_event="Manual")
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
