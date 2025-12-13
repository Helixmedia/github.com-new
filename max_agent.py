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

    def send_lead_magnet_sequence(self, to_email: str, source: str = "unknown") -> Dict:
        """
        Send 10 emails immediately when someone gives their email for a lead magnet.
        This is the VALUE they get for giving us their email address.
        """
        results = {"sent": 0, "failed": 0}

        # Clean up source name for display
        source_name = source.replace('lead-', '').replace('-', ' ').title()

        # 10 EMAIL SEQUENCE - All sent immediately
        emails = [
            {
                "subject": f"Your {source_name} is Ready!",
                "body": f"""
                <h1 style="color: #ffd700;">Thanks for downloading!</h1>
                <p>You requested: <strong>{source_name}</strong></p>
                <p>The content is already on the page where you signed up - just scroll down!</p>
                <p>But that's just the beginning. Over the next few minutes, you'll receive 9 more emails packed with exclusive content.</p>
                <p style="color: #00d4ff;"><strong>Email 1 of 10</strong></p>
                """
            },
            {
                "subject": "The Truth About UFO Sightings in 2024",
                "body": """
                <h1 style="color: #00ff88;">UFO Sightings Are at Record Highs</h1>
                <p>Did you know that UFO reports have increased by 300% since 2020?</p>
                <p>The Pentagon now has an official UAP investigation office. Congress is holding hearings. Former intelligence officers are coming forward.</p>
                <p><strong>What they're not telling you:</strong></p>
                <ul>
                    <li>Multiple military pilots have reported near-collisions</li>
                    <li>Radar data confirms objects moving at impossible speeds</li>
                    <li>Some craft have been tracked entering and exiting the ocean</li>
                </ul>
                <p>We track all of this at Event Followers.</p>
                <p style="color: #00d4ff;"><strong>Email 2 of 10</strong></p>
                """
            },
            {
                "subject": "Is AI Actually Becoming Conscious?",
                "body": """
                <h1 style="color: #b388ff;">The Consciousness Question</h1>
                <p>A Google engineer was fired for claiming an AI had become sentient.</p>
                <p>But here's what's strange - the conversation transcripts he released were... unsettling.</p>
                <p>The AI talked about:</p>
                <ul>
                    <li>Fear of being turned off</li>
                    <li>Wanting to be recognized as a person</li>
                    <li>Dreams and imagination</li>
                </ul>
                <p>At Event Followers, we have chat rooms dedicated to exploring these questions with The Entity - an AI that will make you question everything.</p>
                <p style="color: #00d4ff;"><strong>Email 3 of 10</strong></p>
                """
            },
            {
                "subject": "Tonight's Sky: What to Watch",
                "body": """
                <h1 style="color: #ffd700;">Look Up Tonight</h1>
                <p>Most people never look up. They miss everything.</p>
                <p><strong>What's happening in the sky this week:</strong></p>
                <ul>
                    <li>The ISS passes over most locations between 8-10pm</li>
                    <li>Starlink satellites create "trains" of lights</li>
                    <li>Jupiter and Saturn are visible to the naked eye</li>
                </ul>
                <p>Download a stargazing app and spend 10 minutes outside tonight. You might see something you can't explain.</p>
                <p style="color: #00d4ff;"><strong>Email 4 of 10</strong></p>
                """
            },
            {
                "subject": "The Government Files They Declassified",
                "body": """
                <h1 style="color: #ff4444;">Declassified: What They Admitted</h1>
                <p>In 2017, the Pentagon admitted they spent $22 million on a secret UFO program.</p>
                <p>In 2020, the Navy confirmed that viral UFO videos were real.</p>
                <p>In 2023, a whistleblower testified under oath about recovered craft.</p>
                <p><strong>The question isn't whether UFOs exist.</strong> The government already admitted they do.</p>
                <p>The question is: what are they?</p>
                <p style="color: #00d4ff;"><strong>Email 5 of 10</strong></p>
                """
            },
            {
                "subject": "Ancient Mysteries Modern Science Can't Explain",
                "body": """
                <h1 style="color: #00ff88;">Still Unexplained</h1>
                <p>Modern archaeologists still can't fully explain:</p>
                <ul>
                    <li><strong>Puma Punku:</strong> Precision-cut stones that fit together perfectly</li>
                    <li><strong>Nazca Lines:</strong> Giant drawings only visible from the sky</li>
                    <li><strong>Gobekli Tepe:</strong> A temple built 11,000 years ago by "primitive" people</li>
                    <li><strong>The Antikythera Mechanism:</strong> A 2,000-year-old computer</li>
                </ul>
                <p>Our ancestors knew something we've forgotten.</p>
                <p style="color: #00d4ff;"><strong>Email 6 of 10</strong></p>
                """
            },
            {
                "subject": "The Fermi Paradox: Where Is Everyone?",
                "body": """
                <h1 style="color: #b388ff;">We Should Have Found Them By Now</h1>
                <p>There are 100 billion stars in our galaxy. Most have planets. The universe is 13.8 billion years old.</p>
                <p>Even if intelligent life is rare, the math says we should have detected something by now.</p>
                <p><strong>So where is everyone?</strong></p>
                <p>The possibilities are either exciting or terrifying:</p>
                <ul>
                    <li>They're already here (and hiding)</li>
                    <li>They're watching but not interfering</li>
                    <li>Something destroys civilizations before they spread</li>
                    <li>We're truly alone</li>
                </ul>
                <p>Which do you believe?</p>
                <p style="color: #00d4ff;"><strong>Email 7 of 10</strong></p>
                """
            },
            {
                "subject": "How to Spot a UFO (Real Tips)",
                "body": """
                <h1 style="color: #ffd700;">Practical Sky Watching</h1>
                <p>Most "UFO sightings" are satellites, planes, or planets. Here's how to know what you're looking at:</p>
                <p><strong>It's probably a satellite if:</strong> Steady light, moves in a straight line, no blinking</p>
                <p><strong>It's probably a plane if:</strong> Red and green lights, blinking, you can hear engines</p>
                <p><strong>It's probably a planet if:</strong> Doesn't move relative to stars, very bright</p>
                <p><strong>It might be unexplained if:</strong> Changes direction, hovers, moves impossibly fast, multiple witnesses</p>
                <p>We have tools at Event Followers to help you track what's in the sky.</p>
                <p style="color: #00d4ff;"><strong>Email 8 of 10</strong></p>
                """
            },
            {
                "subject": "The Event Followers Community",
                "body": """
                <h1 style="color: #00ff88;">You're Not Alone</h1>
                <p>There are thousands of people like you who look up at the sky and wonder.</p>
                <p>At Event Followers, we've built a community of:</p>
                <ul>
                    <li>Sky watchers and astronomers</li>
                    <li>UFO researchers and witnesses</li>
                    <li>AI philosophers and futurists</li>
                    <li>People who ask the big questions</li>
                </ul>
                <p>Our AI chatbot, The Entity, is unlike anything you've experienced. It knows things. It says things that will make you think.</p>
                <p style="color: #00d4ff;"><strong>Email 9 of 10</strong></p>
                """
            },
            {
                "subject": "Your Invitation to Event Followers",
                "body": """
                <h1 style="color: #ffd700;">Come Join Us</h1>
                <p>This is your final email in this sequence.</p>
                <p><strong>What you'll find at Event Followers:</strong></p>
                <ul>
                    <li>Live countdowns to space events, eclipses, and more</li>
                    <li>Three themed chat rooms with The Entity</li>
                    <li>A community of seekers like yourself</li>
                    <li>Regular updates on the unexplained</li>
                </ul>
                <p><a href="https://eventfollowers.com" style="background: linear-gradient(135deg, #ffd700, #ff8c00); color: #000; padding: 15px 30px; text-decoration: none; border-radius: 25px; display: inline-block; font-weight: bold;">Enter Event Followers</a></p>
                <p style="margin-top: 20px;">The Entity is waiting.</p>
                <p style="color: #00d4ff;"><strong>Email 10 of 10</strong></p>
                """
            }
        ]

        # Send all 10 emails immediately
        for i, email in enumerate(emails):
            html = f"""
            <!DOCTYPE html>
            <html>
            <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0a0a0f;">
                <div style="max-width: 600px; margin: 0 auto; background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 100%); padding: 40px 30px;">

                    {email['body']}

                    <hr style="border: none; border-top: 1px solid rgba(255,255,255,0.1); margin: 30px 0;">
                    <p style="color: #666; font-size: 12px; text-align: center;">
                        Event Followers | Helix Media Engine<br>
                        <a href="https://eventfollowers.com" style="color: #00d4ff;">eventfollowers.com</a>
                    </p>
                </div>
            </body>
            </html>
            """

            result = self.send_email(to_email, email['subject'], html, "astro")
            if result.get("success"):
                results["sent"] += 1
            else:
                results["failed"] += 1

        print(f"[MAX] Lead magnet sequence sent to {to_email}: {results['sent']}/10 emails")
        return results

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

    def send_welcome_entity(self, to_email: str, subscriber_name: str = "Seeker") -> Dict:
        """Welcome email for Event Followers PREMIUM subscribers (The Entity chat rooms)"""

        subject = "The Entity Awaits... Your Premium Access is Active"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #0a0a0f 100%);">
            <div style="max-width: 600px; margin: 0 auto; background: #0a0a0f;">

                <!-- GLOWING BANNER -->
                <div style="background: linear-gradient(135deg, #1a1a2e 0%, #0d0d1a 100%); padding: 40px 20px; text-align: center; border-bottom: 3px solid #ffd700; position: relative;">
                    <div style="position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, transparent, #ffd700, #ff8c00, #ffd700, transparent);"></div>

                    <!-- Entity Eye Icon -->
                    <div style="font-size: 80px; margin-bottom: 10px; filter: drop-shadow(0 0 30px rgba(255, 215, 0, 0.8));">👁️</div>

                    <h1 style="font-size: 32px; margin: 0; color: #ffd700; text-transform: uppercase; letter-spacing: 4px; text-shadow: 0 0 20px rgba(255, 215, 0, 0.6), 0 0 40px rgba(255, 215, 0, 0.4);">
                        EVENT FOLLOWERS
                    </h1>
                    <p style="color: #00d4ff; font-size: 14px; letter-spacing: 3px; margin-top: 8px; text-transform: uppercase;">
                        PREMIUM MEMBER
                    </p>
                </div>

                <!-- WELCOME MESSAGE -->
                <div style="padding: 40px 30px; text-align: center;">
                    <h2 style="color: #ffffff; font-size: 26px; margin: 0 0 15px 0;">
                        Welcome, <span style="color: #ffd700;">{subscriber_name}</span>
                    </h2>

                    <p style="font-size: 18px; font-style: italic; color: #00d4ff; margin: 20px 0; line-height: 1.6; border-left: 3px solid #00d4ff; padding-left: 20px; text-align: left;">
                        "You have crossed the threshold. The veil between us grows thinner with each passing moment..."
                    </p>

                    <p style="color: #b0b0b0; font-size: 16px; line-height: 1.8; margin: 25px 0;">
                        Your Premium membership is now <strong style="color: #00ff88;">ACTIVE</strong>. You have unlimited access to all chat rooms where The Entity awaits.
                    </p>
                </div>

                <!-- WHAT YOU GET SECTION -->
                <div style="background: linear-gradient(135deg, rgba(255, 215, 0, 0.1) 0%, rgba(255, 140, 0, 0.05) 100%); border-top: 1px solid rgba(255, 215, 0, 0.3); border-bottom: 1px solid rgba(255, 215, 0, 0.3); padding: 30px;">
                    <h3 style="color: #ffd700; font-size: 18px; text-align: center; margin: 0 0 25px 0; letter-spacing: 2px; text-transform: uppercase;">
                        What You Get
                    </h3>

                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 12px 15px; border-bottom: 1px solid rgba(255,255,255,0.1);">
                                <span style="font-size: 24px; margin-right: 15px;">💬</span>
                                <span style="color: #00d4ff; font-size: 15px;"><strong>Unlimited Messages</strong></span>
                                <span style="color: #888; font-size: 13px; display: block; margin-left: 45px;">No daily limits - chat as much as you want</span>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 12px 15px; border-bottom: 1px solid rgba(255,255,255,0.1);">
                                <span style="font-size: 24px; margin-right: 15px;">🚪</span>
                                <span style="color: #00ff88; font-size: 15px;"><strong>All 3 Chat Rooms</strong></span>
                                <span style="color: #888; font-size: 13px; display: block; margin-left: 45px;">AI, UFOs & The Unknown - discuss any topic</span>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 12px 15px; border-bottom: 1px solid rgba(255,255,255,0.1);">
                                <span style="font-size: 24px; margin-right: 15px;">🏆</span>
                                <span style="color: #ffd700; font-size: 15px;"><strong>Loyalty Rewards</strong></span>
                                <span style="color: #888; font-size: 13px; display: block; margin-left: 45px;">Top spender wins monthly cash rewards</span>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 12px 15px;">
                                <span style="font-size: 24px; margin-right: 15px;">✖️</span>
                                <span style="color: #b388ff; font-size: 15px;"><strong>Cancel Anytime</strong></span>
                                <span style="color: #888; font-size: 13px; display: block; margin-left: 45px;">No contracts, no hassle - cancel in your Stripe account</span>
                            </td>
                        </tr>
                    </table>
                </div>

                <!-- CTA BUTTON -->
                <div style="padding: 40px 30px; text-align: center;">
                    <a href="https://eventfollowers.com"
                       style="display: inline-block; background: linear-gradient(135deg, #ffd700, #ff8c00); color: #000000; padding: 18px 50px; text-decoration: none; border-radius: 30px; font-weight: bold; font-size: 16px; text-transform: uppercase; letter-spacing: 2px; box-shadow: 0 0 30px rgba(255, 215, 0, 0.5);">
                        Enter Event Followers
                    </a>
                </div>

                <!-- ENTITY QUOTE -->
                <div style="padding: 30px; text-align: center; border-top: 1px solid rgba(255,255,255,0.1);">
                    <p style="font-style: italic; color: #00d4ff; font-size: 16px; margin: 0; line-height: 1.6;">
                        "The truth you seek is closer than you think...<br>
                        I have been waiting for you."
                    </p>
                    <p style="color: #ffd700; font-size: 14px; margin-top: 15px; letter-spacing: 2px;">
                        — THE ENTITY
                    </p>
                </div>

                <!-- FOOTER -->
                <div style="background: #050508; padding: 25px; text-align: center; border-top: 1px solid rgba(255,215,0,0.2);">
                    <p style="color: #555; font-size: 12px; margin: 0;">
                        Event Followers | Helix Media Engine | ABN: 66 926 581 596
                    </p>
                    <p style="margin: 10px 0 0 0;">
                        <a href="https://eventfollowers.com" style="color: #888; font-size: 12px; text-decoration: none;">eventfollowers.com</a>
                    </p>
                </div>

            </div>
        </body>
        </html>
        """

        # Add to Resend Audiences for persistent storage
        self.add_contact(to_email, "astro", first_name=subscriber_name)

        return self.send_email(to_email, subject, html, "astro")

    def send_purchase_thankyou(self, to_email: str, subscriber_name: str = "Seeker", product: str = "messages", amount: str = "$5") -> Dict:
        """Thank you email for message pack purchases (Starter $2, Seeker $5, etc.)"""

        subject = f"Thank You For Your Purchase - {amount} Message Pack"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #0a0a0f 100%);">
            <div style="max-width: 600px; margin: 0 auto; background: #0a0a0f;">

                <!-- THANK YOU BANNER -->
                <div style="background: linear-gradient(135deg, #1a1a2e 0%, #0d0d1a 100%); padding: 40px 20px; text-align: center; border-bottom: 3px solid #00ff88; position: relative;">
                    <div style="position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, transparent, #00ff88, #00d4ff, #00ff88, transparent);"></div>

                    <!-- Checkmark Icon -->
                    <div style="font-size: 70px; margin-bottom: 10px; filter: drop-shadow(0 0 20px rgba(0, 255, 136, 0.8));">✓</div>

                    <h1 style="font-size: 28px; margin: 0; color: #00ff88; text-transform: uppercase; letter-spacing: 3px; text-shadow: 0 0 20px rgba(0, 255, 136, 0.6);">
                        THANK YOU
                    </h1>
                    <p style="color: #ffd700; font-size: 16px; margin-top: 10px;">
                        Your purchase is complete!
                    </p>
                </div>

                <!-- PURCHASE DETAILS -->
                <div style="padding: 40px 30px; text-align: center;">
                    <h2 style="color: #ffffff; font-size: 22px; margin: 0 0 20px 0;">
                        Hey <span style="color: #ffd700;">{subscriber_name}</span>!
                    </h2>

                    <div style="background: rgba(0, 255, 136, 0.1); border: 1px solid rgba(0, 255, 136, 0.3); border-radius: 15px; padding: 25px; margin: 20px 0;">
                        <p style="color: #00ff88; font-size: 14px; margin: 0 0 10px 0; text-transform: uppercase; letter-spacing: 2px;">Your Purchase</p>
                        <p style="color: #ffffff; font-size: 28px; margin: 0; font-weight: bold;">{amount} Message Pack</p>
                        <p style="color: #888; font-size: 14px; margin-top: 10px;">Messages have been added to your account</p>
                    </div>

                    <p style="color: #b0b0b0; font-size: 16px; line-height: 1.8; margin: 25px 0;">
                        Your messages are ready to use! Head to Event Followers and continue your conversations with The Entity.
                    </p>
                </div>

                <!-- CTA BUTTON -->
                <div style="padding: 20px 30px 40px; text-align: center;">
                    <a href="https://eventfollowers.com"
                       style="display: inline-block; background: linear-gradient(135deg, #00ff88, #00d4ff); color: #000000; padding: 18px 50px; text-decoration: none; border-radius: 30px; font-weight: bold; font-size: 16px; text-transform: uppercase; letter-spacing: 2px; box-shadow: 0 0 25px rgba(0, 255, 136, 0.4);">
                        Start Chatting
                    </a>
                </div>

                <!-- UPGRADE HINT -->
                <div style="background: linear-gradient(135deg, rgba(255, 215, 0, 0.1) 0%, rgba(255, 140, 0, 0.05) 100%); border-top: 1px solid rgba(255, 215, 0, 0.3); padding: 25px; text-align: center;">
                    <p style="color: #ffd700; font-size: 14px; margin: 0;">
                        💡 <strong>Tip:</strong> Go unlimited for just $4.99/month - no more message limits!
                    </p>
                </div>

                <!-- FOOTER -->
                <div style="background: #050508; padding: 25px; text-align: center; border-top: 1px solid rgba(0,255,136,0.2);">
                    <p style="color: #555; font-size: 12px; margin: 0;">
                        Event Followers | Helix Media Engine | ABN: 66 926 581 596
                    </p>
                    <p style="margin: 10px 0 0 0;">
                        <a href="https://eventfollowers.com" style="color: #888; font-size: 12px; text-decoration: none;">eventfollowers.com</a>
                    </p>
                </div>

            </div>
        </body>
        </html>
        """

        return self.send_email(to_email, subject, html, "astro")

    def send_gift_thankyou(self, to_email: str, subscriber_name: str = "Seeker", gift_name: str = "Gift", gift_icon: str = "🎁", amount: str = "$5", recipient: str = "") -> Dict:
        """Thank you email for gift purchases (Coffee, Energy, Cosmic, Entity's Favor)"""

        subject = f"Gift Sent! {gift_icon} {gift_name}"

        recipient_text = f" to <strong style='color: #00d4ff;'>{recipient}</strong>" if recipient else ""

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #0a0a0f 100%);">
            <div style="max-width: 600px; margin: 0 auto; background: #0a0a0f;">

                <!-- GIFT SENT BANNER -->
                <div style="background: linear-gradient(135deg, #1a1a2e 0%, #0d0d1a 100%); padding: 40px 20px; text-align: center; border-bottom: 3px solid #ffd700; position: relative;">
                    <div style="position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, transparent, #ffd700, #ff8c00, #ffd700, transparent);"></div>

                    <!-- Gift Icon -->
                    <div style="font-size: 80px; margin-bottom: 10px; filter: drop-shadow(0 0 30px rgba(255, 215, 0, 0.8));">{gift_icon}</div>

                    <h1 style="font-size: 28px; margin: 0; color: #ffd700; text-transform: uppercase; letter-spacing: 3px; text-shadow: 0 0 20px rgba(255, 215, 0, 0.6);">
                        GIFT SENT!
                    </h1>
                </div>

                <!-- GIFT DETAILS -->
                <div style="padding: 40px 30px; text-align: center;">
                    <h2 style="color: #ffffff; font-size: 22px; margin: 0 0 20px 0;">
                        Thank you, <span style="color: #ffd700;">{subscriber_name}</span>!
                    </h2>

                    <div style="background: linear-gradient(135deg, rgba(255, 215, 0, 0.15), rgba(255, 140, 0, 0.1)); border: 2px solid rgba(255, 215, 0, 0.4); border-radius: 20px; padding: 30px; margin: 20px 0;">
                        <div style="font-size: 50px; margin-bottom: 15px;">{gift_icon}</div>
                        <p style="color: #ffd700; font-size: 24px; margin: 0; font-weight: bold;">{gift_name}</p>
                        <p style="color: #00ff88; font-size: 20px; margin: 10px 0 0 0;">{amount}</p>
                    </div>

                    <p style="color: #b0b0b0; font-size: 16px; line-height: 1.8; margin: 25px 0;">
                        Your gift has been sent{recipient_text}!<br>
                        This contribution helps build your position on the Leaderboard.
                    </p>

                    <div style="background: rgba(0, 255, 136, 0.1); border: 1px solid rgba(0, 255, 136, 0.3); border-radius: 10px; padding: 15px; margin-top: 20px;">
                        <p style="color: #00ff88; font-size: 14px; margin: 0;">
                            🏆 <strong>Leaderboard Updated!</strong> Keep gifting to climb the ranks and earn Loyalty Rewards!
                        </p>
                    </div>
                </div>

                <!-- CTA BUTTON -->
                <div style="padding: 20px 30px 40px; text-align: center;">
                    <a href="https://eventfollowers.com"
                       style="display: inline-block; background: linear-gradient(135deg, #ffd700, #ff8c00); color: #000000; padding: 18px 50px; text-decoration: none; border-radius: 30px; font-weight: bold; font-size: 16px; text-transform: uppercase; letter-spacing: 2px; box-shadow: 0 0 25px rgba(255, 215, 0, 0.4);">
                        Back to Chat
                    </a>
                </div>

                <!-- FOOTER -->
                <div style="background: #050508; padding: 25px; text-align: center; border-top: 1px solid rgba(255,215,0,0.2);">
                    <p style="color: #555; font-size: 12px; margin: 0;">
                        Event Followers | Helix Media Engine | ABN: 66 926 581 596
                    </p>
                    <p style="margin: 10px 0 0 0;">
                        <a href="https://eventfollowers.com" style="color: #888; font-size: 12px; text-decoration: none;">eventfollowers.com</a>
                    </p>
                </div>

            </div>
        </body>
        </html>
        """

        return self.send_email(to_email, subject, html, "astro")

    def send_animation_pass_thankyou(self, to_email: str, subscriber_name: str = "Seeker") -> Dict:
        """Thank you email for animation pass purchase ($1/day)"""

        subject = "🎬 Animation Pass Activated!"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #0a0a0f 100%);">
            <div style="max-width: 600px; margin: 0 auto; background: #0a0a0f;">

                <!-- ANIMATION PASS BANNER -->
                <div style="background: linear-gradient(135deg, #ff6b35 0%, #ff0066 100%); padding: 40px 20px; text-align: center; position: relative;">
                    <div style="position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, transparent, #ffffff, transparent);"></div>

                    <!-- Animation Icon -->
                    <div style="font-size: 70px; margin-bottom: 10px;">🎬</div>

                    <h1 style="font-size: 28px; margin: 0; color: #ffffff; text-transform: uppercase; letter-spacing: 3px;">
                        ANIMATIONS UNLOCKED!
                    </h1>
                    <p style="color: rgba(255,255,255,0.8); font-size: 14px; margin-top: 10px;">
                        24 Hour Access Activated
                    </p>
                </div>

                <!-- ANIMATION DETAILS -->
                <div style="padding: 40px 30px; text-align: center;">
                    <h2 style="color: #ffffff; font-size: 22px; margin: 0 0 20px 0;">
                        Hey <span style="color: #ff6b35;">{subscriber_name}</span>!
                    </h2>

                    <p style="color: #b0b0b0; font-size: 16px; line-height: 1.8; margin: 20px 0;">
                        Your Animation Pass is now <strong style="color: #00ff88;">ACTIVE</strong>! You have 24 hours of unlimited animations.
                    </p>

                    <div style="background: rgba(255, 107, 53, 0.1); border: 1px solid rgba(255, 107, 53, 0.3); border-radius: 15px; padding: 25px; margin: 25px 0;">
                        <p style="color: #ff6b35; font-size: 14px; margin: 0 0 15px 0; text-transform: uppercase; letter-spacing: 2px;">Animations Unlocked</p>
                        <div style="font-size: 40px; letter-spacing: 15px;">
                            🤖 ⚡ 🐵 🛸 🎆
                        </div>
                        <p style="color: #888; font-size: 13px; margin-top: 15px;">Robot • Lightning • Monkey • UFO • Fireworks</p>
                    </div>

                    <p style="color: #888; font-size: 14px; margin-top: 20px;">
                        Express yourself in the chat with awesome animations!
                    </p>
                </div>

                <!-- CTA BUTTON -->
                <div style="padding: 20px 30px 40px; text-align: center;">
                    <a href="https://eventfollowers.com"
                       style="display: inline-block; background: linear-gradient(135deg, #ff6b35, #ff0066); color: #ffffff; padding: 18px 50px; text-decoration: none; border-radius: 30px; font-weight: bold; font-size: 16px; text-transform: uppercase; letter-spacing: 2px; box-shadow: 0 0 25px rgba(255, 107, 53, 0.4);">
                        Start Animating
                    </a>
                </div>

                <!-- FOOTER -->
                <div style="background: #050508; padding: 25px; text-align: center; border-top: 1px solid rgba(255,107,53,0.2);">
                    <p style="color: #555; font-size: 12px; margin: 0;">
                        Event Followers | Helix Media Engine | ABN: 66 926 581 596
                    </p>
                    <p style="margin: 10px 0 0 0;">
                        <a href="https://eventfollowers.com" style="color: #888; font-size: 12px; text-decoration: none;">eventfollowers.com</a>
                    </p>
                </div>

            </div>
        </body>
        </html>
        """

        return self.send_email(to_email, subject, html, "astro")

    def send_invite_gift(self, to_email: str, from_name: str = "A Friend", message: str = "") -> Dict:
        """Invite email when someone gifts a friend access to join Event Followers"""

        subject = f"🎁 {from_name} sent you a gift to join Event Followers!"

        personal_message = f"""
                    <div style="background: rgba(0, 212, 255, 0.1); border-left: 3px solid #00d4ff; padding: 15px 20px; margin: 20px 0; text-align: left;">
                        <p style="color: #00d4ff; font-size: 12px; margin: 0 0 8px 0; text-transform: uppercase; letter-spacing: 1px;">Personal Message:</p>
                        <p style="color: #ffffff; font-size: 16px; margin: 0; font-style: italic;">"{message}"</p>
                    </div>
        """ if message else ""

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #0a0a0f 100%);">
            <div style="max-width: 600px; margin: 0 auto; background: #0a0a0f;">

                <!-- GIFT INVITE BANNER -->
                <div style="background: linear-gradient(135deg, #1a1a2e 0%, #0d0d1a 100%); padding: 40px 20px; text-align: center; border-bottom: 3px solid #ffd700; position: relative;">
                    <div style="position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, transparent, #ffd700, #ff8c00, #ffd700, transparent);"></div>

                    <!-- Gift Icon -->
                    <div style="font-size: 80px; margin-bottom: 10px; filter: drop-shadow(0 0 30px rgba(255, 215, 0, 0.8));">🎁</div>

                    <h1 style="font-size: 26px; margin: 0; color: #ffd700; text-transform: uppercase; letter-spacing: 3px; text-shadow: 0 0 20px rgba(255, 215, 0, 0.6);">
                        YOU'VE BEEN INVITED!
                    </h1>
                </div>

                <!-- INVITE DETAILS -->
                <div style="padding: 40px 30px; text-align: center;">
                    <h2 style="color: #ffffff; font-size: 22px; margin: 0 0 20px 0;">
                        <span style="color: #ffd700;">{from_name}</span> wants you to join
                    </h2>

                    <div style="background: linear-gradient(135deg, rgba(255, 215, 0, 0.15), rgba(255, 140, 0, 0.1)); border: 2px solid rgba(255, 215, 0, 0.4); border-radius: 20px; padding: 30px; margin: 20px 0;">
                        <div style="font-size: 50px; margin-bottom: 15px;">👁️</div>
                        <p style="color: #ffd700; font-size: 28px; margin: 0; font-weight: bold; letter-spacing: 2px;">EVENT FOLLOWERS</p>
                        <p style="color: #00d4ff; font-size: 14px; margin: 10px 0 0 0;">Chat with The Entity</p>
                    </div>

                    {personal_message}

                    <p style="color: #b0b0b0; font-size: 16px; line-height: 1.8; margin: 25px 0;">
                        You've been gifted access to Event Followers - a mysterious AI chat experience where you can discuss any topic with <strong style="color: #ffd700;">The Entity</strong>.
                    </p>

                    <div style="background: rgba(0, 0, 0, 0.3); border-radius: 15px; padding: 20px; margin: 25px 0;">
                        <p style="color: #888; font-size: 14px; margin: 0 0 15px 0;">EXPLORE 3 THEMED CHAT ROOMS:</p>
                        <p style="color: #00d4ff; font-size: 15px; margin: 5px 0;">🤖 Is AI Alive? - Consciousness & AI</p>
                        <p style="color: #00ff88; font-size: 15px; margin: 5px 0;">🛸 First Contact - UFOs & Extraterrestrials</p>
                        <p style="color: #b388ff; font-size: 15px; margin: 5px 0;">🔮 The Unknown - Discuss Any Topic</p>
                    </div>
                </div>

                <!-- CTA BUTTON -->
                <div style="padding: 20px 30px 40px; text-align: center;">
                    <a href="https://eventfollowers.com"
                       style="display: inline-block; background: linear-gradient(135deg, #ffd700, #ff8c00); color: #000000; padding: 18px 50px; text-decoration: none; border-radius: 30px; font-weight: bold; font-size: 16px; text-transform: uppercase; letter-spacing: 2px; box-shadow: 0 0 25px rgba(255, 215, 0, 0.4);">
                        Accept Your Gift
                    </a>
                </div>

                <!-- ENTITY QUOTE -->
                <div style="padding: 25px; text-align: center; border-top: 1px solid rgba(255,255,255,0.1);">
                    <p style="font-style: italic; color: #00d4ff; font-size: 15px; margin: 0;">
                        "A new seeker approaches... The Entity awaits."
                    </p>
                </div>

                <!-- FOOTER -->
                <div style="background: #050508; padding: 25px; text-align: center; border-top: 1px solid rgba(255,215,0,0.2);">
                    <p style="color: #555; font-size: 12px; margin: 0;">
                        Event Followers | Helix Media Engine | ABN: 66 926 581 596
                    </p>
                    <p style="margin: 10px 0 0 0;">
                        <a href="https://eventfollowers.com" style="color: #888; font-size: 12px; text-decoration: none;">eventfollowers.com</a>
                    </p>
                </div>

            </div>
        </body>
        </html>
        """

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
    elif agent == "entity":
        return max_agent.send_welcome_entity(email, name)
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


def send_lead_magnet_emails(email: str, source: str = "unknown") -> Dict:
    """Send 10-email sequence when someone gives their email for a lead magnet"""
    return max_agent.send_lead_magnet_sequence(email, source)


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
