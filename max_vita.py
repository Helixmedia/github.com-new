"""
MAX-VITA - Email Agent for Longevity Futures
==============================================
Dedicated email handler for longevityfutures.online

Responsibilities:
- Receives inbound emails via Resend webhook
- Auto-responds (AR) to customer inquiries
- Sends welcome emails to new subscribers
- Handles failure notifications
- Manages affiliate communications
- MANAGES ALL SUBSCRIBERS for this site

Email: vita@helixmediaengine.com
Site: longevityfutures.online
"""

import resend
import json
import requests
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ===========================================
# CONFIGURATION
# ===========================================

RESEND_API_KEY = "re_EqixYSN6_GdCJxHbgk6nPZkcrKhZERZvG"
resend.api_key = RESEND_API_KEY

# Site-specific config
SITE_CONFIG = {
    "name": "Longevity Futures",
    "domain": "longevityfutures.online",
    "email": "vita@helixmediaengine.com",
    "agent_name": "VITA",
    "color": "#2d5016",
    "topics": ["longevity", "supplements", "anti-aging", "health", "NAD+", "NMN", "resveratrol", "wellness"]
}

# Admin email for alerts
ADMIN_EMAIL = "paul@helixmediaengine.com"


class MaxVita:
    """
    MAX-VITA - Longevity Futures Email Agent
    Handles all email operations AND subscriber management for the longevity site
    """

    def __init__(self):
        self.api_key = RESEND_API_KEY
        self.openai = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.base_url = "https://api.resend.com"
        self.config = SITE_CONFIG

        # Database for subscribers (site-specific)
        self.db_path = os.path.join(os.path.dirname(__file__), "vita_subscribers.db")
        self._init_database()

        print(f"[MAX-VITA] Initialized for {self.config['name']} ({self.config['email']})")
        print(f"[MAX-VITA] Subscriber database: {self.db_path}")

    # ===========================================
    # SUBSCRIBER DATABASE
    # ===========================================

    def _init_database(self):
        """Initialize the subscriber database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Subscribers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscribers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                name TEXT DEFAULT '',
                source TEXT DEFAULT 'website',
                subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active',
                welcome_sent INTEGER DEFAULT 0,
                last_email_at TIMESTAMP,
                email_count INTEGER DEFAULT 0,
                unsubscribed_at TIMESTAMP
            )
        ''')

        # Email log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subscriber_id INTEGER,
                email_type TEXT NOT NULL,
                subject TEXT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'sent',
                FOREIGN KEY (subscriber_id) REFERENCES subscribers (id)
            )
        ''')

        conn.commit()
        conn.close()

    def add_subscriber(self, email: str, name: str = "", source: str = "website") -> Dict:
        """Add a new subscriber to VITA's list"""
        email = email.lower().strip()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Check if already exists
            cursor.execute('SELECT id, status FROM subscribers WHERE email = ?', (email,))
            existing = cursor.fetchone()

            if existing:
                sub_id, status = existing
                if status == 'unsubscribed':
                    # Resubscribe
                    cursor.execute('''
                        UPDATE subscribers
                        SET status = 'active', subscribed_at = ?, name = ?
                        WHERE id = ?
                    ''', (datetime.now().isoformat(), name, sub_id))
                    conn.commit()
                    conn.close()
                    print(f"[MAX-VITA] Resubscribed: {email}")
                    return {"success": True, "id": sub_id, "action": "resubscribed"}
                else:
                    conn.close()
                    return {"success": False, "error": "Already subscribed", "id": sub_id}

            # Add new subscriber
            cursor.execute('''
                INSERT INTO subscribers (email, name, source, subscribed_at)
                VALUES (?, ?, ?, ?)
            ''', (email, name, source, datetime.now().isoformat()))

            sub_id = cursor.lastrowid
            conn.commit()
            conn.close()

            print(f"[MAX-VITA] New subscriber: {email} (ID: {sub_id})")
            return {"success": True, "id": sub_id, "action": "added", "is_new": True}

        except Exception as e:
            conn.close()
            print(f"[MAX-VITA] Error adding subscriber: {e}")
            return {"success": False, "error": str(e)}

    def remove_subscriber(self, email: str = None, subscriber_id: int = None) -> Dict:
        """Remove/unsubscribe a subscriber"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            if subscriber_id:
                cursor.execute('''
                    UPDATE subscribers
                    SET status = 'unsubscribed', unsubscribed_at = ?
                    WHERE id = ?
                ''', (datetime.now().isoformat(), subscriber_id))
            elif email:
                cursor.execute('''
                    UPDATE subscribers
                    SET status = 'unsubscribed', unsubscribed_at = ?
                    WHERE email = ?
                ''', (datetime.now().isoformat(), email.lower().strip()))
            else:
                conn.close()
                return {"success": False, "error": "No email or ID provided"}

            if cursor.rowcount > 0:
                conn.commit()
                conn.close()
                print(f"[MAX-VITA] Unsubscribed: {email or subscriber_id}")
                return {"success": True}
            else:
                conn.close()
                return {"success": False, "error": "Subscriber not found"}

        except Exception as e:
            conn.close()
            return {"success": False, "error": str(e)}

    def get_subscribers(self, status: str = "active") -> List[Dict]:
        """Get all subscribers with given status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if status == "all":
            cursor.execute('SELECT * FROM subscribers ORDER BY subscribed_at DESC')
        else:
            cursor.execute('SELECT * FROM subscribers WHERE status = ? ORDER BY subscribed_at DESC', (status,))

        rows = cursor.fetchall()
        conn.close()

        subscribers = []
        for row in rows:
            subscribers.append({
                "id": row[0],
                "email": row[1],
                "name": row[2],
                "source": row[3],
                "subscribed_at": row[4],
                "status": row[5],
                "welcome_sent": bool(row[6]),
                "last_email_at": row[7],
                "email_count": row[8]
            })

        return subscribers

    def get_subscriber_stats(self) -> Dict:
        """Get subscriber statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Total active
        cursor.execute('SELECT COUNT(*) FROM subscribers WHERE status = "active"')
        total_active = cursor.fetchone()[0]

        # Total unsubscribed
        cursor.execute('SELECT COUNT(*) FROM subscribers WHERE status = "unsubscribed"')
        total_unsubscribed = cursor.fetchone()[0]

        # Today's new subscribers
        today = datetime.now().date().isoformat()
        cursor.execute('SELECT COUNT(*) FROM subscribers WHERE DATE(subscribed_at) = ?', (today,))
        today_count = cursor.fetchone()[0]

        # This week
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        cursor.execute('SELECT COUNT(*) FROM subscribers WHERE subscribed_at >= ?', (week_ago,))
        week_count = cursor.fetchone()[0]

        # Recent subscribers
        cursor.execute('''
            SELECT id, email, name, subscribed_at, source
            FROM subscribers
            WHERE status = "active"
            ORDER BY subscribed_at DESC
            LIMIT 10
        ''')
        recent = cursor.fetchall()

        conn.close()

        return {
            "site": self.config["name"],
            "agent": "MAX-VITA",
            "total_active": total_active,
            "total_unsubscribed": total_unsubscribed,
            "today": today_count,
            "this_week": week_count,
            "recent": [
                {"id": r[0], "email": r[1], "name": r[2], "subscribed_at": r[3], "source": r[4]}
                for r in recent
            ]
        }

    def mark_welcome_sent(self, subscriber_id: int):
        """Mark that welcome email was sent"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE subscribers
            SET welcome_sent = 1, last_email_at = ?, email_count = email_count + 1
            WHERE id = ?
        ''', (datetime.now().isoformat(), subscriber_id))
        conn.commit()
        conn.close()

    def log_email_sent(self, subscriber_id: int, email_type: str, subject: str):
        """Log an email sent to subscriber"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO email_log (subscriber_id, email_type, subject)
            VALUES (?, ?, ?)
        ''', (subscriber_id, email_type, subject))
        cursor.execute('''
            UPDATE subscribers
            SET last_email_at = ?, email_count = email_count + 1
            WHERE id = ?
        ''', (datetime.now().isoformat(), subscriber_id))
        conn.commit()
        conn.close()

    # ===========================================
    # INBOUND EMAIL HANDLING
    # ===========================================

    def handle_inbound_email(self, webhook_data: Dict) -> Dict:
        """
        Process incoming email from Resend webhook

        Args:
            webhook_data: The webhook payload from Resend

        Returns:
            dict with processing result
        """
        try:
            event_type = webhook_data.get("type")

            if event_type != "email.received":
                return {"success": False, "reason": "Not an inbound email event"}

            data = webhook_data.get("data", {})
            email_id = data.get("email_id")
            from_email = data.get("from")
            to_email = data.get("to", [])
            subject = data.get("subject", "No Subject")

            print(f"[MAX-VITA] Received email from {from_email}: {subject}")

            # Fetch the full email content from Resend API
            email_content = self._fetch_email_content(email_id)

            # Generate auto-response using AI
            response = self._generate_auto_response(
                from_email=from_email,
                subject=subject,
                content=email_content
            )

            # Send the auto-response
            if response:
                result = self.send_email(
                    to_email=from_email,
                    subject=f"Re: {subject}",
                    html_content=response
                )

                # Log the interaction
                self._log_email_interaction(from_email, subject, email_content, response)

                return {
                    "success": True,
                    "email_id": email_id,
                    "from": from_email,
                    "response_sent": result.get("success", False)
                }

            return {"success": True, "email_id": email_id, "response_sent": False}

        except Exception as e:
            print(f"[MAX-VITA] Error handling inbound email: {e}")
            self._send_admin_alert("Inbound Email Error", str(e))
            return {"success": False, "error": str(e)}

    def _fetch_email_content(self, email_id: str) -> str:
        """Fetch full email content from Resend API"""
        try:
            response = requests.get(
                f"{self.base_url}/emails/{email_id}",
                headers=self.headers
            )

            if response.status_code == 200:
                data = response.json()
                # Return text or HTML body
                return data.get("text", data.get("html", ""))

        except Exception as e:
            print(f"[MAX-VITA] Error fetching email content: {e}")

        return ""

    def _generate_auto_response(self, from_email: str, subject: str, content: str) -> Optional[str]:
        """
        Generate AI-powered auto-response based on email content

        This is the AR (Auto-Response) system
        """
        try:
            # Build context about what VITA knows
            system_prompt = f"""You are VITA, the friendly AI assistant for Longevity Futures (longevityfutures.online).

Your expertise:
- Evidence-based longevity research
- Supplements: NAD+ precursors (NMN, NR), resveratrol, CoQ10, vitamin D3, K2, omega-3s
- Anti-aging science: cellular health, mitochondria, senolytics
- Healthy aging strategies and lifestyle optimization

Your personality:
- Warm, helpful, and knowledgeable
- Always cite evidence when making claims
- Recommend consulting healthcare providers for medical advice
- Direct people to the website for more articles: https://longevityfutures.online/articles.html

Guidelines for responding:
- Keep responses concise but helpful (2-4 paragraphs)
- If asked about specific products, you can mention them but don't hard-sell
- Always be professional and supportive
- If the question is off-topic, politely redirect to longevity topics
- Sign off as "VITA" from Longevity Futures

Format your response as professional HTML email with proper styling."""

            user_prompt = f"""Someone sent this email to {self.config['email']}:

From: {from_email}
Subject: {subject}

Message:
{content[:2000]}

Please write a helpful, personalized response."""

            response = self.openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )

            ai_response = response.choices[0].message.content

            # Wrap in email template
            html = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333;">
                {ai_response}

                <hr style="border: none; border-top: 1px solid #eee; margin-top: 30px;">
                <p style="color: #999; font-size: 12px;">
                    This is an automated response from VITA, your Longevity Futures guide.<br>
                    Visit us at <a href="https://longevityfutures.online">longevityfutures.online</a><br><br>
                    Helix Media Engine | ABN: 66 926 581 596<br>
                    <a href="https://longevityfutures.online/unsubscribe">Unsubscribe</a>
                </p>
            </body>
            </html>
            """

            return html

        except Exception as e:
            print(f"[MAX-VITA] Error generating auto-response: {e}")
            return None

    def _log_email_interaction(self, from_email: str, subject: str,
                               content: str, response: str):
        """Log email interaction for records"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "from": from_email,
            "subject": subject,
            "content_preview": content[:500] if content else "",
            "response_sent": True
        }

        # Append to log file
        log_file = os.path.join(os.path.dirname(__file__), "email_log.json")
        try:
            if os.path.exists(log_file):
                with open(log_file, "r") as f:
                    logs = json.load(f)
            else:
                logs = []

            logs.append(log_entry)

            # Keep last 1000 entries
            logs = logs[-1000:]

            with open(log_file, "w") as f:
                json.dump(logs, f, indent=2)

        except Exception as e:
            print(f"[MAX-VITA] Error logging interaction: {e}")

    # ===========================================
    # EMAIL SENDING
    # ===========================================

    def send_email(self, to_email: str, subject: str, html_content: str) -> Dict:
        """Send an email from VITA"""
        try:
            params = {
                "from": f"{self.config['agent_name']} - {self.config['name']} <{self.config['email']}>",
                "to": [to_email],
                "subject": subject,
                "html": html_content
            }

            email = resend.Emails.send(params)

            print(f"[MAX-VITA] Email sent to {to_email}")
            return {"success": True, "id": email["id"]}

        except Exception as e:
            print(f"[MAX-VITA] Failed to send email: {str(e)}")
            return {"success": False, "error": str(e)}

    def send_welcome_email(self, to_email: str, subscriber_name: str = "Friend") -> Dict:
        """Welcome email for new Longevity Futures subscribers"""

        subject = "Welcome to Longevity Futures - Your Journey Starts Now"

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h1 style="color: {self.config['color']};">Welcome to Longevity Futures, {subscriber_name}!</h1>

            <p>You've just joined thousands of others on a journey to live longer, healthier lives.</p>

            <h2 style="color: {self.config['color']};">What you'll get:</h2>
            <ul>
                <li>Evidence-based longevity research</li>
                <li>Supplement guides and reviews</li>
                <li>Lifestyle optimization tips</li>
                <li>Latest anti-aging science</li>
            </ul>

            <p><a href="https://{self.config['domain']}/articles.html"
                  style="background: {self.config['color']}; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">
                Browse Our Articles
            </a></p>

            <p style="color: #666; font-size: 14px; margin-top: 30px;">
                Questions? Just reply to this email - I'm here to help!<br>
                - {self.config['agent_name']}, Your Longevity Guide
            </p>

            <hr style="border: none; border-top: 1px solid #eee; margin-top: 30px;">
            <p style="color: #999; font-size: 12px;">
                Helix Media Engine | ABN: 66 926 581 596<br>
                <a href="https://{self.config['domain']}/unsubscribe">Unsubscribe</a>
            </p>
        </body>
        </html>
        """

        return self.send_email(to_email, subject, html)

    # ===========================================
    # NOTIFICATION EMAILS
    # ===========================================

    def _send_admin_alert(self, alert_type: str, details: str):
        """Send alert to admin"""
        subject = f"[MAX-VITA Alert] {alert_type}"

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #dc2626;">MAX-VITA Alert</h2>
            <p><strong>Type:</strong> {alert_type}</p>
            <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>Details:</strong></p>
            <pre style="background: #f5f5f5; padding: 10px; border-radius: 4px;">{details}</pre>
        </body>
        </html>
        """

        self.send_email(ADMIN_EMAIL, subject, html)

    def send_purchase_confirmation(self, to_email: str, product_name: str,
                                   amount: float, order_id: str) -> Dict:
        """Send purchase confirmation"""
        subject = f"Order Confirmed - {product_name}"

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h1 style="color: {self.config['color']};">Thank You for Your Purchase!</h1>

            <div style="background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <p><strong>Order ID:</strong> {order_id}</p>
                <p><strong>Product:</strong> {product_name}</p>
                <p><strong>Amount:</strong> ${amount:.2f}</p>
                <p><strong>Date:</strong> {datetime.now().strftime('%B %d, %Y')}</p>
            </div>

            <p>Your order has been confirmed. If you have any questions, just reply to this email!</p>

            <p style="color: #666; font-size: 14px; margin-top: 30px;">
                - {self.config['agent_name']}, {self.config['name']}
            </p>
        </body>
        </html>
        """

        return self.send_email(to_email, subject, html)

    def send_affiliate_notification(self, to_email: str, product_name: str,
                                    commission: float, order_id: str) -> Dict:
        """Send affiliate commission notification"""
        subject = f"You Earned a Commission! ${commission:.2f}"

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h1 style="color: #059669;">Commission Earned!</h1>

            <div style="background: #f0fdf4; border: 1px solid #86efac; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <p style="font-size: 24px; font-weight: bold; color: #059669; margin: 0;">
                    ${commission:.2f}
                </p>
                <p><strong>Product:</strong> {product_name}</p>
                <p><strong>Order ID:</strong> {order_id}</p>
                <p><strong>Date:</strong> {datetime.now().strftime('%B %d, %Y')}</p>
            </div>

            <p>Someone purchased through your affiliate link. Keep up the great work!</p>

            <p style="color: #666; font-size: 14px; margin-top: 30px;">
                - {self.config['name']} Team
            </p>
        </body>
        </html>
        """

        return self.send_email(to_email, subject, html)

    # ===========================================
    # NEWSLETTER
    # ===========================================

    def send_newsletter(self, email_list: List[str], subject: str, content: str) -> Dict:
        """Send newsletter to subscribers"""
        results = {"sent": 0, "failed": 0, "errors": []}

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            {content}

            <hr style="border: none; border-top: 1px solid #eee; margin-top: 30px;">
            <p style="color: #999; font-size: 12px;">
                Helix Media Engine | ABN: 66 926 581 596<br>
                <a href="https://{self.config['domain']}/unsubscribe">Unsubscribe</a>
            </p>
        </body>
        </html>
        """

        for email in email_list:
            result = self.send_email(email, subject, html)
            if result["success"]:
                results["sent"] += 1
            else:
                results["failed"] += 1
                results["errors"].append({"email": email, "error": result.get("error")})

        print(f"[MAX-VITA] Newsletter sent: {results['sent']} sent, {results['failed']} failed")
        return results


# ===========================================
# SINGLETON INSTANCE
# ===========================================

max_vita = MaxVita()


# ===========================================
# CONVENIENCE FUNCTIONS FOR API
# ===========================================

def handle_inbound_email(webhook_data: Dict) -> Dict:
    """Handle incoming email webhook from Resend"""
    return max_vita.handle_inbound_email(webhook_data)

def send_welcome_email(to_email: str, name: str = "Friend") -> Dict:
    """Send welcome email"""
    return max_vita.send_welcome_email(to_email, name)

def send_email(to_email: str, subject: str, html: str) -> Dict:
    """Send custom email"""
    return max_vita.send_email(to_email, subject, html)

# Subscriber management
def add_subscriber(email: str, name: str = "", source: str = "website") -> Dict:
    """Add a subscriber"""
    return max_vita.add_subscriber(email, name, source)

def remove_subscriber(email: str = None, subscriber_id: int = None) -> Dict:
    """Remove a subscriber"""
    return max_vita.remove_subscriber(email, subscriber_id)

def get_subscribers(status: str = "active") -> List[Dict]:
    """Get all subscribers"""
    return max_vita.get_subscribers(status)

def get_subscriber_stats() -> Dict:
    """Get subscriber stats"""
    return max_vita.get_subscriber_stats()


# ===========================================
# TEST
# ===========================================

if __name__ == "__main__":
    print("=" * 60)
    print("MAX-VITA - Longevity Futures Email Agent")
    print("=" * 60)
    print(f"\nAgent: {SITE_CONFIG['agent_name']}")
    print(f"Email: {SITE_CONFIG['email']}")
    print(f"Site: {SITE_CONFIG['domain']}")
    print("\nCapabilities:")
    print("  - Inbound email handling via Resend webhook")
    print("  - AI-powered auto-responses")
    print("  - Welcome emails for new subscribers")
    print("  - Purchase confirmations")
    print("  - Affiliate notifications")
    print("  - Newsletter sending")
    print("\nReady for operations!")
