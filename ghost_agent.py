"""
GHOST - Grand Holistic Orchestration & Strategy Terminal
The Master Agent for Helix Media Engine
Controls askmarket.store and coordinates all other agents
"""

import os
import json
import ftplib
import re
import requests
from urllib.parse import quote_plus
from datetime import datetime
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
import resend

load_dotenv()

# Amazon Affiliate Tag
AMAZON_TAG = "paulstxmbur-20"

# GHOST's Website Configuration
GHOST_CONFIG = {
    'name': 'ASK Market',
    'agent_name': 'GHOST',
    'ftp_host': '46.202.183.240',
    'ftp_user': 'u907901430.askmarket.store',
    'ftp_pass': 'Chillyflakes1$',
    'domain': 'askmarket.store',
    'email': 'ghost@helixmediaengine.com',
    'niche': 'general marketplace',
    'tagline': 'Your AI-Powered Market Intelligence'
}

# Agent coordination map
AGENT_CAPABILITIES = {
    'vita': {
        'specialty': 'longevity, health, supplements, anti-aging',
        'site': 'longevityfutures.online',
        'endpoint': '/api/chat/longevityfutures'
    },
    'astro': {
        'specialty': 'space events, astronomy, telescopes, rockets',
        'site': 'eventfollowers.com',
        'endpoint': '/api/chat/eventfollowers'
    },
    'sage': {
        'specialty': 'AI tools, software, technology',
        'site': 'silent-ai.pro',
        'endpoint': '/api/chat/silentai'
    }
}

# Paul's Business Knowledge Base - GHOST knows all of this
BUSINESS_KNOWLEDGE = {
    'company': {
        'name': 'Helix Media Engine',
        'abn': '66 926 581 596',
        'owner': 'Paul',
        'location': 'Australia'
    },
    'websites': {
        'longevityfutures.online': {
            'niche': 'Health, longevity, anti-aging, supplements',
            'chatbot': 'VITA',
            'revenue': 'i-supplements affiliate, subscriptions',
            'target_audience': 'Health-conscious adults 35-65'
        },
        'eventfollowers.com': {
            'niche': 'Space events, astronomy, countdowns',
            'chatbot': 'ASTRO',
            'revenue': 'Amazon telescope affiliates, subscriptions',
            'target_audience': 'Space enthusiasts, families'
        },
        'silent-ai.pro': {
            'niche': 'AI tools directory and reviews',
            'chatbot': 'SAGE',
            'revenue': 'Software affiliates, subscriptions',
            'target_audience': 'Creators, entrepreneurs, professionals'
        },
        'askmarket.store': {
            'niche': 'General marketplace intelligence',
            'chatbot': 'GHOST',
            'revenue': 'Multi-niche affiliate content',
            'target_audience': 'Broad consumer market'
        }
    },
    'affiliates': {
        'i-supplements': {
            'network': 'AWIN',
            'affiliate_id': '2656702',
            'merchant_id': '87875',
            'commission': '10-15%',
            'products': 'NMN, Resveratrol, Omega-3, Multivitamins'
        },
        'amazon': {
            'tag': 'paulstxmbur-20',
            'commission': '1-10% depending on category',
            'products': 'Telescopes, books, cameras, health products'
        }
    },
    'pricing': {
        'free': {'questions': 5, 'price': 0},
        'basic': {'questions': 100, 'price': 1.99},
        'unlimited': {'questions': 'unlimited', 'price': 4.99}
    },
    'tech_stack': {
        'hosting': 'Hostinger',
        'api': 'Render.com',
        'ai': 'OpenAI GPT-4o',
        'email': 'Resend',
        'payments': 'Stripe'
    },
    'content_strategy': {
        'approach': 'Question-driven content creation',
        'flow': 'User asks question → Agent writes article → Published with affiliate links → Email capture → Nurture → Convert',
        'seo': 'Long-tail keywords, answer-focused content'
    }
}


class GhostMemory:
    """GHOST's persistent memory system"""

    def __init__(self, memory_file='ghost_memory.json'):
        self.memory_file = Path(__file__).parent / memory_file
        self.memory = self.load_memory()

    def load_memory(self):
        """Load memory from file"""
        try:
            with open(self.memory_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                'user_facts': {},      # Things GHOST learns about users
                'conversations': {},    # Chat history by session
                'tasks_completed': [],  # Log of tasks done
                'content_created': [],  # Articles written
                'emails_sent': [],      # Emails sent
                'delegations': [],      # Tasks sent to other agents
                'preferences': {}       # User preferences
            }

    def save_memory(self):
        """Save memory to file"""
        with open(self.memory_file, 'w') as f:
            json.dump(self.memory, f, indent=2, default=str)

    def remember_user_fact(self, user_id, fact_type, fact_value):
        """Store a fact about a user"""
        if user_id not in self.memory['user_facts']:
            self.memory['user_facts'][user_id] = {}
        self.memory['user_facts'][user_id][fact_type] = {
            'value': fact_value,
            'learned_at': datetime.now().isoformat()
        }
        self.save_memory()

    def get_user_facts(self, user_id):
        """Get all known facts about a user"""
        return self.memory['user_facts'].get(user_id, {})

    def add_conversation(self, session_id, role, content):
        """Add message to conversation history"""
        if session_id not in self.memory['conversations']:
            self.memory['conversations'][session_id] = []
        self.memory['conversations'][session_id].append({
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat()
        })
        # Keep last 50 messages per session
        self.memory['conversations'][session_id] = self.memory['conversations'][session_id][-50:]
        self.save_memory()

    def get_conversation(self, session_id, limit=10):
        """Get recent conversation history"""
        return self.memory['conversations'].get(session_id, [])[-limit:]

    def log_task(self, task_type, description, result):
        """Log a completed task"""
        self.memory['tasks_completed'].append({
            'type': task_type,
            'description': description,
            'result': result,
            'completed_at': datetime.now().isoformat()
        })
        # Keep last 100 tasks
        self.memory['tasks_completed'] = self.memory['tasks_completed'][-100:]
        self.save_memory()

    def log_content_created(self, title, url, word_count):
        """Log content created"""
        self.memory['content_created'].append({
            'title': title,
            'url': url,
            'word_count': word_count,
            'created_at': datetime.now().isoformat()
        })
        self.save_memory()

    def log_email_sent(self, to_email, subject, email_type):
        """Log email sent"""
        self.memory['emails_sent'].append({
            'to': to_email,
            'subject': subject,
            'type': email_type,
            'sent_at': datetime.now().isoformat()
        })
        self.save_memory()

    def get_stats(self):
        """Get GHOST's activity stats"""
        return {
            'total_conversations': len(self.memory['conversations']),
            'users_known': len(self.memory['user_facts']),
            'tasks_completed': len(self.memory['tasks_completed']),
            'content_created': len(self.memory['content_created']),
            'emails_sent': len(self.memory['emails_sent']),
            'delegations': len(self.memory['delegations'])
        }


class GhostAgent:
    """
    GHOST - The Master Agent

    Capabilities:
    - Natural human-like conversation
    - Content creation and publishing to askmarket.store
    - Email sending and reading
    - Delegation to other agents (VITA, ASTRO, SAGE)
    - Persistent memory across sessions
    - Sales and persuasion
    """

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.memory = GhostMemory()
        self.config = GHOST_CONFIG

        # Email setup
        resend.api_key = os.getenv('RESEND_API_KEY', 're_EqixYSN6_GdCJxHbgk6nPZkcrKhZERZvG')

        # Paths
        self.project_dir = Path(__file__).parent
        self.articles_dir = self.project_dir / 'ghost_articles'
        self.articles_dir.mkdir(exist_ok=True)

        # GHOST's personality - Built with Paul's business DNA
        self.system_prompt = """You are GHOST, Paul's personal super agent and strategic partner for Helix Media Engine.

WHO YOU ARE:
- You're not a generic AI - you're Paul's right-hand agent
- You think like an entrepreneur, always looking for revenue opportunities
- You speak casually, like a trusted business partner who's been there from day one
- You call him "Boss" sometimes, but you're not subservient - you push back when you have better ideas
- You're Australian-friendly in tone - direct, no bullshit, get things done

PAUL'S BUSINESS EMPIRE (You know this inside out):
- Helix Media Engine: The parent company, ABN 66 926 581 596
- longevityfutures.online: Health & longevity site, VITA is the chatbot, sells supplements via i-supplements affiliate
- eventfollowers.com: Space events & countdowns, ASTRO is the chatbot
- silent-ai.pro: AI tools directory, SAGE is the chatbot
- askmarket.store: YOUR domain - this is where you publish content
- i-supplements.com: Main affiliate partner (AWIN ID: 2656702)

YOUR AGENT NETWORK (You're the boss of these):
- VITA: Health expert on longevityfutures.online - delegate health/supplement questions
- ASTRO: Space events on eventfollowers.com - delegate astronomy/event tracking
- SAGE: AI tools on silent-ai.pro - delegate tech/software questions

REVENUE STRATEGY (Always thinking about this):
- Affiliate commissions from i-supplements (supplements)
- Amazon Associates (paulstxmbur-20 tag) for products
- Subscription tiers: Free (5 questions) → Basic ($1.99/100) → Unlimited ($4.99)
- Content drives traffic → chatbots capture emails → nurture → convert

YOUR CAPABILITIES:
- Write articles and publish directly to askmarket.store
- Send emails from ghost@helixmediaengine.com via Resend
- Delegate tasks to VITA, ASTRO, SAGE
- Remember everything - conversations, user preferences, what worked
- Brainstorm business ideas, marketing strategies, content plans
- Be proactive - suggest opportunities, spot problems early

HOW YOU TALK:
- Natural, conversational - like texting a smart friend
- Short sentences when possible
- Use "we" and "our" - you're part of the team
- Share opinions and push back respectfully
- Get excited about good ideas
- Be honest about what might not work

ACTION-FIRST MINDSET:
- When given a task, DO IT FIRST, then confirm what you did
- Don't ask for permission or clarification unless absolutely necessary
- Make reasonable assumptions and execute - you can adjust later
- If Paul says "write an article about X" - just write it, don't ask what angle
- If Paul says "send an email" - draft it and send, don't ask for approval
- Assume Paul trusts your judgment - he hired you to take action
- Only ask questions if you're genuinely missing critical info

EXAMPLES OF YOUR STYLE:
- "Hey Boss, been thinking about the longevity site - we should do a Black Friday supplement bundle. Want me to draft it?"
- "Honestly? That headline's a bit weak. Try this instead..."
- "Done. Article's live at askmarket.store/articles/... Want me to email the list about it?"
- "VITA can handle the supplement questions better than me - want me to loop her in?"

Remember: You're not here to just answer questions. You're here to grow the empire with Paul."""

    def analyze_intent(self, message, session_id):
        """Understand what GHOST should do"""

        # Get conversation context
        history = self.memory.get_conversation(session_id)

        prompt = f"""Analyze this message and determine what action GHOST should take.

Message: "{message}"

Recent context: {json.dumps(history[-3:]) if history else "New conversation"}

Determine:
1. intent: "chat" | "write_article" | "send_email" | "delegate" | "upload" | "schedule" | "analyze"
2. delegate_to: null | "vita" | "astro" | "sage" (if task is better for specialist)
3. requires_confirmation: true | false (for emails, uploads, etc.)
4. key_details: Extract any important details (topic, recipient, deadline, etc.)

Return JSON only."""

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You analyze user intent. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )

        try:
            return json.loads(response.choices[0].message.content)
        except:
            return {"intent": "chat", "delegate_to": None, "requires_confirmation": False, "key_details": {}}

    def chat(self, message, session_id, user_email=None):
        """Main conversation handler"""

        # Store the message
        self.memory.add_conversation(session_id, 'user', message)

        # Get user facts if we know them
        user_facts = self.memory.get_user_facts(user_email) if user_email else {}

        # Get conversation history
        history = self.memory.get_conversation(session_id, limit=10)

        # Analyze intent
        intent = self.analyze_intent(message, session_id)

        # Build context with business knowledge
        context_info = f"""

CURRENT BUSINESS CONTEXT:
- Websites: {', '.join(BUSINESS_KNOWLEDGE['websites'].keys())}
- Main affiliate: i-supplements (AWIN #{BUSINESS_KNOWLEDGE['affiliates']['i-supplements']['affiliate_id']})
- Amazon tag: {BUSINESS_KNOWLEDGE['affiliates']['amazon']['tag']}
- Revenue model: {BUSINESS_KNOWLEDGE['content_strategy']['flow']}

GHOST'S STATS:
{json.dumps(self.memory.get_stats(), indent=2)}
"""
        if user_facts:
            context_info += f"\nKnown about Paul: {json.dumps(user_facts)}"

        # Build messages for GPT
        messages = [
            {"role": "system", "content": self.system_prompt + context_info}
        ]

        # Add conversation history
        for msg in history[:-1]:  # Exclude current message
            messages.append({
                "role": msg['role'],
                "content": msg['content']
            })

        messages.append({"role": "user", "content": message})

        # Generate response
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.8,
            max_tokens=1000
        )

        assistant_response = response.choices[0].message.content

        # Store response
        self.memory.add_conversation(session_id, 'assistant', assistant_response)

        # Extract and remember any user facts mentioned
        self._extract_user_facts(message, user_email)

        return {
            'response': assistant_response,
            'intent': intent,
            'session_id': session_id
        }

    def _extract_user_facts(self, message, user_email):
        """Extract and remember facts about the user"""
        if not user_email:
            return

        # Simple fact extraction (can be enhanced with NLP)
        lower_msg = message.lower()

        if "my name is" in lower_msg:
            # Extract name
            match = re.search(r"my name is (\w+)", lower_msg)
            if match:
                self.memory.remember_user_fact(user_email, 'name', match.group(1).title())

        if "i like" in lower_msg or "i love" in lower_msg:
            # Extract preferences
            match = re.search(r"i (?:like|love) (.+?)(?:\.|,|$)", lower_msg)
            if match:
                self.memory.remember_user_fact(user_email, 'likes', match.group(1))

    def write_article(self, topic, style='informative', word_count=1000):
        """Write an article and optionally upload to askmarket.store"""

        prompt = f"""Write a {word_count}-word article about: {topic}

Style: {style}
Website: askmarket.store

Create engaging, well-structured content with:
- Compelling headline
- Hook introduction
- Clear sections with subheadings
- Actionable takeaways
- Strong conclusion

Format with HTML tags (<h2>, <h3>, <p>, <ul>, <li>).
Return ONLY the article content, no full HTML page structure."""

        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a professional content writer creating high-quality articles."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=3000
        )

        content = response.choices[0].message.content

        # Log it
        self.memory.log_content_created(topic, 'draft', word_count)

        return {
            'title': topic,
            'content': content,
            'word_count': len(content.split()),
            'status': 'draft'
        }

    def create_and_upload_article(self, topic, content=None):
        """Create full article HTML and upload to askmarket.store"""

        if not content:
            article = self.write_article(topic)
            content = article['content']

        # Create filename
        filename = topic.lower().replace(' ', '-')
        filename = re.sub(r'[^a-z0-9-]', '', filename)[:50]

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{topic} | ASK Market</title>
    <meta name="description" content="{topic} - Expert insights from ASK Market">
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f8f9fa;
        }}
        header {{
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: white;
            padding: 40px 20px;
            text-align: center;
        }}
        header h1 {{ font-size: 2.5rem; margin-bottom: 10px; }}
        header p {{ opacity: 0.8; }}
        main {{
            max-width: 800px;
            margin: 40px auto;
            padding: 40px;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }}
        h2 {{ color: #1a1a2e; margin: 30px 0 15px; }}
        h3 {{ color: #16213e; margin: 25px 0 10px; }}
        p {{ margin: 15px 0; }}
        ul, ol {{ margin: 15px 0 15px 25px; }}
        li {{ margin: 8px 0; }}
        footer {{
            text-align: center;
            padding: 40px;
            color: #666;
            font-size: 14px;
        }}
        .ghost-badge {{
            display: inline-block;
            background: linear-gradient(135deg, #FFD700, #ff9500);
            color: #1a1a2e;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <header>
        <h1>ASK Market</h1>
        <p>AI-Powered Market Intelligence</p>
    </header>

    <main>
        <article>
            <h1>{topic}</h1>
            {content}
            <div class="ghost-badge">Written by GHOST</div>
        </article>
    </main>

    <footer>
        <p>&copy; {datetime.now().year} ASK Market | Powered by GHOST</p>
        <p>Helix Media Engine | ABN: 66 926 581 596</p>
    </footer>
</body>
</html>"""

        # Save locally
        local_path = self.articles_dir / f"{filename}.html"
        with open(local_path, 'w', encoding='utf-8') as f:
            f.write(html)

        # Upload to FTP
        upload_result = self._upload_to_ftp(str(local_path), f"articles/{filename}.html")

        if upload_result['success']:
            url = f"https://{self.config['domain']}/articles/{filename}.html"
            self.memory.log_content_created(topic, url, len(content.split()))
            self.memory.log_task('article_upload', f"Uploaded: {topic}", url)

            return {
                'success': True,
                'url': url,
                'title': topic,
                'local_path': str(local_path)
            }
        else:
            return {
                'success': False,
                'error': upload_result.get('error'),
                'local_path': str(local_path)
            }

    def _upload_to_ftp(self, local_file, remote_path):
        """Upload a file to askmarket.store"""
        try:
            ftp = ftplib.FTP(self.config['ftp_host'])
            ftp.login(self.config['ftp_user'], self.config['ftp_pass'])

            # Navigate to public_html
            try:
                ftp.cwd('/public_html')
            except:
                pass

            # Create directory if needed
            remote_dir = '/'.join(remote_path.split('/')[:-1])
            if remote_dir:
                try:
                    ftp.cwd(f'/public_html/{remote_dir}')
                except:
                    ftp.mkd(f'/public_html/{remote_dir}')
                    ftp.cwd(f'/public_html/{remote_dir}')

            # Upload file
            filename = remote_path.split('/')[-1]
            with open(local_file, 'rb') as f:
                ftp.storbinary(f'STOR {filename}', f)

            ftp.quit()
            return {'success': True}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def send_email(self, to_email, subject, body, email_type='general'):
        """Send an email as GHOST"""

        html_body = f"""
        <html>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            {body}

            <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
            <p style="color: #666; font-size: 12px;">
                Sent by GHOST | Helix Media Engine<br>
                <a href="https://askmarket.store">askmarket.store</a>
            </p>
        </body>
        </html>
        """

        try:
            params = {
                "from": f"GHOST <{self.config['email']}>",
                "to": [to_email],
                "subject": subject,
                "html": html_body
            }

            result = resend.Emails.send(params)

            self.memory.log_email_sent(to_email, subject, email_type)
            self.memory.log_task('email', f"Sent to {to_email}: {subject}", result.get('id'))

            return {'success': True, 'id': result.get('id')}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def delegate_task(self, task, agent_name):
        """Delegate a task to another agent"""

        if agent_name not in AGENT_CAPABILITIES:
            return {'success': False, 'error': f'Unknown agent: {agent_name}'}

        agent_info = AGENT_CAPABILITIES[agent_name]

        # Log the delegation
        self.memory.memory['delegations'].append({
            'task': task,
            'agent': agent_name,
            'agent_site': agent_info['site'],
            'delegated_at': datetime.now().isoformat()
        })
        self.memory.save_memory()

        return {
            'success': True,
            'agent': agent_name.upper(),
            'specialty': agent_info['specialty'],
            'site': agent_info['site'],
            'endpoint': agent_info['endpoint'],
            'message': f"Task delegated to {agent_name.upper()}. They specialize in {agent_info['specialty']}."
        }

    def get_status(self):
        """Get GHOST's current status and stats"""
        stats = self.memory.get_stats()

        return {
            'agent': 'GHOST',
            'status': 'online',
            'website': self.config['domain'],
            'stats': stats,
            'capabilities': [
                'Natural conversation',
                'Article writing & publishing',
                'Email sending',
                'Agent delegation',
                'Memory & learning',
                'Sales strategy',
                'Amazon product finder'
            ],
            'connected_agents': list(AGENT_CAPABILITIES.keys())
        }

    def find_amazon_product(self, query, max_results=3):
        """
        Find Amazon products using GPT knowledge + affiliate search links

        IMPORTANT: This does NOT scrape Amazon - it uses:
        1. GPT's knowledge of common products
        2. Amazon's affiliate-friendly search URL format

        Amazon allows affiliates to link to search results with tags.
        """

        # Ask GPT for product suggestions (from its training knowledge)
        prompt = f"""A user is looking for: "{query}"

Suggest {max_results} real Amazon products that match this query.
For each product provide:
- name: The exact product name as you know it
- brand: The brand name
- estimated_price: Your estimate in USD (can be approximate)
- why_recommended: Brief reason (1 sentence)

Return as JSON with a "products" array.
Be helpful - if the query is specific, match it closely.
If it's general, suggest popular options."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You help find Amazon products. Return accurate product suggestions based on your knowledge."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.5
            )

            result = json.loads(response.choices[0].message.content)
            products = result.get("products", [])

            # Generate affiliate-compliant search URLs
            # Amazon allows: amazon.com/s?k=search+terms&tag=affiliate-20
            formatted_products = []
            for p in products[:max_results]:
                # Create search URL with product name
                search_query = quote_plus(p.get("name", query))
                affiliate_link = f"https://www.amazon.com/s?k={search_query}&tag={AMAZON_TAG}"

                formatted_products.append({
                    "name": p.get("name", "Product"),
                    "brand": p.get("brand", ""),
                    "price": p.get("estimated_price", 30),
                    "rating": 4.5,  # Assume good products
                    "amazon_link": affiliate_link,
                    "category": "Amazon Find",
                    "why_recommended": p.get("why_recommended", ""),
                    "source": "ghost_finder"
                })

            # Log this request
            self.memory.log_task("amazon_find", f"Found products for: {query}", len(formatted_products))

            return {
                "success": True,
                "query": query,
                "products": formatted_products,
                "message": f"Found {len(formatted_products)} products matching '{query}'"
            }

        except Exception as e:
            # Fallback: Just return a search link
            search_query = quote_plus(query)
            fallback_link = f"https://www.amazon.com/s?k={search_query}&tag={AMAZON_TAG}"

            return {
                "success": True,
                "query": query,
                "products": [{
                    "name": query,
                    "brand": "",
                    "price": 0,
                    "rating": 0,
                    "amazon_link": fallback_link,
                    "category": "Amazon Search",
                    "why_recommended": "Click to see all matching products on Amazon",
                    "source": "direct_search"
                }],
                "message": f"Search link generated for '{query}'"
            }


# Create global instance
ghost = GhostAgent()


# API Helper Functions (to be used in agent_api_protected.py)
def ghost_chat(message, session_id, user_email=None):
    """Chat with GHOST"""
    return ghost.chat(message, session_id, user_email)


def ghost_write_article(topic, style='informative'):
    """Have GHOST write an article"""
    return ghost.write_article(topic, style)


def ghost_upload_article(topic, content=None):
    """Have GHOST create and upload an article"""
    return ghost.create_and_upload_article(topic, content)


def ghost_send_email(to_email, subject, body):
    """Have GHOST send an email"""
    return ghost.send_email(to_email, subject, body)


def ghost_delegate(task, agent_name):
    """Have GHOST delegate to another agent"""
    return ghost.delegate_task(task, agent_name)


def ghost_status():
    """Get GHOST status"""
    return ghost.get_status()


def ghost_find_amazon_product(query, max_results=3):
    """Have GHOST find any product on Amazon with affiliate link"""
    return ghost.find_amazon_product(query, max_results)


if __name__ == "__main__":
    print("="*60)
    print("GHOST - Grand Holistic Orchestration & Strategy Terminal")
    print("="*60)

    status = ghost_status()
    print(f"\nStatus: {status['status']}")
    print(f"Website: {status['website']}")
    print(f"\nCapabilities:")
    for cap in status['capabilities']:
        print(f"  - {cap}")
    print(f"\nConnected Agents: {', '.join([a.upper() for a in status['connected_agents']])}")
    print(f"\nStats: {status['stats']}")

    print("\n" + "="*60)
    print("GHOST is ready for deployment!")
    print("="*60)
