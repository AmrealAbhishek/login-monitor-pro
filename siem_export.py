#!/usr/bin/env python3
"""
CyVigil SIEM/Webhook Integration
=================================
Exports security events to SIEM systems, webhooks, and collaboration tools.
Supports: Splunk, Microsoft Sentinel, Elastic, Slack, Teams, Discord, custom webhooks.
"""

import os
import sys
import json
import time
import hashlib
import hmac
import base64
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from enum import Enum
import threading
from queue import Queue, Empty

import requests

# Configuration
CONFIG_PATH = Path.home() / ".login-monitor" / "config.json"
LOG_PATH = "/tmp/loginmonitor-siem.log"

# Event types to export
EVENT_TYPES = [
    'security_alerts',
    'usb_events',
    'clipboard_events',
    'shadow_it_detections',
    'file_transfer_events',
    'events',  # Login/unlock events
]


class IntegrationType(Enum):
    SPLUNK = "splunk"
    SENTINEL = "sentinel"
    ELASTIC = "elastic"
    WEBHOOK = "webhook"
    SLACK = "slack"
    TEAMS = "teams"
    DISCORD = "discord"
    SYSLOG = "syslog"


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


class SIEMIntegration:
    """Base class for SIEM integrations."""

    def __init__(self, config: Dict):
        self.config = config
        self.name = config.get('name', 'Unknown')
        self.endpoint = config.get('endpoint_url', '')
        self.auth_type = config.get('auth_type', 'none')
        self.auth_token = config.get('auth_token', '')
        self.enabled = config.get('enabled', True)

    def send(self, event: Dict) -> bool:
        """Send event to the integration."""
        raise NotImplementedError

    def format_event(self, event: Dict) -> Dict:
        """Format event for this integration."""
        return event


class SplunkIntegration(SIEMIntegration):
    """Splunk HEC (HTTP Event Collector) integration."""

    def format_event(self, event: Dict) -> Dict:
        """Format event for Splunk HEC."""
        return {
            "event": event,
            "sourcetype": "cyvigil:security",
            "source": "cyvigil",
            "host": event.get('device_id', 'unknown'),
            "time": datetime.now().timestamp()
        }

    def send(self, event: Dict) -> bool:
        """Send event to Splunk HEC."""
        try:
            formatted = self.format_event(event)
            response = requests.post(
                self.endpoint,
                headers={
                    "Authorization": f"Splunk {self.auth_token}",
                    "Content-Type": "application/json"
                },
                json=formatted,
                timeout=10,
                verify=True
            )
            return response.status_code in (200, 201)
        except Exception as e:
            log(f"Splunk error: {e}")
            return False


class SentinelIntegration(SIEMIntegration):
    """Microsoft Sentinel (Log Analytics) integration."""

    def __init__(self, config: Dict):
        super().__init__(config)
        self.workspace_id = config.get('workspace_id', '')
        self.shared_key = config.get('shared_key', '')
        self.log_type = config.get('log_type', 'CyVigil')

    def _build_signature(self, date: str, content_length: int, method: str = "POST",
                         content_type: str = "application/json", resource: str = "/api/logs") -> str:
        """Build the API signature for Azure Log Analytics."""
        x_headers = f"x-ms-date:{date}"
        string_to_hash = f"{method}\n{content_length}\n{content_type}\n{x_headers}\n{resource}"
        bytes_to_hash = string_to_hash.encode('utf-8')
        decoded_key = base64.b64decode(self.shared_key)
        encoded_hash = base64.b64encode(
            hmac.new(decoded_key, bytes_to_hash, digestmod=hashlib.sha256).digest()
        ).decode('utf-8')
        return f"SharedKey {self.workspace_id}:{encoded_hash}"

    def send(self, event: Dict) -> bool:
        """Send event to Microsoft Sentinel."""
        try:
            body = json.dumps([event])
            content_length = len(body)
            rfc1123_date = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
            signature = self._build_signature(rfc1123_date, content_length)

            url = f"https://{self.workspace_id}.ods.opinsights.azure.com/api/logs?api-version=2016-04-01"

            response = requests.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "Log-Type": self.log_type,
                    "Authorization": signature,
                    "x-ms-date": rfc1123_date,
                    "time-generated-field": "created_at"
                },
                data=body,
                timeout=10
            )
            return response.status_code in (200, 202)
        except Exception as e:
            log(f"Sentinel error: {e}")
            return False


class ElasticIntegration(SIEMIntegration):
    """Elasticsearch integration."""

    def __init__(self, config: Dict):
        super().__init__(config)
        self.index = config.get('index', 'cyvigil-events')

    def send(self, event: Dict) -> bool:
        """Send event to Elasticsearch."""
        try:
            url = f"{self.endpoint}/{self.index}/_doc"
            headers = {"Content-Type": "application/json"}

            if self.auth_type == "bearer":
                headers["Authorization"] = f"Bearer {self.auth_token}"
            elif self.auth_type == "basic":
                headers["Authorization"] = f"Basic {self.auth_token}"
            elif self.auth_type == "api_key":
                headers["Authorization"] = f"ApiKey {self.auth_token}"

            event['@timestamp'] = datetime.utcnow().isoformat()

            response = requests.post(
                url,
                headers=headers,
                json=event,
                timeout=10
            )
            return response.status_code in (200, 201)
        except Exception as e:
            log(f"Elastic error: {e}")
            return False


class SlackIntegration(SIEMIntegration):
    """Slack webhook integration."""

    def format_event(self, event: Dict) -> Dict:
        """Format event as Slack message."""
        event_type = event.get('alert_type', event.get('event_type', 'Unknown'))
        severity = event.get('severity', 'info').upper()
        title = event.get('title', event_type)
        description = event.get('description', '')
        device_id = event.get('device_id', 'Unknown')[:8]

        # Color based on severity
        colors = {
            'LOW': '#36a64f',      # Green
            'MEDIUM': '#f2c744',   # Yellow
            'HIGH': '#ff9000',     # Orange
            'CRITICAL': '#ff0000', # Red
            'INFO': '#0066cc'      # Blue
        }
        color = colors.get(severity, '#cccccc')

        return {
            "attachments": [{
                "color": color,
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"🔒 CyVigil Alert: {title}"
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*Severity:*\n{severity}"},
                            {"type": "mrkdwn", "text": f"*Device:*\n{device_id}..."},
                            {"type": "mrkdwn", "text": f"*Type:*\n{event_type}"},
                            {"type": "mrkdwn", "text": f"*Time:*\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}
                        ]
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Details:*\n{description[:500]}"
                        }
                    }
                ]
            }]
        }

    def send(self, event: Dict) -> bool:
        """Send event to Slack."""
        try:
            formatted = self.format_event(event)
            response = requests.post(
                self.endpoint,
                json=formatted,
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            log(f"Slack error: {e}")
            return False


class TeamsIntegration(SIEMIntegration):
    """Microsoft Teams webhook integration."""

    def format_event(self, event: Dict) -> Dict:
        """Format event as Teams Adaptive Card."""
        event_type = event.get('alert_type', event.get('event_type', 'Unknown'))
        severity = event.get('severity', 'info').upper()
        title = event.get('title', event_type)
        description = event.get('description', '')

        # Color based on severity
        colors = {'LOW': 'good', 'MEDIUM': 'warning', 'HIGH': 'attention', 'CRITICAL': 'attention'}

        return {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": "ff0000" if severity == 'CRITICAL' else "0076D7",
            "summary": f"CyVigil Alert: {title}",
            "sections": [{
                "activityTitle": f"🔒 CyVigil Alert: {title}",
                "facts": [
                    {"name": "Severity", "value": severity},
                    {"name": "Type", "value": event_type},
                    {"name": "Time", "value": datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                ],
                "text": description[:500],
                "markdown": True
            }]
        }

    def send(self, event: Dict) -> bool:
        """Send event to Microsoft Teams."""
        try:
            formatted = self.format_event(event)
            response = requests.post(
                self.endpoint,
                json=formatted,
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            log(f"Teams error: {e}")
            return False


class DiscordIntegration(SIEMIntegration):
    """Discord webhook integration."""

    def format_event(self, event: Dict) -> Dict:
        """Format event as Discord embed."""
        event_type = event.get('alert_type', event.get('event_type', 'Unknown'))
        severity = event.get('severity', 'info').upper()
        title = event.get('title', event_type)
        description = event.get('description', '')

        # Color based on severity (Discord uses decimal)
        colors = {
            'LOW': 3066993,      # Green
            'MEDIUM': 15844367,  # Yellow
            'HIGH': 16744448,    # Orange
            'CRITICAL': 16711680 # Red
        }

        return {
            "embeds": [{
                "title": f"🔒 CyVigil Alert: {title}",
                "description": description[:500],
                "color": colors.get(severity, 7506394),
                "fields": [
                    {"name": "Severity", "value": severity, "inline": True},
                    {"name": "Type", "value": event_type, "inline": True}
                ],
                "timestamp": datetime.utcnow().isoformat()
            }]
        }

    def send(self, event: Dict) -> bool:
        """Send event to Discord."""
        try:
            formatted = self.format_event(event)
            response = requests.post(
                self.endpoint,
                json=formatted,
                timeout=10
            )
            return response.status_code in (200, 204)
        except Exception as e:
            log(f"Discord error: {e}")
            return False


class WebhookIntegration(SIEMIntegration):
    """Generic webhook integration."""

    def send(self, event: Dict) -> bool:
        """Send event to generic webhook."""
        try:
            headers = {"Content-Type": "application/json"}

            if self.auth_type == "bearer":
                headers["Authorization"] = f"Bearer {self.auth_token}"
            elif self.auth_type == "basic":
                headers["Authorization"] = f"Basic {self.auth_token}"
            elif self.auth_type == "api_key":
                headers["X-API-Key"] = self.auth_token

            response = requests.post(
                self.endpoint,
                headers=headers,
                json=event,
                timeout=10
            )
            return response.status_code in (200, 201, 202, 204)
        except Exception as e:
            log(f"Webhook error: {e}")
            return False


class SIEMExporter:
    """Main SIEM exporter service."""

    def __init__(self):
        self.config = self._load_config()
        self.device_id = self.config.get("device_id", "")
        self.supabase_url = self.config.get("supabase_url", "")
        self.supabase_key = self.config.get("supabase_key", "")

        # Event queue for async processing
        self.event_queue: Queue = Queue()

        # Integrations
        self.integrations: List[SIEMIntegration] = []
        self._load_integrations()

        # Track last export time per event type
        self.last_export: Dict[str, datetime] = {}

        log(f"SIEM Exporter initialized. {len(self.integrations)} integrations loaded.")

    def _load_config(self) -> dict:
        """Load configuration from file."""
        try:
            if CONFIG_PATH.exists():
                with open(CONFIG_PATH) as f:
                    return json.load(f)
        except Exception as e:
            log(f"Error loading config: {e}")
        return {}

    def _load_integrations(self):
        """Load integrations from config."""
        integrations_config = self.config.get("siem_integrations", [])

        # Also try to load from Supabase
        try:
            if self.supabase_url and self.supabase_key:
                response = requests.get(
                    f"{self.supabase_url}/rest/v1/siem_integrations?enabled=eq.true",
                    headers={
                        "apikey": self.supabase_key,
                        "Authorization": f"Bearer {self.supabase_key}"
                    },
                    timeout=10
                )
                if response.status_code == 200:
                    integrations_config.extend(response.json())
        except Exception as e:
            log(f"Failed to load integrations from Supabase: {e}")

        for config in integrations_config:
            integration = self._create_integration(config)
            if integration and integration.enabled:
                self.integrations.append(integration)
                log(f"Loaded integration: {integration.name} ({config.get('integration_type', 'webhook')})")

    def _create_integration(self, config: Dict) -> Optional[SIEMIntegration]:
        """Create integration instance based on type."""
        integration_type = config.get('integration_type', 'webhook').lower()

        integrations_map = {
            'splunk': SplunkIntegration,
            'sentinel': SentinelIntegration,
            'elastic': ElasticIntegration,
            'slack': SlackIntegration,
            'teams': TeamsIntegration,
            'discord': DiscordIntegration,
            'webhook': WebhookIntegration,
        }

        integration_class = integrations_map.get(integration_type, WebhookIntegration)
        return integration_class(config)

    def _fetch_new_events(self, table: str) -> List[Dict]:
        """Fetch new events from Supabase."""
        if not self.supabase_url or not self.supabase_key:
            return []

        try:
            # Get events since last export
            since = self.last_export.get(table, datetime.now() - timedelta(minutes=5))
            since_str = since.isoformat()

            response = requests.get(
                f"{self.supabase_url}/rest/v1/{table}?created_at=gt.{since_str}&order=created_at.asc&limit=100",
                headers={
                    "apikey": self.supabase_key,
                    "Authorization": f"Bearer {self.supabase_key}"
                },
                timeout=10
            )

            if response.status_code == 200:
                events = response.json()
                if events:
                    self.last_export[table] = datetime.now()
                return events

        except Exception as e:
            log(f"Error fetching events from {table}: {e}")

        return []

    def _log_export(self, integration_id: str, event_type: str, event_id: str,
                    status: str, response_code: int = None, error: str = None):
        """Log export attempt to Supabase."""
        try:
            data = {
                "integration_id": integration_id,
                "event_type": event_type,
                "event_id": event_id,
                "status": status,
                "response_code": response_code,
                "error_message": error
            }
            requests.post(
                f"{self.supabase_url}/rest/v1/siem_export_log",
                headers={
                    "apikey": self.supabase_key,
                    "Authorization": f"Bearer {self.supabase_key}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal"
                },
                json=data,
                timeout=5
            )
        except Exception:
            pass

    def export_event(self, event: Dict, event_type: str):
        """Export event to all integrations."""
        for integration in self.integrations:
            try:
                success = integration.send(event)
                status = "sent" if success else "failed"
                log(f"Export to {integration.name}: {status}")
            except Exception as e:
                log(f"Export to {integration.name} failed: {e}")

    def _worker(self):
        """Worker thread for processing events."""
        while True:
            try:
                event, event_type = self.event_queue.get(timeout=1)
                self.export_event(event, event_type)
                self.event_queue.task_done()
            except Empty:
                continue
            except Exception as e:
                log(f"Worker error: {e}")

    def run(self):
        """Main export loop."""
        log("SIEM Exporter starting...")

        if not self.integrations:
            log("No integrations configured. Add integrations in config.json or dashboard.")
            log("Example config:")
            log('  "siem_integrations": [{"integration_type": "slack", "endpoint_url": "https://hooks.slack.com/...", "enabled": true}]')

        # Start worker threads
        for _ in range(2):
            worker = threading.Thread(target=self._worker, daemon=True)
            worker.start()

        try:
            while True:
                # Fetch and export events from each table
                for table in EVENT_TYPES:
                    events = self._fetch_new_events(table)
                    for event in events:
                        event['_event_type'] = table
                        self.event_queue.put((event, table))

                # Check every 30 seconds
                time.sleep(30)

        except KeyboardInterrupt:
            log("SIEM Exporter stopping...")


def main():
    """Entry point."""
    exporter = SIEMExporter()
    exporter.run()


if __name__ == "__main__":
    main()
