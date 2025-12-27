#!/usr/bin/env python3
"""
Report Generator for Login Monitor PRO
Generates daily/weekly/monthly security reports.
"""

import json
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List
from collections import defaultdict


def get_base_dir() -> Path:
    """Get base directory for data files"""
    return Path.home() / ".login-monitor"


def log(message: str):
    """Write timestamped log message"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] [ReportGenerator] {message}"
    print(log_msg, flush=True)

    try:
        log_file = Path("/tmp/loginmonitor-reports.log")
        with open(log_file, "a") as f:
            f.write(log_msg + "\n")
    except:
        pass


class ReportGenerator:
    """Generates security reports"""

    def __init__(self):
        self.base_dir = get_base_dir()
        self.config = self._load_config()
        self.reports_dir = self.base_dir / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

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

    def get_events(self, since: datetime, until: datetime = None) -> List[Dict]:
        """Get events from Supabase for the report period"""
        events = []
        until = until or datetime.now()

        try:
            from supabase_client import SupabaseClient

            config = self._load_config()
            supabase_config = config.get("supabase", {})

            if not supabase_config.get("url") or not supabase_config.get("device_id"):
                return events

            client = SupabaseClient(
                url=supabase_config["url"],
                anon_key=supabase_config.get("anon_key", ""),
                service_key=supabase_config.get("service_key", supabase_config.get("anon_key", ""))
            )

            result = client._request(
                "GET",
                f"/rest/v1/events?device_id=eq.{supabase_config['device_id']}"
                f"&timestamp=gte.{since.isoformat()}"
                f"&timestamp=lte.{until.isoformat()}"
                f"&order=timestamp.desc",
                use_service_key=True
            )

            events = result if result else []

        except Exception as e:
            log(f"Error fetching events: {e}")

        return events

    def get_app_usage(self, since: datetime, until: datetime = None) -> List[Dict]:
        """Get app usage data for the report period"""
        usage = []
        until = until or datetime.now()

        try:
            db_path = self.base_dir / "app_usage.db"
            if not db_path.exists():
                return usage

            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            cursor.execute('''
                SELECT app_name, SUM(duration_seconds) as total, COUNT(*) as sessions
                FROM app_sessions
                WHERE launched_at >= ? AND launched_at <= ?
                GROUP BY app_name
                ORDER BY total DESC
            ''', (since.isoformat(), until.isoformat()))

            for row in cursor.fetchall():
                usage.append({
                    "app_name": row[0],
                    "total_seconds": row[1],
                    "sessions": row[2]
                })

            conn.close()

        except Exception as e:
            log(f"Error fetching app usage: {e}")

        return usage

    def generate_report(self, report_type: str = "daily") -> Dict:
        """Generate a report for the specified period"""
        now = datetime.now()

        if report_type == "daily":
            since = now - timedelta(days=1)
            period_name = "Daily"
        elif report_type == "weekly":
            since = now - timedelta(weeks=1)
            period_name = "Weekly"
        elif report_type == "monthly":
            since = now - timedelta(days=30)
            period_name = "Monthly"
        else:
            since = now - timedelta(days=1)
            period_name = "Custom"

        log(f"Generating {period_name} report from {since} to {now}")

        # Fetch data
        events = self.get_events(since, now)
        app_usage = self.get_app_usage(since, now)

        # Analyze events
        event_summary = self._analyze_events(events)
        security_alerts = self._get_security_alerts(events)
        photos_captured = len([e for e in events if e.get("photos")])

        # Generate summary
        summary = {
            "report_type": report_type,
            "period_name": period_name,
            "period_start": since.isoformat(),
            "period_end": now.isoformat(),
            "generated_at": now.isoformat(),

            "total_events": len(events),
            "events_by_type": event_summary,
            "security_alerts": security_alerts,
            "photos_captured": photos_captured,

            "app_usage_summary": app_usage[:10],  # Top 10 apps

            "highlights": self._generate_highlights(events, security_alerts)
        }

        # Save report locally
        report_filename = f"report_{report_type}_{now.strftime('%Y%m%d_%H%M%S')}.json"
        report_path = self.reports_dir / report_filename

        with open(report_path, 'w') as f:
            json.dump(summary, f, indent=2)

        log(f"Report saved: {report_path}")

        # Upload to Supabase
        self._upload_report(summary, report_type, since, now)

        return summary

    def _analyze_events(self, events: List[Dict]) -> Dict:
        """Analyze events by type"""
        by_type = defaultdict(int)

        for event in events:
            event_type = event.get("event_type", "Unknown")
            by_type[event_type] += 1

        return dict(by_type)

    def _get_security_alerts(self, events: List[Dict]) -> List[Dict]:
        """Extract security-related events"""
        security_types = [
            "Intruder",
            "UnknownUSB",
            "UnknownNetwork",
            "GeofenceExit",
            "Movement",
            "SuspiciousApp"
        ]

        alerts = []
        for event in events:
            if event.get("event_type") in security_types:
                alerts.append({
                    "type": event.get("event_type"),
                    "timestamp": event.get("timestamp"),
                    "details": {
                        k: v for k, v in event.items()
                        if k not in ["id", "device_id", "created_at", "is_read"]
                    }
                })

        return alerts

    def _generate_highlights(self, events: List[Dict], alerts: List[Dict]) -> List[str]:
        """Generate report highlights"""
        highlights = []

        if not events:
            highlights.append("No events recorded during this period.")
            return highlights

        # Count event types
        logins = len([e for e in events if e.get("event_type") == "Login"])
        unlocks = len([e for e in events if e.get("event_type") == "Unlock"])

        if logins > 0:
            highlights.append(f"{logins} login event(s) recorded.")

        if unlocks > 0:
            highlights.append(f"{unlocks} screen unlock event(s) recorded.")

        # Security alerts
        if alerts:
            alert_types = set(a["type"] for a in alerts)
            highlights.append(f"{len(alerts)} security alert(s): {', '.join(alert_types)}")

        # Photos
        photos = len([e for e in events if e.get("photos")])
        if photos > 0:
            highlights.append(f"{photos} event(s) with photos captured.")

        return highlights

    def _upload_report(self, summary: Dict, report_type: str, since: datetime, until: datetime):
        """Upload report summary to Supabase"""
        try:
            from supabase_client import SupabaseClient

            config = self._load_config()
            supabase_config = config.get("supabase", {})

            if not supabase_config.get("url") or not supabase_config.get("device_id"):
                return

            client = SupabaseClient(
                url=supabase_config["url"],
                anon_key=supabase_config.get("anon_key", ""),
                service_key=supabase_config.get("service_key", supabase_config.get("anon_key", ""))
            )

            client._request(
                "POST",
                "/rest/v1/reports",
                {
                    "device_id": supabase_config["device_id"],
                    "report_type": report_type,
                    "period_start": since.isoformat(),
                    "period_end": until.isoformat(),
                    "summary": summary
                },
                use_service_key=True
            )

            log("Report uploaded to Supabase")

        except Exception as e:
            log(f"Error uploading report: {e}")

    def generate_html_report(self, summary: Dict) -> str:
        """Generate an HTML version of the report"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Login Monitor PRO - {summary['period_name']} Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0C1F1F;
            color: #FDFEFE;
            padding: 20px;
            max-width: 800px;
            margin: 0 auto;
        }}
        h1, h2, h3 {{
            color: #06E6DA;
        }}
        .card {{
            background: #1a2f2f;
            border: 1px solid #06E6DA;
            border-radius: 8px;
            padding: 16px;
            margin: 16px 0;
        }}
        .alert {{
            background: #2a1a1a;
            border-color: #FF3B3B;
        }}
        .stat {{
            font-size: 24px;
            font-weight: bold;
            color: #06E6DA;
        }}
        .highlight {{
            background: #06E6DA;
            color: #0C1F1F;
            padding: 4px 8px;
            border-radius: 4px;
            margin: 4px 0;
            display: inline-block;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 8px;
            text-align: left;
            border-bottom: 1px solid #333;
        }}
        th {{
            color: #06E6DA;
        }}
    </style>
</head>
<body>
    <h1>Login Monitor PRO</h1>
    <h2>{summary['period_name']} Security Report</h2>
    <p>Period: {summary['period_start'][:10]} to {summary['period_end'][:10]}</p>

    <div class="card">
        <h3>Summary</h3>
        <p>Total Events: <span class="stat">{summary['total_events']}</span></p>
        <p>Security Alerts: <span class="stat">{len(summary['security_alerts'])}</span></p>
        <p>Photos Captured: <span class="stat">{summary['photos_captured']}</span></p>
    </div>

    <div class="card">
        <h3>Highlights</h3>
        {''.join(f'<p class="highlight">{h}</p><br>' for h in summary['highlights'])}
    </div>

    <div class="card">
        <h3>Events by Type</h3>
        <table>
            <tr><th>Event Type</th><th>Count</th></tr>
            {''.join(f'<tr><td>{k}</td><td>{v}</td></tr>' for k, v in summary['events_by_type'].items())}
        </table>
    </div>

    {'<div class="card alert"><h3>Security Alerts</h3>' + ''.join(f'''
        <p><strong>{a["type"]}</strong> - {a["timestamp"][:19]}</p>
    ''' for a in summary['security_alerts'][:5]) + '</div>' if summary['security_alerts'] else ''}

    {'<div class="card"><h3>Top Apps</h3><table><tr><th>App</th><th>Time</th><th>Sessions</th></tr>' + ''.join(f'''
        <tr>
            <td>{a["app_name"]}</td>
            <td>{a["total_seconds"] // 60}m</td>
            <td>{a["sessions"]}</td>
        </tr>
    ''' for a in summary['app_usage_summary'][:5]) + '</table></div>' if summary.get('app_usage_summary') else ''}

    <p style="text-align: center; margin-top: 40px; color: #666;">
        Generated by Login Monitor PRO<br>
        {summary['generated_at'][:19]}
    </p>
</body>
</html>
        """

        # Save HTML report
        html_filename = f"report_{summary['report_type']}_{summary['generated_at'][:10].replace('-', '')}.html"
        html_path = self.reports_dir / html_filename

        with open(html_path, 'w') as f:
            f.write(html)

        log(f"HTML report saved: {html_path}")

        return str(html_path)

    def list_reports(self) -> List[Dict]:
        """List all generated reports"""
        reports = []

        for report_file in self.reports_dir.glob("*.json"):
            try:
                with open(report_file) as f:
                    report = json.load(f)
                    reports.append({
                        "filename": report_file.name,
                        "report_type": report.get("report_type"),
                        "period_start": report.get("period_start"),
                        "period_end": report.get("period_end"),
                        "generated_at": report.get("generated_at"),
                        "total_events": report.get("total_events"),
                        "security_alerts": len(report.get("security_alerts", []))
                    })
            except:
                pass

        return sorted(reports, key=lambda x: x.get("generated_at", ""), reverse=True)


def main():
    import sys

    generator = ReportGenerator()

    report_type = "daily"
    if len(sys.argv) > 1:
        report_type = sys.argv[1]

    summary = generator.generate_report(report_type)
    html_path = generator.generate_html_report(summary)

    print(f"\nReport generated!")
    print(f"Period: {summary['period_name']}")
    print(f"Total events: {summary['total_events']}")
    print(f"Security alerts: {len(summary['security_alerts'])}")
    print(f"\nHTML report: {html_path}")


if __name__ == "__main__":
    main()
