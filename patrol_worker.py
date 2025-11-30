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


async def run_patrol_loop():
    """Main patrol loop - runs every 12 hours"""
    patrol = CloudPatrol()

    print("""
============================================================
     HELIX PATROL WORKER - CLOUD EDITION
============================================================
     Running 24/7 on Render.com (FREE)
     Patrol Interval: Every 12 hours
============================================================
    """)

    while True:
        # Run patrol for all sites
        for site_key in SITES:
            try:
                report = await patrol.patrol_site(site_key)

                # Save report (could send to webhook, email, etc.)
                print(f"\nPatrol #{patrol.patrol_count} complete.")
                print(f"Next patrol in {PATROL_INTERVAL_HOURS} hours.")

            except Exception as e:
                print(f"[ERROR] Patrol failed for {site_key}: {e}")

        # Wait for next patrol
        await asyncio.sleep(PATROL_INTERVAL_HOURS * 3600)


if __name__ == "__main__":
    asyncio.run(run_patrol_loop())
