#!/usr/bin/env python3
"""
Daily Summary Report for Login Monitor PRO
============================================

Sends a daily email summary of all login activity.
Run via cron or LaunchAgent at specified time.
"""

import os
import sys
import json
import smtplib
from pathlib import Path
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "config.json"
EVENTS_DIR = SCRIPT_DIR / "events"
IMAGES_DIR = SCRIPT_DIR / "captured_images"


def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}


def load_events_for_period(days=1):
    """Load events from the last N days"""
    events = []
    cutoff = datetime.now() - timedelta(days=days)

    if EVENTS_DIR.exists():
        for event_file in EVENTS_DIR.glob("*.json"):
            try:
                with open(event_file, 'r') as f:
                    event = json.load(f)

                event_time = datetime.strptime(event['timestamp'], '%Y-%m-%d %H:%M:%S')
                if event_time >= cutoff:
                    events.append(event)
            except:
                pass

    return sorted(events, key=lambda x: x['timestamp'])


def generate_summary_html(events, period_name="Daily"):
    """Generate HTML summary report"""
    now = datetime.now().strftime('%Y-%m-%d %H:%M')

    # Statistics
    total = len(events)
    by_type = {}
    by_user = {}
    locations = []

    for e in events:
        event_type = e.get('event_type', 'Unknown')
        by_type[event_type] = by_type.get(event_type, 0) + 1

        user = e.get('user', 'Unknown')
        by_user[user] = by_user.get(user, 0) + 1

        loc = e.get('location', {})
        if loc.get('city'):
            locations.append(loc['city'])

    unique_locations = list(set(locations))

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; background: #1a1a2e; color: #eee; padding: 20px; }}
        .container {{ max-width: 800px; margin: 0 auto; }}
        .header {{ background: linear-gradient(135deg, #0f3460, #16213e); padding: 30px; border-radius: 10px; text-align: center; }}
        .header h1 {{ margin: 0; color: #00ff88; }}
        .stats {{ display: flex; justify-content: space-around; margin: 20px 0; }}
        .stat-card {{ background: #16213e; padding: 20px; border-radius: 10px; text-align: center; flex: 1; margin: 0 10px; }}
        .stat-number {{ font-size: 2.5em; font-weight: bold; color: #00aaff; }}
        .stat-label {{ color: #888; }}
        .events-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        .events-table th, .events-table td {{ padding: 12px; text-align: left; border-bottom: 1px solid #333; }}
        .events-table th {{ background: #0f3460; }}
        .badge {{ padding: 4px 8px; border-radius: 4px; font-size: 0.8em; }}
        .badge-login {{ background: #00ff88; color: #000; }}
        .badge-unlock {{ background: #00aaff; color: #000; }}
        .badge-wake {{ background: #ffaa00; color: #000; }}
        .footer {{ text-align: center; color: #666; margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 Login Monitor PRO</h1>
            <h2>{period_name} Summary Report</h2>
            <p>Generated: {now}</p>
        </div>

        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{total}</div>
                <div class="stat-label">Total Events</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{len(by_user)}</div>
                <div class="stat-label">Users</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{len(unique_locations)}</div>
                <div class="stat-label">Locations</div>
            </div>
        </div>

        <h3>📊 Events by Type</h3>
        <ul>
"""

    for event_type, count in by_type.items():
        html += f"<li>{event_type}: {count}</li>\n"

    html += """
        </ul>

        <h3>📋 Event Log</h3>
        <table class="events-table">
            <tr>
                <th>Time</th>
                <th>Type</th>
                <th>User</th>
                <th>Location</th>
                <th>IP</th>
            </tr>
"""

    for e in events:
        event_type = e.get('event_type', 'Unknown')
        badge_class = f"badge-{event_type.lower()}"

        html += f"""
            <tr>
                <td>{e.get('timestamp', 'N/A')}</td>
                <td><span class="badge {badge_class}">{event_type}</span></td>
                <td>{e.get('user', 'N/A')}</td>
                <td>{e.get('location', {}).get('city', 'Unknown')}</td>
                <td>{e.get('public_ip', 'N/A')}</td>
            </tr>
"""

    html += """
        </table>

        <div class="footer">
            <p>🔐 Login Monitor PRO - Keep your devices safe</p>
        </div>
    </div>
</body>
</html>
"""
    return html


def send_summary(config, html_content, period_name="Daily"):
    """Send summary email"""
    smtp_config = config.get('smtp', {})

    if not smtp_config.get('sender_email'):
        print("Email not configured")
        return False

    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = smtp_config['sender_email']
        msg['To'] = config.get('notification_email', smtp_config['sender_email'])
        msg['Subject'] = f"[Login Monitor] {period_name} Summary - {datetime.now().strftime('%Y-%m-%d')}"

        # Plain text version
        text = f"Login Monitor {period_name} Summary\n\nPlease view this email in HTML format."
        msg.attach(MIMEText(text, 'plain'))

        # HTML version
        msg.attach(MIMEText(html_content, 'html'))

        # Send
        if smtp_config.get('use_ssl', True):
            server = smtplib.SMTP_SSL(smtp_config['server'], smtp_config['port'])
        else:
            server = smtplib.SMTP(smtp_config['server'], smtp_config['port'])
            if smtp_config.get('use_tls', False):
                server.starttls()

        server.login(smtp_config['sender_email'], smtp_config['password'])
        server.send_message(msg)
        server.quit()

        print(f"{period_name} summary sent!")
        return True

    except Exception as e:
        print(f"Failed to send summary: {e}")
        return False


def main():
    print("="*60)
    print("LOGIN MONITOR PRO - Daily Summary")
    print("="*60)

    config = load_config()

    # Get events from last 24 hours
    events = load_events_for_period(days=1)
    print(f"Found {len(events)} events in the last 24 hours")

    # Generate and send summary
    html = generate_summary_html(events, "Daily")
    send_summary(config, html, "Daily")


if __name__ == "__main__":
    main()
