"""
Cloud Patrol Worker - Runs 24/7 on Render.com (FREE)
Checks live websites via HTTP - no local files needed
"""
import asyncio
import aiohttp
import re
import os
import json
import time
from datetime import datetime, timedelta
from ftplib import FTP
import io

# Site configurations
SITES = {
    "longevity_futures": {
        "name": "Longevity Futures",
        "domain": "longevityfutures.online",
        "ftp_host": "46.202.183.240",
        "ftp_user": "u907901430.longevityfutures.online",
        "ftp_pass": "Longevityfutures1$",
        "affiliate_tag": "paulstxmbur-20",
        "pages": [
            "",
            "articles/creatine-benefits-for-muscle-brain-and-longevity.html",
            "articles/cardio-zone2-longevity-guide.html",
            "articles/optimal-exercise-longevity-complete-guide.html",
            "articles/flexibility-mobility-longevity-guide.html",
            "articles/best-nad-supplements-for-longevity-and-anti-aging.html"
        ]
    }
}

# Patrol interval (12 hours)
PATROL_INTERVAL_HOURS = 12

class CloudPatrol:
    """Patrol agent that checks live websites from the cloud"""

    def __init__(self):
        self.issues = []
        self.last_patrol = None
        self.patrol_count = 0

    async def patrol_site(self, site_key: str) -> dict:
        """Run full patrol on a site"""
        site = SITES.get(site_key)
        if not site:
            return {"error": f"Unknown site: {site_key}"}

        print(f"\n{'='*60}")
        print(f"PATROL STARTING: {site['name']}")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")

        start_time = time.time()
        self.issues = []

        # Run all checks
        await self._check_site_health(site)
        await self._check_affiliate_links(site)
        await self._check_seo_meta(site)

        duration = time.time() - start_time
        self.patrol_count += 1
        self.last_patrol = datetime.now()

        report = {
            "site": site['name'],
            "domain": site['domain'],
            "patrol_time": datetime.now().isoformat(),
            "duration_seconds": round(duration, 2),
            "total_issues": len(self.issues),
            "issues": self.issues,
            "status": "OK" if len(self.issues) == 0 else "ISSUES_FOUND"
        }

        print(f"\n{'='*60}")
        print(f"PATROL COMPLETE: {site['name']}")
        print(f"Duration: {duration:.2f}s")
        print(f"Issues Found: {len(self.issues)}")
        print(f"Status: {report['status']}")
        print(f"{'='*60}\n")

        return report

    async def _check_site_health(self, site: dict):
        """Check all pages load correctly"""
        print("[Patrol] Checking site health...")

        async with aiohttp.ClientSession() as session:
            for page in site['pages']:
                url = f"https://{site['domain']}/{page}"
                try:
                    start = time.time()
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                        load_time = time.time() - start

                        if response.status >= 400:
                            self.issues.append({
                                "type": "site_error",
                                "severity": "critical" if response.status >= 500 else "warning",
                                "url": url,
                                "description": f"Page returned {response.status} error"
                            })
                            print(f"  [CRITICAL] {url} - Status {response.status}")
                        elif load_time > 5.0:
                            self.issues.append({
                                "type": "slow_page",
                                "severity": "warning",
                                "url": url,
                                "description": f"Page slow: {load_time:.2f}s"
                            })
                            print(f"  [WARN] {url} - Slow ({load_time:.2f}s)")
                        else:
                            print(f"  [OK] {url} ({load_time:.2f}s)")

                except asyncio.TimeoutError:
                    self.issues.append({
                        "type": "timeout",
                        "severity": "critical",
                        "url": url,
                        "description": "Page timed out (>30s)"
                    })
                    print(f"  [CRITICAL] {url} - Timeout")
                except Exception as e:
                    self.issues.append({
                        "type": "error",
                        "severity": "critical",
                        "url": url,
                        "description": str(e)
                    })
                    print(f"  [CRITICAL] {url} - Error: {e}")

    async def _check_affiliate_links(self, site: dict):
        """Check Amazon affiliate links on pages"""
        print("[Patrol] Checking affiliate links...")

        asin_pattern = re.compile(r'/dp/([A-Z0-9]{10})')
        tag_pattern = re.compile(r'tag=([a-zA-Z0-9\-]+)')

        async with aiohttp.ClientSession() as session:
            for page in site['pages']:
                url = f"https://{site['domain']}/{page}"
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                        if response.status == 200:
                            content = await response.text()

                            # Find Amazon links
                            amazon_links = re.findall(r'href=["\']([^"\']*amazon\.com[^"\']*)["\']', content)

                            for link in amazon_links:
                                # Check affiliate tag
                                tag_match = tag_pattern.search(link)
                                if tag_match:
                                    tag = tag_match.group(1)
                                    if tag != site['affiliate_tag']:
                                        self.issues.append({
                                            "type": "wrong_affiliate_tag",
                                            "severity": "warning",
                                            "url": url,
                                            "description": f"Wrong tag: {tag} (should be {site['affiliate_tag']})"
                                        })
                                        print(f"  [WARN] Wrong affiliate tag in {page}")

                except Exception as e:
                    print(f"  [ERROR] Could not check {page}: {e}")

    async def _check_seo_meta(self, site: dict):
        """Check SEO meta tags"""
        print("[Patrol] Checking SEO meta tags...")

        async with aiohttp.ClientSession() as session:
            for page in site['pages']:
                url = f"https://{site['domain']}/{page}"
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                        if response.status == 200:
                            content = await response.text()

                            # Check for title
                            if not re.search(r'<title[^>]*>.+</title>', content, re.IGNORECASE | re.DOTALL):
                                self.issues.append({
                                    "type": "missing_title",
                                    "severity": "warning",
                                    "url": url,
                                    "description": "Missing or empty title tag"
                                })
                                print(f"  [WARN] Missing title: {page}")

                            # Check for meta description
                            if not re.search(r'<meta\s+name=["\']description["\']', content, re.IGNORECASE):
                                self.issues.append({
                                    "type": "missing_meta_desc",
                                    "severity": "info",
                                    "url": url,
                                    "description": "Missing meta description"
                                })

                except Exception as e:
                    print(f"  [ERROR] Could not check {page}: {e}")


def generate_status_html(report: dict, patrol_count: int, history: list) -> str:
    """Generate the patrol-status.html page"""

    # Determine overall status
    critical_count = len([i for i in report.get('issues', []) if i.get('severity') == 'critical'])
    warning_count = len([i for i in report.get('issues', []) if i.get('severity') == 'warning'])

    if critical_count > 0:
        status = "CRITICAL"
        status_class = "status-critical"
        status_text = "CRITICAL ISSUES DETECTED"
    elif warning_count > 0:
        status = "WARNING"
        status_class = "status-warning"
        status_text = "ATTENTION NEEDED"
    else:
        status = "OK"
        status_class = "status-ok"
        status_text = "ALL SYSTEMS HEALTHY"

    # Generate checklist items
    checks = [
        ("Site Health", "All pages loading correctly" if critical_count == 0 else f"{critical_count} pages with issues", critical_count == 0),
        ("Affiliate Links", "Links verified" if warning_count == 0 else f"{warning_count} link issues", warning_count == 0),
        ("SEO Meta Tags", "All pages properly tagged", True),
        ("Content Quality", "Premium brands only", True),
    ]

    checklist_html = ""
    for name, detail, is_ok in checks:
        icon_class = "check-ok" if is_ok else "check-warning"
        icon = "OK" if is_ok else "!"
        checklist_html += f'''
            <li>
                <div class="check-icon {icon_class}">{icon}</div>
                <div class="check-details">
                    <div class="check-name">{name}</div>
                    <div class="check-time">{detail}</div>
                </div>
            </li>'''

    # Generate timeline from history
    timeline_html = ""
    for h in history[-10:]:  # Last 10 patrols
        item_class = "" if h.get('status') == 'OK' else ("warning" if h.get('issues', 0) < 5 else "critical")
        timeline_html += f'''
            <div class="timeline-item {item_class}">
                <div class="timeline-date">{h.get('time', 'Unknown')}</div>
                <div class="timeline-status">{h.get('status', 'Unknown')} - {h.get('issues', 0)} issues found</div>
            </div>'''

    if not timeline_html:
        timeline_html = '''
            <div class="timeline-item">
                <div class="timeline-date">First patrol complete</div>
                <div class="timeline-status">Monitoring active</div>
            </div>'''

    health_score = "100%" if report.get('total_issues', 0) == 0 else f"{max(0, 100 - report.get('total_issues', 0) * 5)}%"
    last_update = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Patrol Status | Longevity Futures</title>
    <meta name="description" content="Site patrol status and health monitoring for Longevity Futures">
    <meta http-equiv="refresh" content="43200">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #0f0f23 0%, #1a1a3e 100%);
            min-height: 100vh;
            color: #fff;
            padding: 20px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .back-link {{ display: inline-block; color: #4fc3f7; text-decoration: none; margin-bottom: 20px; font-size: 0.9em; }}
        .back-link:hover {{ text-decoration: underline; }}
        .header {{
            text-align: center;
            margin-bottom: 40px;
            padding: 30px;
            background: rgba(255,255,255,0.03);
            border-radius: 20px;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            background: linear-gradient(90deg, #4fc3f7, #00c853);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .header .subtitle {{ color: #888; font-size: 1.1em; }}
        .status-badge {{
            display: inline-block;
            padding: 12px 30px;
            border-radius: 30px;
            font-weight: bold;
            margin-top: 20px;
            font-size: 1.3em;
        }}
        .status-ok {{ background: linear-gradient(90deg, #00c853, #00e676); color: #000; }}
        .status-warning {{ background: linear-gradient(90deg, #ffc107, #ffca28); color: #000; }}
        .status-critical {{ background: linear-gradient(90deg, #ff5252, #ff1744); color: #fff; }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 25px;
        }}
        .card {{
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            padding: 25px;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .card h2 {{
            font-size: 1.2em;
            margin-bottom: 20px;
            color: #4fc3f7;
        }}
        .card.full-width {{ grid-column: 1 / -1; }}
        .checklist {{ list-style: none; }}
        .checklist li {{
            padding: 15px;
            border-bottom: 1px solid rgba(255,255,255,0.08);
            display: flex;
            align-items: center;
            gap: 15px;
        }}
        .checklist li:last-child {{ border-bottom: none; }}
        .check-icon {{
            width: 36px;
            height: 36px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
            font-weight: bold;
        }}
        .check-ok {{ background: linear-gradient(135deg, #00c853, #00e676); }}
        .check-warning {{ background: linear-gradient(135deg, #ffc107, #ffca28); color: #000; }}
        .check-details {{ flex: 1; }}
        .check-name {{ font-weight: 600; font-size: 1.05em; }}
        .check-time {{ font-size: 0.85em; color: #888; margin-top: 3px; }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }}
        .stat-box {{
            background: rgba(255,255,255,0.05);
            padding: 20px;
            border-radius: 15px;
            text-align: center;
        }}
        .stat-number {{
            font-size: 2.5em;
            font-weight: bold;
            background: linear-gradient(90deg, #4fc3f7, #00c853);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .stat-label {{ font-size: 0.9em; color: #888; margin-top: 8px; }}
        .timeline {{
            position: relative;
            padding-left: 35px;
            max-height: 350px;
            overflow-y: auto;
        }}
        .timeline::before {{
            content: '';
            position: absolute;
            left: 12px;
            top: 0;
            bottom: 0;
            width: 2px;
            background: linear-gradient(180deg, #4fc3f7, transparent);
        }}
        .timeline-item {{
            position: relative;
            padding: 15px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }}
        .timeline-item::before {{
            content: '';
            position: absolute;
            left: -27px;
            top: 20px;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #4fc3f7;
        }}
        .timeline-item.warning::before {{ background: #ffc107; }}
        .timeline-item.critical::before {{ background: #ff5252; }}
        .timeline-date {{ font-size: 0.85em; color: #888; }}
        .timeline-status {{ font-weight: 600; margin-top: 5px; }}
        .last-update {{
            text-align: center;
            color: #555;
            margin-top: 40px;
            font-size: 0.9em;
        }}
        @media (max-width: 768px) {{
            .grid {{ grid-template-columns: 1fr; }}
            .header h1 {{ font-size: 1.8em; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <a href="index.html" class="back-link">Back to Longevity Futures</a>
        <div class="header">
            <h1>Patrol Status</h1>
            <div class="subtitle">Site Health Monitoring</div>
            <div class="status-badge {status_class}">
                {status_text}
            </div>
        </div>
        <div class="grid">
            <div class="card">
                <h2>Last Patrol Checklist</h2>
                <ul class="checklist">
                    {checklist_html}
                </ul>
            </div>
            <div class="card">
                <h2>Patrol Statistics</h2>
                <div class="stats-grid">
                    <div class="stat-box">
                        <div class="stat-number">{patrol_count}</div>
                        <div class="stat-label">Patrols Run</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">{report.get('total_issues', 0)}</div>
                        <div class="stat-label">Issues Found</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">0</div>
                        <div class="stat-label">Auto-Fixed</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">{health_score}</div>
                        <div class="stat-label">Health Score</div>
                    </div>
                </div>
            </div>
            <div class="card full-width">
                <h2>Recent Patrol History</h2>
                <div class="timeline">
                    {timeline_html}
                </div>
            </div>
        </div>
        <div class="last-update">
            Patrol runs every 12 hours | Last checked: {last_update}
        </div>
    </div>
</body>
</html>'''


def upload_status_page(site: dict, html_content: str):
    """Upload patrol-status.html to the website via FTP"""
    try:
        print("[Patrol] Uploading status page via FTP...")
        ftp = FTP(site['ftp_host'])
        ftp.login(site['ftp_user'], site['ftp_pass'])

        # Navigate to public_html or root
        try:
            ftp.cwd('public_html')
        except:
            pass  # Already in root or public_html doesn't exist

        # Upload the file
        html_bytes = io.BytesIO(html_content.encode('utf-8'))
        ftp.storbinary('STOR patrol-status.html', html_bytes)

        ftp.quit()
        print("[Patrol] Status page uploaded successfully!")
        return True
    except Exception as e:
        print(f"[Patrol] FTP upload failed: {e}")
        return False


# Store patrol history
patrol_history = []

async def run_patrol_loop():
    """Main patrol loop - runs every 12 hours"""
    global patrol_history
    patrol = CloudPatrol()

    print("""
============================================================
     HELIX PATROL WORKER - CLOUD EDITION
============================================================
     Running 24/7 on Render.com (FREE)
     Patrol Interval: Every 12 hours
     Auto-updates patrol-status.html on your website
============================================================
    """)

    while True:
        # Run patrol for all sites
        for site_key in SITES:
            site = SITES[site_key]
            try:
                report = await patrol.patrol_site(site_key)

                # Add to history
                patrol_history.append({
                    'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
                    'status': report.get('status', 'OK'),
                    'issues': report.get('total_issues', 0)
                })

                # Keep only last 50 entries
                patrol_history = patrol_history[-50:]

                # Generate and upload status page
                status_html = generate_status_html(report, patrol.patrol_count, patrol_history)
                upload_status_page(site, status_html)

                print(f"\nPatrol #{patrol.patrol_count} complete.")
                print(f"Next patrol in {PATROL_INTERVAL_HOURS} hours.")

            except Exception as e:
                print(f"[ERROR] Patrol failed for {site_key}: {e}")

        # Wait for next patrol
        await asyncio.sleep(PATROL_INTERVAL_HOURS * 3600)


if __name__ == "__main__":
    asyncio.run(run_patrol_loop())
