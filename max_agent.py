"""
MAX - Master Email Agent for Helix Media Engine
=================================================
Centralizes ALL email operations across all sites and agents.

Responsibilities:
- Welcome emails (VITA, ASTRO, SAGE)
- Failure notifications
- Affiliate commission emails
- Subscriber management via Resend Audiences (persistent storage)
- Email analytics and tracking

Uses Resend Audiences API for persistent contact storage
(Render's ephemeral filesystem can't store local databases)
"""

import resend
import json
import requests
from datetime import datetime
from typing import Optional, List, Dict

# ===========================================
# CONFIGURATION
# ===========================================

RESEND_API_KEY = "re_EqixYSN6_GdCJxHbgk6nPZkcrKhZERZvG"
resend.api_key = RESEND_API_KEY

# Agent configurations
AGENTS = {
    "vita": {
        "email": "vita@helixmediaengine.com",
        "name": "VITA - Longevity Futures",
        "site": "longevityfutures.online",
        "color": "#2d5016"
    },
    "astro": {
        "email": "astro@helixmediaengine.com",
        "name": "ASTRO - Event Followers",
        "site": "eventfollowers.com",
        "color": "#1a237e"
    },
    "sage": {
        "email": "sage@helixmediaengine.com",
        "name": "SAGE - Silent AI",
        "site": "silent-ai.com",
        "color": "#424242"
    },
    "max": {
        "email": "max@helixmediaengine.com",
        "name": "MAX - Helix Email System",
        "site": "helixmediaengine.com",
        "color": "#8b5cf6"
    },
    "support": {
        "email": "support@helixmediaengine.com",
        "name": "Helix Media Engine Support",
        "site": "helixmediaengine.com",
        "color": "#059669"
    }
}

# Resend Audiences IDs (will be created if not exist)
AUDIENCES = {
    "vita": None,  # Will store audience ID
    "astro": None,
    "sage": None,
    "all": None    # Master list
}


class MaxEmailAgent:
    """
    MAX - Master Email Agent
    Handles ALL email operations for Helix Media Engine
    """

    def __init__(self):
        self.api_key = RESEND_API_KEY
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.base_url = "https://api.resend.com"
        self.audiences_enabled = True  # Will be set to False if API key is restricted
        self._init_audiences()
        print(f"[MAX] Initialized - Email sending: ON | Audiences: {'ON' if self.audiences_enabled else 'OFF'}")

    # ===========================================
    # AUDIENCE MANAGEMENT (Persistent Storage)
    # ===========================================

    def _init_audiences(self):
        """Initialize or fetch existing audiences from Resend"""
        try:
            # Get existing audiences
            response = requests.get(
                f"{self.base_url}/audiences",
                headers=self.headers
            )

            if response.status_code == 200:
                existing = response.json().get("data", [])
                for audience in existing:
                    name = audience.get("name", "").lower()
                    if name in AUDIENCES:
                        AUDIENCES[name] = audience.get("id")
                        print(f"[MAX] Found audience: {name} ({audience.get('id')})")

                # Create missing audiences
                for name in ["vita", "astro", "sage", "all"]:
                    if not AUDIENCES.get(name):
                        self._create_audience(name)
            elif response.status_code == 401:
                # API key restricted - audiences not available
                print("[MAX] Audiences API not available (restricted key) - email sending only")
                self.audiences_enabled = False
            else:
                print(f"[MAX] Audiences check failed: {response.status_code}")

        except Exception as e:
            print(f"[MAX] Error initializing audiences: {e}")

    def _create_audience(self, name: str) -> Optional[str]:
        """Create a new audience in Resend"""
        try:
            display_name = f"Helix - {name.upper()}"
            if name == "all":
                display_name = "Helix - All Subscribers"

            response = requests.post(
                f"{self.base_url}/audiences",
                headers=self.headers,
                json={"name": display_name}
            )

            if response.status_code in [200, 201]:
                audience_id = response.json().get("id")
                AUDIENCES[name] = audience_id
                print(f"[MAX] Created audience: {name} ({audience_id})")
                return audience_id
            else:
                print(f"[MAX] Failed to create audience {name}: {response.text}")

        except Exception as e:
            print(f"[MAX] Error creating audience {name}: {e}")

        return None

    def add_contact(self, email: str, agent: str = "all",
                    first_name: str = "", last_name: str = "") -> Dict:
        """
        Add a contact to Resend Audiences (persistent storage)

        Args:
            email: Contact's email address
            agent: Which agent/site they subscribed from (vita, astro, sage, all)
            first_name: Optional first name
            last_name: Optional last name

        Returns:
            dict with success status and contact info
        """
        result = {"success": False, "email": email}

        # Add to specific agent audience
        audience_id = AUDIENCES.get(agent)
        if audience_id:
            try:
                response = requests.post(
                    f"{self.base_url}/audiences/{audience_id}/contacts",
                    headers=self.headers,
                    json={
                        "email": email,
                        "first_name": first_name,
                        "last_name": last_name,
                        "unsubscribed": False
                    }
                )

                if response.status_code in [200, 201]:
                    result["success"] = True
                    result["contact_id"] = response.json().get("id")
                    result["audience"] = agent
                    print(f"[MAX] Added {email} to {agent} audience")
                elif response.status_code == 409:
                    # Already exists - still success
                    result["success"] = True
                    result["message"] = "Contact already exists"
                    print(f"[MAX] {email} already in {agent} audience")
                else:
                    result["error"] = response.text
                    print(f"[MAX] Failed to add {email}: {response.text}")

            except Exception as e:
                result["error"] = str(e)
                print(f"[MAX] Error adding contact: {e}")

        # Also add to master "all" list if not already adding to it
        if agent != "all" and AUDIENCES.get("all"):
            try:
                requests.post(
                    f"{self.base_url}/audiences/{AUDIENCES['all']}/contacts",
                    headers=self.headers,
                    json={
                        "email": email,
                        "first_name": first_name,
                        "last_name": last_name,
                        "unsubscribed": False
                    }
                )
            except:
                pass  # Silent fail for master list

        return result

    def remove_contact(self, email: str, agent: str = None) -> Dict:
        """Remove a contact from audiences"""
        result = {"success": False, "email": email}

        audiences_to_check = [agent] if agent else list(AUDIENCES.keys())

        for aud_name in audiences_to_check:
            audience_id = AUDIENCES.get(aud_name)
            if not audience_id:
                continue

            try:
                # First get the contact ID
                response = requests.get(
                    f"{self.base_url}/audiences/{audience_id}/contacts",
                    headers=self.headers
                )

                if response.status_code == 200:
                    contacts = response.json().get("data", [])
                    for contact in contacts:
                        if contact.get("email", "").lower() == email.lower():
                            contact_id = contact.get("id")
                            # Delete the contact
                            del_response = requests.delete(
                                f"{self.base_url}/audiences/{audience_id}/contacts/{contact_id}",
                                headers=self.headers
                            )
                            if del_response.status_code in [200, 204]:
                                result["success"] = True
                                print(f"[MAX] Removed {email} from {aud_name}")
                            break

            except Exception as e:
                print(f"[MAX] Error removing contact: {e}")

        return result

    def get_contacts(self, agent: str = "all") -> List[Dict]:
        """Get all contacts from an audience"""
        audience_id = AUDIENCES.get(agent)
        if not audience_id:
            return []

        try:
            response = requests.get(
                f"{self.base_url}/audiences/{audience_id}/contacts",
                headers=self.headers
            )

            if response.status_code == 200:
                return response.json().get("data", [])

        except Exception as e:
            print(f"[MAX] Error getting contacts: {e}")

        return []

    def get_stats(self) -> Dict:
        """Get subscriber statistics across all audiences"""
        stats = {
            "total": 0,
            "by_agent": {},
            "timestamp": datetime.now().isoformat()
        }

        for agent_name in ["vita", "astro", "sage", "all"]:
            contacts = self.get_contacts(agent_name)
            count = len(contacts)
            stats["by_agent"][agent_name] = count
            if agent_name != "all":
                stats["total"] += count

        return stats

    # ===========================================
    # EMAIL SENDING
    # ===========================================

    def send_email(self, to_email: str, subject: str, html_content: str,
                   from_agent: str = "support") -> Dict:
        """
        Send an email from any Helix agent

        Args:
            to_email: Recipient email address
            subject: Email subject line
            html_content: HTML body of email
            from_agent: Which agent sends it (vita, astro, sage, max, support)

        Returns:
            dict with success status and email id
        """
        agent = AGENTS.get(from_agent, AGENTS["support"])

        try:
            params = {
                "from": f"{agent['name']} <{agent['email']}>",
                "to": [to_email],
                "subject": subject,
                "html": html_content
            }

            email = resend.Emails.send(params)

            print(f"[MAX] Email sent to {to_email} from {agent['email']}")
            return {"success": True, "id": email["id"], "agent": from_agent}

        except Exception as e:
            print(f"[MAX] Failed to send email: {str(e)}")
            return {"success": False, "error": str(e)}

    def send_bulk_email(self, email_list: List[str], subject: str,
                        html_content: str, from_agent: str = "support") -> Dict:
        """Send same email to multiple recipients"""
        results = {"sent": 0, "failed": 0, "errors": []}

        for email in email_list:
            result = self.send_email(email, subject, html_content, from_agent)
            if result["success"]:
                results["sent"] += 1
            else:
                results["failed"] += 1
                results["errors"].append({"email": email, "error": result.get("error")})

        print(f"[MAX] Bulk send complete: {results['sent']} sent, {results['failed']} failed")
        return results

    # ===========================================
    # WELCOME EMAILS
    # ===========================================

    def send_welcome_vita(self, to_email: str, subscriber_name: str = "Friend") -> Dict:
        """Welcome email for Longevity Futures subscribers"""

        subject = "Welcome to Longevity Futures - Your Journey Starts Now"

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h1 style="color: #2d5016;">Welcome to Longevity Futures, {subscriber_name}!</h1>

            <p>You've just joined thousands of others on a journey to live longer, healthier lives.</p>

            <h2 style="color: #2d5016;">What you'll get:</h2>
            <ul>
                <li>Evidence-based longevity research</li>
                <li>Supplement guides and reviews</li>
                <li>Lifestyle optimization tips</li>
                <li>Latest anti-aging science</li>
            </ul>

            <p><a href="https://longevityfutures.online/articles.html"
                  style="background: #2d5016; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">
                Browse Our Articles
            </a></p>

            <p style="color: #666; font-size: 14px; margin-top: 30px;">
                Questions? Just reply to this email.<br>
                - VITA, Your Longevity Guide
            </p>

            <hr style="border: none; border-top: 1px solid #eee; margin-top: 30px;">
            <p style="color: #999; font-size: 12px;">
                Helix Media Engine | ABN: 66 926 581 596<br>
                <a href="https://longevityfutures.online/unsubscribe">Unsubscribe</a>
            </p>
        </body>
        </html>
        """

        # Add to Resend Audiences for persistent storage
        self.add_contact(to_email, "vita", first_name=subscriber_name)

        return self.send_email(to_email, subject, html, "vita")

    def send_welcome_astro(self, to_email: str, subscriber_name: str = "Explorer") -> Dict:
        """Welcome email for Event Followers subscribers"""

        subject = "Welcome to Event Followers - Never Miss a Moment"

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h1 style="color: #1a237e;">Welcome aboard, {subscriber_name}!</h1>

            <p>You're now tracking the most exciting events in the universe.</p>

            <h2 style="color: #1a237e;">What's coming up:</h2>
            <ul>
                <li>Asteroid passes and space events</li>
                <li>Rocket launches</li>
                <li>Eclipses and lunar events</li>
                <li>Custom countdown timers</li>
            </ul>

            <p><a href="https://eventfollowers.com"
                  style="background: #1a237e; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">
                View Live Countdowns
            </a></p>

            <p style="color: #666; font-size: 14px; margin-top: 30px;">
                Keep looking up!<br>
                - ASTRO, Your Event Tracker
            </p>

            <hr style="border: none; border-top: 1px solid #eee; margin-top: 30px;">
            <p style="color: #999; font-size: 12px;">
                Helix Media Engine | ABN: 66 926 581 596<br>
                <a href="https://eventfollowers.com/unsubscribe">Unsubscribe</a>
            </p>
        </body>
        </html>
        """

        # Add to Resend Audiences for persistent storage
        self.add_contact(to_email, "astro", first_name=subscriber_name)

        return self.send_email(to_email, subject, html, "astro")

    def send_welcome_sage(self, to_email: str, subscriber_name: str = "Friend") -> Dict:
        """Welcome email for Silent AI subscribers"""

        subject = "Welcome to Silent AI"

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h1 style="color: #424242;">Welcome, {subscriber_name}</h1>

            <p>You're now part of Silent AI.</p>

            <p>More details coming soon.</p>

            <p style="color: #666; font-size: 14px; margin-top: 30px;">
                - SAGE
            </p>

            <hr style="border: none; border-top: 1px solid #eee; margin-top: 30px;">
            <p style="color: #999; font-size: 12px;">
                Helix Media Engine | ABN: 66 926 581 596<br>
                <a href="https://silent-ai.com/unsubscribe">Unsubscribe</a>
            </p>
        </body>
        </html>
        """

        # Add to Resend Audiences for persistent storage
        self.add_contact(to_email, "sage", first_name=subscriber_name)

        return self.send_email(to_email, subject, html, "sage")

    # ===========================================
    # TRANSACTIONAL EMAILS
    # ===========================================

    def send_purchase_confirmation(self, to_email: str, product_name: str,
                                   amount: float, order_id: str) -> Dict:
        """Send purchase confirmation email"""

        subject = f"Order Confirmed - {product_name}"

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h1 style="color: #2d5016;">Thank You for Your Purchase!</h1>

            <div style="background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <p><strong>Order ID:</strong> {order_id}</p>
                <p><strong>Product:</strong> {product_name}</p>
                <p><strong>Amount:</strong> ${amount:.2f}</p>
                <p><strong>Date:</strong> {datetime.now().strftime('%B %d, %Y')}</p>
            </div>

            <p>Your order has been confirmed and you'll receive access shortly.</p>

            <p style="color: #666; font-size: 14px; margin-top: 30px;">
                Questions? Reply to this email.<br>
                - Helix Media Engine Team
            </p>
        </body>
        </html>
        """

        return self.send_email(to_email, subject, html, "support")

    def send_subscription_confirmation(self, to_email: str, plan_name: str,
                                       amount: float, site: str = "Event Followers") -> Dict:
        """Send subscription confirmation email"""

        subject = f"Subscription Activated - {plan_name}"

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h1 style="color: #1a237e;">Subscription Confirmed!</h1>

            <div style="background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <p><strong>Plan:</strong> {plan_name}</p>
                <p><strong>Amount:</strong> ${amount:.2f}</p>
                <p><strong>Site:</strong> {site}</p>
                <p><strong>Started:</strong> {datetime.now().strftime('%B %d, %Y')}</p>
            </div>

            <p>You now have full access to all premium features!</p>

            <p style="color: #666; font-size: 14px; margin-top: 30px;">
                Manage your subscription anytime.<br>
                - Helix Media Engine Team
            </p>
        </body>
        </html>
        """

        agent = "astro" if "Event" in site else "vita"
        return self.send_email(to_email, subject, html, agent)

    # ===========================================
    # FAILURE NOTIFICATIONS
    # ===========================================

    def send_failure_alert(self, admin_email: str, failure_type: str,
                          details: str, site: str = "Helix") -> Dict:
        """Send failure notification to admin"""

        subject = f"[ALERT] {failure_type} - {site}"

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h1 style="color: #dc2626;">System Alert</h1>

            <div style="background: #fef2f2; border: 1px solid #fecaca; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <p><strong>Type:</strong> {failure_type}</p>
                <p><strong>Site:</strong> {site}</p>
                <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p><strong>Details:</strong></p>
                <pre style="background: #fff; padding: 10px; border-radius: 4px; overflow-x: auto;">{details}</pre>
            </div>

            <p style="color: #666; font-size: 14px;">
                - MAX, Helix Email System
            </p>
        </body>
        </html>
        """

        return self.send_email(admin_email, subject, html, "max")

    # ===========================================
    # AFFILIATE EMAILS
    # ===========================================

    def send_affiliate_commission(self, to_email: str, product_name: str,
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

            <p>Congratulations! Someone purchased through your affiliate link.</p>

            <p style="color: #666; font-size: 14px; margin-top: 30px;">
                - Helix Media Engine
            </p>
        </body>
        </html>
        """

        return self.send_email(to_email, subject, html, "support")

    # ===========================================
    # NEWSLETTER
    # ===========================================

    def send_newsletter(self, agent: str, subject: str, content: str) -> Dict:
        """
        Send newsletter to all subscribers of an agent

        Args:
            agent: Which agent's subscribers (vita, astro, sage, all)
            subject: Newsletter subject
            content: HTML content (body only, wrapper added)
        """
        contacts = self.get_contacts(agent)

        if not contacts:
            return {"success": False, "error": "No subscribers found"}

        agent_config = AGENTS.get(agent, AGENTS["support"])

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            {content}

            <hr style="border: none; border-top: 1px solid #eee; margin-top: 30px;">
            <p style="color: #999; font-size: 12px;">
                Helix Media Engine | ABN: 66 926 581 596<br>
                <a href="https://{agent_config['site']}/unsubscribe">Unsubscribe</a>
            </p>
        </body>
        </html>
        """

        email_list = [c.get("email") for c in contacts if c.get("email")]
        return self.send_bulk_email(email_list, subject, html, agent)


# ===========================================
# SINGLETON INSTANCE
# ===========================================

max_agent = MaxEmailAgent()


# ===========================================
# CONVENIENCE FUNCTIONS
# ===========================================

def send_welcome_email(email: str, agent: str = "vita", name: str = "Friend") -> Dict:
    """Send welcome email for any agent"""
    if agent == "vita":
        return max_agent.send_welcome_vita(email, name)
    elif agent == "astro":
        return max_agent.send_welcome_astro(email, name)
    elif agent == "sage":
        return max_agent.send_welcome_sage(email, name)
    else:
        return max_agent.send_welcome_vita(email, name)


def add_subscriber(email: str, agent: str = "all", name: str = "") -> Dict:
    """Add subscriber to Resend Audiences"""
    return max_agent.add_contact(email, agent, first_name=name)


def remove_subscriber(email: str, agent: str = None) -> Dict:
    """Remove subscriber from Resend Audiences"""
    return max_agent.remove_contact(email, agent)


def get_subscriber_stats() -> Dict:
    """Get subscriber statistics"""
    return max_agent.get_stats()


def send_email(to: str, subject: str, html: str, from_agent: str = "support") -> Dict:
    """Send email from any agent"""
    return max_agent.send_email(to, subject, html, from_agent)


def send_failure_alert(details: str, failure_type: str = "Error", site: str = "Helix") -> Dict:
    """Send failure alert to admin"""
    return max_agent.send_failure_alert(
        "paul@helixmediaengine.com",
        failure_type,
        details,
        site
    )


# ===========================================
# TEST / DEMO
# ===========================================

if __name__ == "__main__":
    print("=" * 60)
    print("MAX - Master Email Agent")
    print("Helix Media Engine - Centralized Email System")
    print("=" * 60)

    print("\nAvailable agents:")
    for key, agent in AGENTS.items():
        print(f"  - {key}: {agent['email']}")

    print("\n" + "=" * 60)
    print("Checking Resend Audiences...")
    print("=" * 60)

    stats = max_agent.get_stats()
    print(f"\nSubscriber Stats:")
    for agent, count in stats["by_agent"].items():
        print(f"  - {agent}: {count} subscribers")

    print("\n" + "=" * 60)
    print("Ready for operations!")
    print("=" * 60)

    print("\nExample usage:")
    print("  from max_agent import send_welcome_email, add_subscriber")
    print("  send_welcome_email('user@email.com', 'vita', 'UserName')")
    print("  add_subscriber('user@email.com', 'vita', 'UserName')")
