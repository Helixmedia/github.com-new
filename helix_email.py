"""
HELIX MEDIA ENGINE - Email System
Central email system for all agents and sites
Uses Resend API
"""

import resend
import json
from datetime import datetime

# ===========================================
# CONFIGURATION
# ===========================================

resend.api_key = "re_EqixYSN6_GdCJxHbgk6nPZkcrKhZERZvG"

# Agent email addresses
AGENTS = {
    "vita": {
        "email": "vita@helixmediaengine.com",
        "name": "VITA - Longevity Futures",
        "site": "longevityfutures.online"
    },
    "astro": {
        "email": "astro@helixmediaengine.com",
        "name": "ASTRO - Event Followers",
        "site": "eventfollowers.com"
    },
    "sage": {
        "email": "sage@helixmediaengine.com",
        "name": "SAGE - Silent AI",
        "site": "silent-ai.com"
    },
    "support": {
        "email": "support@helixmediaengine.com",
        "name": "Helix Media Engine Support",
        "site": "helixmediaengine.com"
    }
}

# ===========================================
# CORE EMAIL FUNCTIONS
# ===========================================

def send_email(to_email, subject, html_content, from_agent="support"):
    """
    Send an email from any Helix agent

    Args:
        to_email: Recipient email address
        subject: Email subject line
        html_content: HTML body of email
        from_agent: Which agent sends it (vita, astro, sage, support)

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

        print(f"[OK] Email sent to {to_email} from {agent['email']}")
        return {"success": True, "id": email["id"]}

    except Exception as e:
        print(f"[ERROR] Failed to send email: {str(e)}")
        return {"success": False, "error": str(e)}


def send_bulk_email(email_list, subject, html_content, from_agent="support"):
    """
    Send same email to multiple recipients

    Args:
        email_list: List of email addresses
        subject: Email subject line
        html_content: HTML body of email
        from_agent: Which agent sends it

    Returns:
        dict with success count and failures
    """
    results = {"sent": 0, "failed": 0, "errors": []}

    for email in email_list:
        result = send_email(email, subject, html_content, from_agent)
        if result["success"]:
            results["sent"] += 1
        else:
            results["failed"] += 1
            results["errors"].append({"email": email, "error": result["error"]})

    print(f"\nBulk send complete: {results['sent']} sent, {results['failed']} failed")
    return results


# ===========================================
# WELCOME EMAILS
# ===========================================

def send_welcome_vita(to_email, subscriber_name="Friend"):
    """Welcome email for Longevity Futures subscribers"""

    subject = "Welcome to Longevity Futures - Your Journey Starts Now"

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h1 style="color: #2d5016;">Welcome to Longevity Futures, {subscriber_name}!</h1>

        <p>You've just joined thousands of others on a journey to live longer, healthier lives.</p>

        <h2 style="color: #2d5016;">What you'll get:</h2>
        <ul>
            <li>🧬 Evidence-based longevity research</li>
            <li>💊 Supplement guides and reviews</li>
            <li>🏃 Lifestyle optimization tips</li>
            <li>📊 Latest anti-aging science</li>
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

    return send_email(to_email, subject, html, "vita")


def send_welcome_astro(to_email, subscriber_name="Explorer"):
    """Welcome email for Event Followers subscribers"""

    subject = "Welcome to Event Followers - Never Miss a Moment"

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h1 style="color: #1a237e;">Welcome aboard, {subscriber_name}!</h1>

        <p>You're now tracking the most exciting events in the universe.</p>

        <h2 style="color: #1a237e;">What's coming up:</h2>
        <ul>
            <li>🌠 Asteroid passes and space events</li>
            <li>🚀 Rocket launches</li>
            <li>🌙 Eclipses and lunar events</li>
            <li>⏰ Custom countdown timers</li>
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

    return send_email(to_email, subject, html, "astro")


def send_welcome_sage(to_email, subscriber_name="Friend"):
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

    return send_email(to_email, subject, html, "sage")


# ===========================================
# NEWSLETTER FUNCTIONS
# ===========================================

def send_newsletter(email_list, subject, content, from_agent="support"):
    """
    Send a newsletter to a list of subscribers

    Args:
        email_list: List of subscriber emails
        subject: Newsletter subject
        content: HTML content (just the body, wrapper added automatically)
        from_agent: Which agent sends it
    """

    agent = AGENTS.get(from_agent, AGENTS["support"])

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        {content}

        <hr style="border: none; border-top: 1px solid #eee; margin-top: 30px;">
        <p style="color: #999; font-size: 12px;">
            Helix Media Engine | ABN: 66 926 581 596<br>
            <a href="https://{agent['site']}/unsubscribe">Unsubscribe</a>
        </p>
    </body>
    </html>
    """

    return send_bulk_email(email_list, subject, html, from_agent)


# ===========================================
# TRANSACTIONAL EMAILS
# ===========================================

def send_purchase_confirmation(to_email, product_name, amount, order_id):
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

    return send_email(to_email, subject, html, "support")


def send_subscription_confirmation(to_email, plan_name, amount, site="Event Followers"):
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
    return send_email(to_email, subject, html, agent)


# ===========================================
# SUBSCRIBER MANAGEMENT (Enhanced JSON file with IDs & timestamps)
# ===========================================

import os
SUBSCRIBERS_FILE = os.path.join(os.path.dirname(__file__), "subscribers.json")

def load_subscribers():
    """Load subscribers from JSON file - enhanced format with IDs"""
    try:
        with open(SUBSCRIBERS_FILE, "r") as f:
            data = json.load(f)
            # Migration: convert old format to new if needed
            if isinstance(data.get("vita"), list) and len(data.get("vita", [])) > 0 and isinstance(data["vita"][0], str):
                # Old format detected, migrate
                return _migrate_subscribers(data)
            return data
    except FileNotFoundError:
        return {"subscribers": [], "next_id": 1}

def _migrate_subscribers(old_data):
    """Migrate old simple list format to new format with IDs"""
    new_data = {"subscribers": [], "next_id": 1}
    seen_emails = set()

    for agent in ["vita", "astro", "sage", "all"]:
        for email in old_data.get(agent, []):
            if email not in seen_emails:
                seen_emails.add(email)
                new_data["subscribers"].append({
                    "id": new_data["next_id"],
                    "email": email,
                    "agent": agent,
                    "subscribed_at": datetime.now().isoformat(),
                    "name": ""
                })
                new_data["next_id"] += 1

    save_subscribers(new_data)
    return new_data

def save_subscribers(data):
    """Save subscribers to JSON file"""
    with open(SUBSCRIBERS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def add_subscriber(email, agent="all", name=""):
    """Add a new subscriber with ID and timestamp"""
    data = load_subscribers()

    # Check if already exists
    for sub in data["subscribers"]:
        if sub["email"].lower() == email.lower():
            print(f"Already subscribed: {email}")
            return False

    # Add new subscriber
    new_sub = {
        "id": data["next_id"],
        "email": email,
        "agent": agent,
        "subscribed_at": datetime.now().isoformat(),
        "name": name
    }
    data["subscribers"].append(new_sub)
    data["next_id"] += 1
    save_subscribers(data)
    print(f"[OK] Added {email} to {agent} list (ID: {new_sub['id']})")
    return True

def remove_subscriber(email=None, subscriber_id=None, agent=None):
    """Remove a subscriber by email or ID"""
    data = load_subscribers()

    for i, sub in enumerate(data["subscribers"]):
        if (subscriber_id and sub["id"] == subscriber_id) or \
           (email and sub["email"].lower() == email.lower()):
            removed = data["subscribers"].pop(i)
            save_subscribers(data)
            print(f"[OK] Removed {removed['email']} (ID: {removed['id']})")
            return True
    return False

def get_subscribers(agent=None):
    """Get list of subscribers, optionally filtered by agent"""
    data = load_subscribers()
    if agent and agent != "all":
        return [s for s in data["subscribers"] if s["agent"] == agent]
    return data["subscribers"]

def get_subscriber_stats():
    """Get subscriber statistics for dashboard"""
    data = load_subscribers()
    subs = data["subscribers"]

    now = datetime.now()
    today = now.date()
    week_ago = now - timedelta(days=7)

    today_count = 0
    week_count = 0

    for sub in subs:
        sub_date = datetime.fromisoformat(sub["subscribed_at"])
        if sub_date.date() == today:
            today_count += 1
        if sub_date >= week_ago:
            week_count += 1

    return {
        "total_subscribers": len(subs),
        "today": today_count,
        "this_week": week_count,
        "subscribers": sorted(subs, key=lambda x: x["subscribed_at"], reverse=True)
    }

# Import timedelta for stats
from datetime import timedelta


# ===========================================
# TEST / DEMO
# ===========================================

if __name__ == "__main__":
    print("=" * 50)
    print("HELIX MEDIA ENGINE - Email System")
    print("=" * 50)
    print("\nAvailable agents:")
    for key, agent in AGENTS.items():
        print(f"  • {key}: {agent['email']}")

    print("\n" + "=" * 50)
    print("TEST MODE")
    print("=" * 50)

    # Uncomment to test:
    # send_welcome_vita("test@example.com", "Paul")
    # send_welcome_astro("test@example.com", "Paul")

    print("\nTo test, uncomment the test lines in the script")
    print("or import and use in your code:")
    print("")
    print("  from helix_email import send_welcome_vita")
    print("  send_welcome_vita('user@email.com', 'UserName')")
