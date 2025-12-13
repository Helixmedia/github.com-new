"""
WEEKLY NEWSLETTER AGENT - Event Followers
==========================================
Sends weekly newsletter to all subscribers every Sunday at 10am.
Run this as a cron job or scheduled task.
"""

import resend
import requests
from datetime import datetime
from max_agent import max_agent, AGENTS

RESEND_API_KEY = "re_EqixYSN6_GdCJxHbgk6nPZkcrKhZERZvG"
resend.api_key = RESEND_API_KEY


def get_all_subscribers():
    """Get all Event Followers subscribers"""
    try:
        contacts = max_agent.get_contacts("astro")
        emails = [c.get("email") for c in contacts if c.get("email")]
        print(f"[NEWSLETTER] Found {len(emails)} subscribers")
        return emails
    except Exception as e:
        print(f"[NEWSLETTER] Error getting subscribers: {e}")
        return []


def generate_newsletter():
    """Generate this week's newsletter content"""

    today = datetime.now()
    week_of = today.strftime("%B %d, %Y")

    newsletter = {
        "subject": f"Event Followers Weekly - {week_of}",
        "html": f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0a0a0f;">
    <div style="max-width: 600px; margin: 0 auto; background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 100%);">

        <!-- HEADER -->
        <div style="background: linear-gradient(135deg, #1a1a2e 0%, #0d0d1a 100%); padding: 40px 20px; text-align: center; border-bottom: 3px solid #00ff88;">
            <h1 style="font-size: 28px; margin: 0; color: #00ff88; letter-spacing: 3px;">
                EVENT FOLLOWERS
            </h1>
            <p style="color: #888; font-size: 14px; margin-top: 8px; letter-spacing: 2px;">
                WEEKLY UPDATE
            </p>
        </div>

        <!-- INTRO -->
        <div style="padding: 30px; text-align: center;">
            <p style="color: #888; font-size: 16px; line-height: 1.6;">
                Week of <strong style="color: #00ff88;">{week_of}</strong>
            </p>
            <p style="color: #b0b0b0; font-size: 15px; line-height: 1.8; margin-top: 15px;">
                Here's what's happening this week.
            </p>
        </div>

        <!-- CONTENT -->
        <div style="background: rgba(0, 255, 136, 0.1); border-left: 3px solid #00ff88; margin: 20px; padding: 20px;">
            <h2 style="color: #00ff88; font-size: 18px; margin: 0 0 15px 0;">
                This Week's Highlights
            </h2>
            <ul style="color: #b0b0b0; font-size: 14px; line-height: 2; padding-left: 20px;">
                <li>New content added to the site</li>
                <li>Chat rooms are active</li>
                <li>Check out the latest discussions</li>
            </ul>
        </div>

        <!-- CTA -->
        <div style="padding: 30px; text-align: center;">
            <a href="https://eventfollowers.com"
               style="display: inline-block; background: linear-gradient(135deg, #00ff88, #00aa55); color: #000; padding: 15px 40px; text-decoration: none; border-radius: 25px; font-weight: bold; font-size: 14px; letter-spacing: 1px;">
                VISIT EVENT FOLLOWERS
            </a>
        </div>

        <!-- FOOTER -->
        <div style="background: #050508; padding: 25px; text-align: center;">
            <p style="color: #555; font-size: 12px; margin: 0;">
                Event Followers | Helix Media Engine | ABN: 66 926 581 596
            </p>
            <p style="margin: 10px 0 0 0;">
                <a href="https://eventfollowers.com" style="color: #888; font-size: 12px; text-decoration: none;">eventfollowers.com</a>
            </p>
            <p style="margin: 15px 0 0 0;">
                <a href="https://eventfollowers.com/unsubscribe" style="color: #666; font-size: 11px; text-decoration: underline;">Unsubscribe</a>
            </p>
        </div>

    </div>
</body>
</html>
"""
    }

    return newsletter


def send_newsletter():
    """Send newsletter to all subscribers"""

    subscribers = get_all_subscribers()

    if not subscribers:
        print("[NEWSLETTER] No subscribers found - skipping")
        return {"sent": 0, "failed": 0}

    newsletter = generate_newsletter()

    results = {"sent": 0, "failed": 0, "errors": []}

    for email in subscribers:
        try:
            result = max_agent.send_email(
                email,
                newsletter["subject"],
                newsletter["html"],
                "astro"
            )

            if result.get("success"):
                results["sent"] += 1
                print(f"[NEWSLETTER] Sent to {email}")
            else:
                results["failed"] += 1
                results["errors"].append({"email": email, "error": result.get("error")})

        except Exception as e:
            results["failed"] += 1
            results["errors"].append({"email": email, "error": str(e)})

    print(f"[NEWSLETTER] Complete: {results['sent']} sent, {results['failed']} failed")
    return results


def send_test_newsletter(test_email: str):
    """Send test newsletter to a single email"""
    newsletter = generate_newsletter()

    result = max_agent.send_email(
        test_email,
        f"[TEST] {newsletter['subject']}",
        newsletter["html"],
        "astro"
    )

    print(f"[NEWSLETTER] Test sent to {test_email}: {result}")
    return result


if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("EVENT FOLLOWERS WEEKLY NEWSLETTER")
    print("=" * 60)

    if len(sys.argv) > 1:
        if sys.argv[1] == "test" and len(sys.argv) > 2:
            # Send test to specific email
            test_email = sys.argv[2]
            print(f"\nSending TEST newsletter to: {test_email}")
            send_test_newsletter(test_email)
        elif sys.argv[1] == "send":
            # Send to all subscribers
            print("\nSending newsletter to ALL subscribers...")
            results = send_newsletter()
            print(f"\nResults: {results['sent']} sent, {results['failed']} failed")
    else:
        print("\nUsage:")
        print("  python newsletter_agent.py test your@email.com  - Send test")
        print("  python newsletter_agent.py send                  - Send to all")
