"""
ASTRO 2.0 - AUTONOMOUS REVENUE AGENT (OpenAI Edition)
Creates content on-the-fly + Recommends 5-10 affiliate products
Millions of tokens available - Perfect for 24/7 operation
"""

import os
import json
import ftplib
import re
from datetime import datetime, timedelta
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class AstroV2OpenAI:
    """Autonomous content creation + multi-product recommendations using OpenAI"""

    def __init__(self, website_config):
        """
        Initialize Astro for a specific website

        website_config = {
            'name': 'Event Followers',
            'ftp_host': '...',
            'ftp_user': '...',
            'ftp_pass': '...',
            'domain': 'eventfollowers.com',
            'niche': 'space events',
            'product_categories': ['telescope', 'binoculars', ...]
        }
        """
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.config = website_config

        # FTP from config
        self.ftp_host = website_config['ftp_host']
        self.ftp_user = website_config['ftp_user']
        self.ftp_pass = website_config['ftp_pass']

        # Paths
        self.project_dir = Path(__file__).parent
        self.articles_dir = self.project_dir / 'articles'

        # Load product database for this website
        self.product_database = self.load_products(website_config['niche'])

    def load_products(self, niche):
        """Load product database based on website niche"""

        if niche == 'space events':
            return {
                "telescope": [
                    {"name": "Celestron NexStar 6SE", "price": 899, "rating": 5, "amazon": "B0007UQNKY", "category": "Premium"},
                    {"name": "Orion SkyQuest XT8", "price": 449, "rating": 4.5, "amazon": "B00D05BKOW", "category": "Best Value"},
                    {"name": "Celestron AstroMaster 70AZ", "price": 199, "rating": 4, "amazon": "B001TI9Y2M", "category": "Budget"},
                    {"name": "Meade Instruments ETX90", "price": 599, "rating": 4.5, "amazon": "B0000665V0", "category": "Portable"},
                    {"name": "Celestron CGX 925", "price": 3299, "rating": 5, "amazon": "B01LZ5Q3YF", "category": "Professional"}
                ],
                "binoculars": [
                    {"name": "Celestron SkyMaster 25x70", "price": 89, "rating": 4.5, "amazon": "B00008Y0VN", "category": "Best Stargazing"},
                    {"name": "Nikon Aculon A211 10x50", "price": 99, "rating": 4, "amazon": "B00B7LYMYY", "category": "All-Purpose"},
                    {"name": "Orion 09351 UltraView 10x50", "price": 49, "rating": 4, "amazon": "B0000XMQBY", "category": "Budget"},
                ],
                "camera": [
                    {"name": "Canon EOS Rebel T7", "price": 449, "rating": 4.5, "amazon": "B07C2Z5V8T", "category": "Beginner"},
                    {"name": "Nikon D3500", "price": 499, "rating": 4.5, "amazon": "B07GWKDLGT", "category": "Best Value"},
                    {"name": "Sony Alpha a6400", "price": 898, "rating": 5, "amazon": "B07MTWVN3M", "category": "Advanced"},
                ],
                "books": [
                    {"name": "NightWatch: A Practical Guide", "price": 25, "rating": 5, "amazon": "B004GHLYEY", "category": "Essential"},
                    {"name": "Turn Left at Orion", "price": 24, "rating": 5, "amazon": "B07NNZX7SB", "category": "Beginner"},
                ],
                "apps": [
                    {"name": "SkySafari Plus", "price": 15, "rating": 5, "store": "app_store", "category": "Best Overall"},
                    {"name": "Star Walk 2", "price": 3, "rating": 4.5, "store": "app_store", "category": "Budget"},
                ]
            }

        elif niche == 'longevity':
            return {
                "nmn": [
                    {"name": "NMN 500mg (High Purity)", "price": 49, "rating": 4.5, "affiliate": "i-supplements", "category": "NAD+ Booster"},
                    {"name": "NMN + Resveratrol Combo", "price": 79, "rating": 5, "affiliate": "i-supplements", "category": "Premium Stack"},
                ],
                "omega3": [
                    {"name": "Omega-3 Fish Oil (Triple Strength)", "price": 29, "rating": 4.5, "affiliate": "i-supplements", "category": "Heart Health"},
                ],
                "multivitamin": [
                    {"name": "Men's 50+ Multivitamin", "price": 35, "rating": 4.5, "affiliate": "i-supplements", "category": "Daily Essential"},
                ]
            }

        elif niche == 'ai tools':
            return {
                "ai_writing": [
                    {"name": "Jasper AI", "price": 49, "rating": 4.5, "affiliate": "jasper", "category": "Content Creation"},
                    {"name": "Grammarly Premium", "price": 12, "rating": 4.5, "affiliate": "grammarly", "category": "Writing Assistant"},
                ],
                "ai_design": [
                    {"name": "Midjourney Pro", "price": 30, "rating": 5, "affiliate": "midjourney", "category": "AI Art"},
                ]
            }

        return {}

    def detect_user_intent(self, user_message):
        """Analyze what user wants using OpenAI"""

        available_categories = list(self.product_database.keys())

        prompt = f"""Analyze this user question and extract key information.

Website: {self.config['name']} ({self.config['niche']})
User question: "{user_message}"

Available product categories: {', '.join(available_categories)}

Return JSON with:
- event_name: Brief name (e.g. "Perseid Meteor Shower", "Jupiter Viewing")
- event_type: Type of event/topic
- needs_article: true if they want information we should create content for
- product_categories: Array of 2-4 relevant categories from the available list above
- urgency: "tonight", "this_week", "this_month", or "general"

Be smart about product categories - suggest 2-4 that would help them accomplish their goal.
"""

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",  # Fast and cheap for analysis
            messages=[
                {"role": "system", "content": "You are an intent analyzer. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )

        try:
            return json.loads(response.choices[0].message.content)
        except:
            return {
                "event_name": "General Topic",
                "event_type": "general",
                "needs_article": True,
                "product_categories": list(self.product_database.keys())[:2],
                "urgency": "general"
            }

    def generate_article_content(self, event_name, event_type, user_context):
        """Generate article content using OpenAI"""

        prompt = f"""Write a comprehensive, engaging article about: {event_name}

Context: {user_context}
Website: {self.config['name']}
Niche: {self.config['niche']}

Create an 800-1200 word article that includes:
- Exciting introduction that hooks readers
- What makes this special/important
- Practical information (when, where, how)
- Step-by-step guidance for best experience
- Helpful tips and tricks
- Interesting facts that add value

Write in a friendly, accessible style. Use HTML formatting with <h2>, <h3>, <p>, <ul>, <li> tags.
Make it valuable and engaging!

Return ONLY the article HTML (no full page structure, just content).
"""

        response = self.client.chat.completions.create(
            model="gpt-4o",  # Best quality for content
            messages=[
                {"role": "system", "content": f"You are an expert content writer for {self.config['name']}."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=3000
        )

        return response.choices[0].message.content

    def select_products(self, product_categories):
        """Select 5-10 relevant products across categories"""
        selected = []

        for category in product_categories[:3]:
            if category in self.product_database:
                products = self.product_database[category]
                selected.extend(products[:3])

        return selected[:10]

    def format_product_recommendations(self, products, amazon_tag="paulstxmbur-20"):
        """Format products as beautiful HTML with affiliate links"""

        html = """
        <div class="product-recommendations">
            <h2>🛒 Recommended Gear & Resources</h2>
            <p>Everything you need to make the most of this:</p>
"""

        categories = {}
        for product in products:
            cat = product.get('category', 'Recommended')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(product)

        for category, items in categories.items():
            html += f"""
            <div class="product-category">
                <h3>{category}</h3>
"""

            for product in items:
                stars = "⭐" * int(product['rating'])

                # Build affiliate link
                if 'amazon' in product:
                    link = f"https://amazon.com/dp/{product['amazon']}?tag={amazon_tag}"
                    button_text = "View on Amazon →"
                elif 'affiliate' in product:
                    if product['affiliate'] == 'i-supplements':
                        link = "https://www.awin1.com/cread.php?awinmid=87875&awinaffid=2656702&ued=https%3A%2F%2Fwww.i-supplements.com"
                        button_text = "Shop at i-Supplements →"
                    else:
                        link = "#"
                        button_text = "Learn More →"
                else:
                    link = "#"
                    button_text = "Learn More →"

                html += f"""
                <div class="product-card">
                    <h4>{product['name']}</h4>
                    <p class="price">${product['price']}</p>
                    <p class="rating">{stars} ({product['rating']}/5)</p>
                    <a href="{link}" target="_blank" rel="noopener" class="buy-button">{button_text}</a>
                </div>
"""

            html += """
            </div>
"""

        html += """
        </div>

        <style>
        .product-recommendations {
            background: #f8f9fa;
            padding: 30px;
            border-radius: 12px;
            margin: 40px 0;
        }
        .product-category {
            margin: 30px 0;
        }
        .product-category h3 {
            color: #4A90E2;
            border-bottom: 2px solid #4A90E2;
            padding-bottom: 10px;
        }
        .product-card {
            background: white;
            padding: 20px;
            margin: 15px 0;
            border-radius: 8px;
            border-left: 4px solid #4A90E2;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .product-card h4 {
            margin: 0 0 10px 0;
            color: #333;
        }
        .price {
            font-size: 24px;
            font-weight: bold;
            color: #4A90E2;
            margin: 10px 0;
        }
        .rating {
            color: #666;
            margin: 5px 0;
        }
        .buy-button {
            display: inline-block;
            background: #FF9900;
            color: white;
            padding: 12px 24px;
            border-radius: 6px;
            text-decoration: none;
            font-weight: bold;
            margin-top: 10px;
            transition: background 0.3s;
        }
        .buy-button:hover {
            background: #E88800;
        }
        </style>
"""

        return html

    def create_complete_article(self, event_name, event_date, content, products):
        """Create full HTML article"""

        filename = event_name.lower().replace(' ', '-').replace(':', '')
        filename = re.sub(r'[^a-z0-9-]', '', filename)

        product_html = self.format_product_recommendations(products)

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{event_name} - Complete Guide | {self.config['name']}</title>
    <meta name="description" content="Complete guide to {event_name} with expert tips and recommendations.">
    <link rel="stylesheet" href="../style.css">
</head>
<body>
    <header class="site-header">
        <h1>🌠 {self.config['name'].upper()}</h1>
        <p>{self.config.get('tagline', 'Your trusted guide')}</p>
    </header>

    <main class="article-content">
        <div class="countdown-banner">
            <h1>🚀 {event_name}</h1>
            <p class="event-subtitle">Your Complete Guide</p>
            <div class="countdown-display" id="countdown">
                <div class="time-unit"><span id="days">--</span><label>Days</label></div>
                <div class="time-unit"><span id="hours">--</span><label>Hours</label></div>
                <div class="time-unit"><span id="minutes">--</span><label>Minutes</label></div>
                <div class="time-unit"><span id="seconds">--</span><label>Seconds</label></div>
            </div>
        </div>

        <article>
{content}

{product_html}
        </article>
    </main>

    <footer class="site-footer">
        <p>&copy; 2024 {self.config['name']}. All rights reserved.</p>
    </footer>

    <script>
        const targetDate = new Date('{event_date}').getTime();

        function updateCountdown() {{
            const now = new Date().getTime();
            const distance = targetDate - now;

            if (distance < 0) {{
                document.getElementById('countdown').innerHTML = '<p class="event-passed">Event has passed!</p>';
                return;
            }}

            const days = Math.floor(distance / (1000 * 60 * 60 * 24));
            const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((distance % (1000 * 60)) / 1000);

            document.getElementById('days').textContent = days;
            document.getElementById('hours').textContent = hours;
            document.getElementById('minutes').textContent = minutes;
            document.getElementById('seconds').textContent = seconds;
        }}

        updateCountdown();
        setInterval(updateCountdown, 1000);
    </script>
</body>
</html>"""

        article_path = self.articles_dir / f"{filename}.html"
        with open(article_path, 'w', encoding='utf-8') as f:
            f.write(html)

        return {
            "success": True,
            "filename": f"{filename}.html",
            "path": str(article_path),
            "url": f"https://{self.config['domain']}/articles/{filename}.html",
            "products_count": len(products)
        }

    def upload_to_website(self, local_file):
        """Upload article to live website"""
        try:
            ftp = ftplib.FTP(self.ftp_host)
            ftp.login(self.ftp_user, self.ftp_pass)

            try:
                ftp.cwd('/public_html/articles')
            except:
                ftp.mkd('/public_html/articles')
                ftp.cwd('/public_html/articles')

            filename = Path(local_file).name
            with open(local_file, 'rb') as f:
                ftp.storbinary(f'STOR {filename}', f)

            ftp.quit()
            return {"success": True, "message": "Uploaded successfully"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def process_user_question(self, user_message):
        """Main function: User question → Content + Products"""

        agent_name = self.config.get('agent_name', 'ASTRO 2.0')
        print(f"\n[{agent_name}] ({self.config['name']}): Processing...")
        print(f"Question: {user_message}")

        # Analyze intent
        intent = self.detect_user_intent(user_message)
        print(f"[OK] Intent: {intent.get('event_name')}")

        # Generate content
        content = self.generate_article_content(
            intent['event_name'],
            intent['event_type'],
            user_message
        )
        print(f"[OK] Content generated")

        # Select products
        products = self.select_products(intent.get('product_categories', []))
        print(f"[OK] {len(products)} products selected")

        # Create article
        event_date = (datetime.now() + timedelta(days=30)).strftime('%B %d, %Y %H:%M:%S UTC')
        result = self.create_complete_article(
            intent['event_name'],
            event_date,
            content,
            products
        )
        print(f"[OK] Article created: {result['filename']}")

        # Upload
        upload_result = self.upload_to_website(result['path'])
        print(f"[OK] Uploaded to website")

        return {
            "article_url": result['url'],
            "article_title": intent['event_name'],
            "products": products,
            "created_at": datetime.now().isoformat()
        }

# Website configurations
WEBSITES = {
    'eventfollowers': {
        'name': 'Event Followers',
        'agent_name': 'ASTRO',
        'ftp_host': '46.202.183.240',
        'ftp_user': 'u907901430.eventfollowers.com',
        'ftp_pass': 'Chillyflakes1$',
        'domain': 'eventfollowers.com',
        'niche': 'space events',
        'tagline': 'Countdown to Humanity\'s Greatest Moments',
        'product_categories': ['telescope', 'binoculars', 'camera', 'books', 'apps']
    },
    'longevityfutures': {
        'name': 'Longevity Futures',
        'agent_name': 'VITA',
        'ftp_host': '46.202.183.240',
        'ftp_user': 'u907901430.longevityfutures.online',
        'ftp_pass': 'Chillyflakes1$',
        'domain': 'longevityfutures.online',
        'niche': 'longevity',
        'tagline': 'Science-Backed Longevity Research',
        'product_categories': ['nmn', 'omega3', 'multivitamin', 'resveratrol']
    },
    'silentai': {
        'name': 'Silent-AI',
        'agent_name': 'SAGE',
        'ftp_host': '46.202.183.240',
        'ftp_user': 'u907901430.silent-ai.pro',
        'ftp_pass': 'Chillyflakes1$',
        'domain': 'silent-ai.pro',
        'niche': 'ai tools',
        'tagline': 'Discover AI Tools That Actually Work',
        'product_categories': ['ai_writing', 'ai_design', 'ai_video']
    }
}

if __name__ == "__main__":
    # Test with Event Followers
    print("="*60)
    print("ASTRO 2.0 - MULTI-WEBSITE TEST")
    print("="*60)

    # Initialize for Event Followers
    astro = AstroV2OpenAI(WEBSITES['eventfollowers'])

    question = "When can I see Jupiter tonight with a telescope?"
    result = astro.process_user_question(question)

    print("\n" + "="*60)
    print("SUCCESS!")
    print("="*60)
    print(f"Article: {result['article_url']}")
    print(f"Products: {len(result['products'])}")
