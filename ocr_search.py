#!/usr/bin/env python3
"""
CyVigil OCR Screen Search
==========================
Extracts text from screenshots using OCR for searchable audit trail.
Detects sensitive data in screen content.
"""

import os
import sys
import json
import time
import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

# Try to import Vision framework for OCR
try:
    import Quartz
    from Foundation import NSURL
    import Vision
    HAS_VISION = True
except ImportError:
    HAS_VISION = False
    print("Warning: Vision framework not available.")

# Try PIL for image handling
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("Warning: PIL not installed. Install with: pip3 install Pillow")

# Configuration
CONFIG_PATH = Path.home() / ".login-monitor" / "config.json"
LOG_PATH = "/tmp/loginmonitor-ocr.log"
SCREENSHOTS_DIR = Path.home() / ".login-monitor" / "captured_images"

# Sensitive patterns to detect in OCR text
SENSITIVE_PATTERNS = {
    'credit_card': (r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b', 'critical'),
    'ssn': (r'\b\d{3}-\d{2}-\d{4}\b', 'critical'),
    'api_key': (r'\b(?:api[_-]?key|apikey)["\'\s:=]+["\']?([a-zA-Z0-9_\-]{20,})', 'high'),
    'password': (r'\b(?:password|passwd)["\'\s:=]+["\']?([^\s"\']{6,})', 'high'),
    'aws_key': (r'\bAKIA[0-9A-Z]{16}\b', 'critical'),
    'private_key': (r'-----BEGIN.*PRIVATE KEY-----', 'critical'),
}


def log(message: str):
    """Log message with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}"
    print(log_line)
    try:
        with open(LOG_PATH, 'a') as f:
            f.write(log_line + '\n')
    except Exception:
        pass


class OCRProcessor:
    """Processes screenshots with OCR."""

    def __init__(self):
        self.config = self._load_config()
        self.device_id = self.config.get("device_id", "")
        self.supabase_url = self.config.get("supabase_url", "")
        self.supabase_key = self.config.get("supabase_key", "")

        # OCR settings
        dlp_config = self.config.get("dlp", {})
        self.enabled = dlp_config.get("ocr_enabled", True)
        self.detect_sensitive = dlp_config.get("ocr_detect_sensitive", True)
        self.store_text = dlp_config.get("ocr_store_text", True)

        # Track processed files
        self.processed_files: set = set()

        log(f"OCR Processor initialized. Device: {self.device_id[:8] if self.device_id else 'unknown'}...")

    def _load_config(self) -> dict:
        """Load configuration from file."""
        try:
            if CONFIG_PATH.exists():
                with open(CONFIG_PATH) as f:
                    return json.load(f)
        except Exception as e:
            log(f"Error loading config: {e}")
        return {}

    def _send_to_supabase(self, table: str, data: dict) -> bool:
        """Send data to Supabase."""
        if not self.supabase_url or not self.supabase_key:
            return False

        try:
            response = requests.post(
                f"{self.supabase_url}/rest/v1/{table}",
                headers={
                    "apikey": self.supabase_key,
                    "Authorization": f"Bearer {self.supabase_key}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal"
                },
                json=data,
                timeout=10
            )
            return response.status_code in (200, 201)
        except Exception as e:
            log(f"Supabase error: {e}")
            return False

    def _create_security_alert(self, alert_type: str, severity: str,
                                title: str, description: str):
        """Create a security alert."""
        alert_data = {
            "device_id": self.device_id,
            "alert_type": alert_type,
            "severity": severity,
            "title": title,
            "description": description
        }
        self._send_to_supabase("security_alerts", alert_data)
        log(f"ALERT [{severity.upper()}]: {title}")

    def extract_text_vision(self, image_path: str) -> str:
        """Extract text using macOS Vision framework."""
        if not HAS_VISION:
            return ""

        try:
            # Create image request handler
            image_url = NSURL.fileURLWithPath_(image_path)
            handler = Vision.VNImageRequestHandler.alloc().initWithURL_options_(image_url, None)

            # Create text recognition request
            request = Vision.VNRecognizeTextRequest.alloc().init()
            request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)

            # Perform request
            success, error = handler.performRequests_error_([request], None)

            if success:
                results = request.results()
                text_parts = []

                for observation in results:
                    candidates = observation.topCandidates_(1)
                    if candidates:
                        text_parts.append(candidates[0].string())

                return '\n'.join(text_parts)

        except Exception as e:
            log(f"Vision OCR error: {e}")

        return ""

    def extract_text_tesseract(self, image_path: str) -> str:
        """Fallback: Extract text using tesseract if available."""
        try:
            import subprocess
            result = subprocess.run(
                ['tesseract', image_path, 'stdout', '-l', 'eng'],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                return result.stdout
        except Exception:
            pass

        return ""

    def extract_text(self, image_path: str) -> str:
        """Extract text from image using best available method."""
        # Try Vision first (macOS native)
        text = self.extract_text_vision(image_path)

        # Fallback to tesseract
        if not text:
            text = self.extract_text_tesseract(image_path)

        return text

    def detect_sensitive_data(self, text: str) -> List[Tuple[str, str]]:
        """Detect sensitive data patterns in text."""
        detections = []

        for pattern_name, (pattern, severity) in SENSITIVE_PATTERNS.items():
            try:
                if re.search(pattern, text, re.IGNORECASE):
                    detections.append((pattern_name, severity))
            except Exception:
                pass

        return detections

    def process_screenshot(self, image_path: str) -> Optional[Dict]:
        """Process a screenshot with OCR."""
        path = Path(image_path)

        if not path.exists():
            return None

        if str(path) in self.processed_files:
            return None

        self.processed_files.add(str(path))

        log(f"Processing: {path.name}")

        # Extract text
        text = self.extract_text(str(path))

        if not text:
            log(f"No text extracted from {path.name}")
            return None

        # Detect sensitive data
        sensitive = self.detect_sensitive_data(text)

        # Create hash
        text_hash = hashlib.sha256(text.encode()).hexdigest()

        # Prepare result
        result = {
            "device_id": self.device_id,
            "screenshot_url": str(path),
            "extracted_text": text[:10000] if self.store_text else "",  # Limit to 10K chars
            "text_hash": text_hash,
            "sensitive_detected": len(sensitive) > 0,
            "sensitive_types": [s[0] for s in sensitive] if sensitive else [],
            "app_name": "",
            "window_title": ""
        }

        # Try to get app info from filename
        # Format: screenshot_YYYYMMDD_HHMMSS_*.png
        try:
            parts = path.stem.split('_')
            if len(parts) >= 3:
                # Extract date/time from filename
                pass
        except Exception:
            pass

        # Store in Supabase
        self._send_to_supabase("ocr_extractions", result)

        # Alert on sensitive data
        if sensitive and self.detect_sensitive:
            highest_severity = max(sensitive, key=lambda s: {'low': 0, 'medium': 1, 'high': 2, 'critical': 3}.get(s[1], 0))
            if highest_severity[1] in ('high', 'critical'):
                self._create_security_alert(
                    "ocr_sensitive_data",
                    highest_severity[1],
                    f"Sensitive Data on Screen: {highest_severity[0]}",
                    f"OCR detected sensitive data ({', '.join([s[0] for s in sensitive])}) in screenshot. "
                    f"File: {path.name}"
                )

        log(f"OCR complete: {len(text)} chars, {len(sensitive)} sensitive items")
        return result

    def scan_screenshots_dir(self):
        """Scan screenshots directory for new files."""
        if not SCREENSHOTS_DIR.exists():
            return

        for file in SCREENSHOTS_DIR.glob("*.png"):
            if str(file) not in self.processed_files:
                self.process_screenshot(str(file))

        for file in SCREENSHOTS_DIR.glob("*.jpg"):
            if str(file) not in self.processed_files:
                self.process_screenshot(str(file))

    def run(self):
        """Main monitoring loop."""
        log("OCR Processor starting...")

        if not HAS_VISION:
            log("WARNING: Vision framework not available. OCR quality may be limited.")

        try:
            while True:
                if self.enabled:
                    self.scan_screenshots_dir()

                # Check every 30 seconds
                time.sleep(30)

        except KeyboardInterrupt:
            log("OCR Processor stopping...")


def main():
    """Entry point."""
    processor = OCRProcessor()
    processor.run()


if __name__ == "__main__":
    main()
