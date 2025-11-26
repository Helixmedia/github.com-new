"""
Email Notification System
Sends alerts when users subscribe, upgrade, or hit limits
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

class EmailNotifier:
    def __init__(self):
        # Email configuration from .env
        self.from_email = os.getenv('NOTIFICATION_EMAIL', '')
        self.from_password = os.getenv('NOTIFICATION_PASSWORD', '')
        self.to_email = os.getenv('ALERT_EMAIL', self.from_email)
        self.enabled = bool(self.from_email and self.from_password)

        if not self.enabled:
            print("[WARNING] Email notifications not configured. Set NOTIFICATION_EMAIL and NOTIFICATION_PASSWORD in .env")

    def send_email(self, subject, body_html):
        """Send an email notification"""
        if not self.enabled:
            print(f"[NOTIFICATION DISABLED] Would have sent: {subject}")
            return False

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.from_email
            msg['To'] = self.to_email
            msg['Subject'] = subject

            # Add HTML body
            html_part = MIMEText(body_html, 'html')
            msg.attach(html_part)

            # Send via Gmail SMTP
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(self.from_email, self.from_password)
                server.send_message(msg)

            print(f"[OK] Email sent: {subject}")
            return True

        except Exception as e:
            print(f"[ERROR] Failed to send email: {str(e)}")
            return False

    def notify_new_subscription(self, email, tier, amount_paid):
        """Send notification when someone subscribes"""
        subject = f"💰 New {tier.upper()} Subscription - ${amount_paid}"

        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <div style="background: #4CAF50; color: white; padding: 20px; border-radius: 5px;">
                <h2 style="margin: 0;">🎉 New Subscription!</h2>
            </div>

            <div style="padding: 20px; background: #f9f9f9; margin-top: 20px; border-radius: 5px;">
                <h3 style="color: #333;">Subscription Details:</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;"><strong>Plan:</strong></td>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;">{tier.upper()}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;"><strong>Customer Email:</strong></td>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;">{email}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;"><strong>Amount:</strong></td>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd; color: #4CAF50; font-size: 18px;"><strong>${amount_paid:.2f}</strong></td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;"><strong>Time:</strong></td>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;">{datetime.now().strftime('%B %d, %Y at %I:%M %p')}</td>
                    </tr>
                </table>
            </div>

            <div style="padding: 20px; margin-top: 20px; background: #fff3cd; border-left: 4px solid #ffc107; border-radius: 5px;">
                <p style="margin: 0; color: #856404;">
                    <strong>💡 Quick Stats:</strong><br>
                    Check your Stripe dashboard for full details:<br>
                    <a href="https://dashboard.stripe.com/subscriptions" style="color: #007bff;">View Subscriptions</a>
                </p>
            </div>

            <div style="margin-top: 30px; padding: 20px; text-align: center; color: #666; font-size: 12px;">
                <p>Helix Media Engine - AI Agent Subscriptions</p>
                <p>This is an automated notification from your payment system.</p>
            </div>
        </body>
        </html>
        """

        return self.send_email(subject, body)

    def notify_free_limit_reached(self, email, questions_asked):
        """Send notification when user hits free limit (potential conversion!)"""
        subject = f"🎯 Free User Hit Limit - Potential Conversion: {email}"

        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <div style="background: #ff9800; color: white; padding: 20px; border-radius: 5px;">
                <h2 style="margin: 0;">🎯 Potential Paying Customer!</h2>
            </div>

            <div style="padding: 20px; background: #f9f9f9; margin-top: 20px; border-radius: 5px;">
                <h3 style="color: #333;">User Details:</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;"><strong>Email:</strong></td>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;">{email}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;"><strong>Questions Used:</strong></td>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;">{questions_asked}/3 (FREE LIMIT)</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;"><strong>Status:</strong></td>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd; color: #ff9800;"><strong>Shown Upgrade Options</strong></td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;"><strong>Time:</strong></td>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;">{datetime.now().strftime('%B %d, %Y at %I:%M %p')}</td>
                    </tr>
                </table>
            </div>

            <div style="padding: 20px; margin-top: 20px; background: #e8f5e9; border-left: 4px solid #4CAF50; border-radius: 5px;">
                <p style="margin: 0; color: #2e7d32;">
                    <strong>💰 Conversion Opportunity:</strong><br>
                    This user engaged enough to use all 3 free questions!<br>
                    They're seeing upgrade options now.<br>
                    Watch for a subscription notification next!
                </p>
            </div>

            <div style="margin-top: 30px; padding: 20px; text-align: center; color: #666; font-size: 12px;">
                <p>Helix Media Engine - User Activity Alert</p>
            </div>
        </body>
        </html>
        """

        return self.send_email(subject, body)

    def notify_subscription_cancelled(self, email, tier):
        """Send notification when someone cancels"""
        subject = f"⚠️ Subscription Cancelled - {tier.upper()}: {email}"

        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <div style="background: #f44336; color: white; padding: 20px; border-radius: 5px;">
                <h2 style="margin: 0;">⚠️ Subscription Cancelled</h2>
            </div>

            <div style="padding: 20px; background: #f9f9f9; margin-top: 20px; border-radius: 5px;">
                <h3 style="color: #333;">Cancellation Details:</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;"><strong>Plan:</strong></td>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;">{tier.upper()}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;"><strong>Customer Email:</strong></td>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;">{email}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;"><strong>Time:</strong></td>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;">{datetime.now().strftime('%B %d, %Y at %I:%M %p')}</td>
                    </tr>
                </table>
            </div>

            <div style="padding: 20px; margin-top: 20px; background: #fff3cd; border-left: 4px solid #ffc107; border-radius: 5px;">
                <p style="margin: 0; color: #856404;">
                    <strong>💡 Action Items:</strong><br>
                    Consider reaching out to understand why they cancelled.<br>
                    Check Stripe for full details.
                </p>
            </div>

            <div style="margin-top: 30px; padding: 20px; text-align: center; color: #666; font-size: 12px;">
                <p>Helix Media Engine - Cancellation Alert</p>
            </div>
        </body>
        </html>
        """

        return self.send_email(subject, body)


# Test function
if __name__ == "__main__":
    print("\n" + "="*70)
    print("EMAIL NOTIFICATION SYSTEM TEST")
    print("="*70)

    notifier = EmailNotifier()

    if not notifier.enabled:
        print("\n[!] Email not configured. To enable notifications:")
        print("\n1. Open .env file")
        print("2. Add these lines:\n")
        print("   NOTIFICATION_EMAIL=your-email@gmail.com")
        print("   NOTIFICATION_PASSWORD=your-app-password")
        print("   ALERT_EMAIL=where-to-send-alerts@gmail.com")
        print("\n3. For Gmail, create an App Password:")
        print("   https://myaccount.google.com/apppasswords")
        print("\n" + "="*70)
    else:
        print("\n[OK] Email configured!")
        print(f"From: {notifier.from_email}")
        print(f"To: {notifier.to_email}")
        print("\nSending test notification...")

        # Send test
        notifier.notify_new_subscription(
            email="test@example.com",
            tier="basic",
            amount_paid=1.99
        )

        print("\n" + "="*70)
        print("Check your email!")
        print("="*70)
