"""
BOOMER - LONGEVITY SALES AI
Next-Level Sales Agent for Longevity Futures
Blends with VITA's knowledge + Advanced selling capabilities
With PERSISTENT MEMORY - Remembers users across sessions
"""

import os
import json
from datetime import datetime
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
from astro_v2_openai import AstroV2OpenAI, WEBSITES

load_dotenv()

# Import GHOST for Amazon product finding
try:
    from ghost_agent import ghost_find_amazon_product
    GHOST_AVAILABLE = True
except ImportError:
    GHOST_AVAILABLE = False
    print("[BOOMER] GHOST not available - Amazon product finder disabled")


class BoomerMemory:
    """Persistent memory system for BOOMER - survives restarts"""

    def __init__(self, memory_file="boomer_memory.json"):
        self.memory_file = Path(__file__).parent / memory_file
        self.memory = self._load_memory()

    def _load_memory(self):
        """Load memory from file"""
        if self.memory_file.exists():
            try:
                with open(self.memory_file, 'r') as f:
                    return json.load(f)
            except:
                return {"users": {}, "stats": {"total_conversations": 0, "total_products_recommended": 0}}
        return {"users": {}, "stats": {"total_conversations": 0, "total_products_recommended": 0}}

    def _save_memory(self):
        """Save memory to file"""
        try:
            with open(self.memory_file, 'w') as f:
                json.dump(self.memory, f, indent=2, default=str)
        except Exception as e:
            print(f"[BOOMER] Memory save error: {e}")

    def get_user(self, email):
        """Get user profile by email"""
        return self.memory["users"].get(email, None)

    def create_user(self, email):
        """Create new user profile"""
        self.memory["users"][email] = {
            "email": email,
            "name": None,
            "first_seen": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
            "conversation_count": 0,
            "health_goals": [],
            "preferred_budget": None,
            "experience_level": "beginner",
            "products_viewed": [],
            "products_purchased": [],  # For future tracking
            "preferences": {},
            "conversation_history": [],
            "notes": []  # Things BOOMER learns about them
        }
        self._save_memory()
        return self.memory["users"][email]

    def get_or_create_user(self, email):
        """Get existing user or create new one"""
        user = self.get_user(email)
        if not user:
            user = self.create_user(email)
        return user

    def update_user(self, email, updates):
        """Update user profile"""
        if email in self.memory["users"]:
            self.memory["users"][email].update(updates)
            self.memory["users"][email]["last_seen"] = datetime.now().isoformat()
            self._save_memory()

    def set_user_name(self, email, name):
        """Remember user's name"""
        if email in self.memory["users"]:
            self.memory["users"][email]["name"] = name
            self._save_memory()

    def add_conversation(self, email, message, response, intent, products):
        """Add conversation to history"""
        if email in self.memory["users"]:
            self.memory["users"][email]["conversation_history"].append({
                "timestamp": datetime.now().isoformat(),
                "message": message,
                "response_preview": response[:200] + "..." if len(response) > 200 else response,
                "intent": intent,
                "products_recommended": [p["name"] for p in products[:3]]
            })
            self.memory["users"][email]["conversation_count"] += 1

            # Keep last 50 conversations per user
            if len(self.memory["users"][email]["conversation_history"]) > 50:
                self.memory["users"][email]["conversation_history"] = \
                    self.memory["users"][email]["conversation_history"][-50:]

            # Update health goals from intent
            for goal in intent.get("health_goals", []):
                if goal not in self.memory["users"][email]["health_goals"]:
                    self.memory["users"][email]["health_goals"].append(goal)

            # Update budget preference
            if intent.get("budget_tier"):
                self.memory["users"][email]["preferred_budget"] = intent["budget_tier"]

            # Update experience level
            if intent.get("experience_level"):
                self.memory["users"][email]["experience_level"] = intent["experience_level"]

            # Track products viewed
            for p in products[:5]:
                if p["name"] not in self.memory["users"][email]["products_viewed"]:
                    self.memory["users"][email]["products_viewed"].append(p["name"])

            # Update stats
            self.memory["stats"]["total_conversations"] += 1
            self.memory["stats"]["total_products_recommended"] += len(products)

            self._save_memory()

    def add_note(self, email, note):
        """Add a note about the user (learned fact)"""
        if email in self.memory["users"]:
            self.memory["users"][email]["notes"].append({
                "timestamp": datetime.now().isoformat(),
                "note": note
            })
            self._save_memory()

    def get_user_context(self, email):
        """Get context string for GPT about this user"""
        user = self.get_user(email)
        if not user:
            return "New user, no history."

        context_parts = []

        if user.get("name"):
            context_parts.append(f"User's name is {user['name']}.")

        if user.get("health_goals"):
            context_parts.append(f"Their health goals: {', '.join(user['health_goals'])}.")

        if user.get("preferred_budget"):
            context_parts.append(f"Budget preference: {user['preferred_budget']}.")

        if user.get("experience_level"):
            context_parts.append(f"Experience level: {user['experience_level']}.")

        if user.get("products_viewed"):
            recent_products = user["products_viewed"][-5:]
            context_parts.append(f"Previously viewed: {', '.join(recent_products)}.")

        if user.get("notes"):
            recent_notes = [n["note"] for n in user["notes"][-3:]]
            context_parts.append(f"Notes: {'; '.join(recent_notes)}")

        if user.get("conversation_count", 0) > 0:
            context_parts.append(f"This is conversation #{user['conversation_count'] + 1} with this user.")

        return " ".join(context_parts) if context_parts else "Returning user, limited history."

    def get_stats(self):
        """Get overall BOOMER stats"""
        return {
            "total_users": len(self.memory["users"]),
            "total_conversations": self.memory["stats"]["total_conversations"],
            "total_products_recommended": self.memory["stats"]["total_products_recommended"]
        }


class BoomerAgent:
    """
    BOOMER - The Ultimate Longevity Sales AI

    Features:
    - Personalized supplement recommendations based on health goals
    - Stack builder for complete protocols
    - Budget-conscious suggestions
    - Urgency and scarcity tactics (ethical)
    - Cross-sell and upsell intelligence
    - PERSISTENT MEMORY - Remembers users, names, preferences across sessions
    """

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.astro = AstroV2OpenAI(WEBSITES['longevityfutures'])
        self.products = self.astro.product_database
        self.memory = BoomerMemory()  # Persistent memory system

        # Health goal to product category mapping
        self.goal_mapping = {
            "energy": ["nmn", "nr", "coq10", "pqq", "ala", "vitamin_d"],
            "anti-aging": ["nmn", "nr", "resveratrol", "senolytics", "spermidine", "collagen"],
            "longevity": ["nmn", "nr", "resveratrol", "senolytics", "spermidine", "stacks"],
            "skin": ["collagen", "resveratrol", "vitamin_d", "omega3"],
            "sleep": ["sleep", "magnesium"],
            "brain": ["brain", "omega3", "magnesium", "nmn"],
            "heart": ["omega3", "coq10", "resveratrol", "berberine"],
            "gut": ["probiotics", "spermidine"],
            "joints": ["joint", "collagen", "omega3"],
            "metabolism": ["berberine", "ala", "coq10"],
            "immune": ["vitamin_d", "probiotics", "multivitamin"],
            "beginner": ["multivitamin", "omega3", "vitamin_d", "magnesium"],
            "advanced": ["nmn", "resveratrol", "senolytics", "spermidine", "stacks"]
        }

        # Budget tiers
        self.budget_tiers = {
            "budget": {"max": 50, "label": "Budget-Friendly"},
            "moderate": {"max": 100, "label": "Best Value"},
            "premium": {"max": 200, "label": "Premium Quality"},
            "unlimited": {"max": 9999, "label": "Maximum Results"}
        }

    def analyze_user_intent(self, message, user_email=None):
        """Analyze what the user is looking for using GPT - also extracts name"""

        # Get user context from memory
        user_context = ""
        if user_email:
            self.memory.get_or_create_user(user_email)
            user_context = self.memory.get_user_context(user_email)

        prompt = f"""Analyze this user message about longevity/health supplements.

User message: "{message}"
{f"Known about this user: {user_context}" if user_context else ""}

Extract:
1. health_goals: Array of goals (energy, anti-aging, longevity, skin, sleep, brain, heart, gut, joints, metabolism, immune)
2. experience_level: beginner, intermediate, or advanced
3. budget_tier: budget (<$50), moderate ($50-100), premium ($100-200), unlimited (>$200)
4. specific_products: Any specific supplements mentioned (NMN, resveratrol, etc.)
5. concerns: Any health concerns or conditions mentioned
6. urgency: low, medium, high
7. is_buying_signal: true if they seem ready to purchase
8. user_name: If they mention their name (e.g. "Hi I'm John", "My name is Sarah"), extract it. Otherwise null.
9. learned_facts: Array of any personal facts we should remember (age, health conditions, lifestyle, etc.)

Return as JSON.
"""

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are BOOMER, an expert longevity supplement advisor. Analyze user intent and return JSON. Be thorough in extracting names and facts."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )

        try:
            intent = json.loads(response.choices[0].message.content)

            # Save name if detected
            if user_email and intent.get("user_name"):
                self.memory.set_user_name(user_email, intent["user_name"])

            # Save any learned facts
            if user_email and intent.get("learned_facts"):
                for fact in intent["learned_facts"]:
                    self.memory.add_note(user_email, fact)

            return intent
        except:
            return {
                "health_goals": ["longevity"],
                "experience_level": "beginner",
                "budget_tier": "moderate",
                "specific_products": [],
                "concerns": [],
                "urgency": "medium",
                "is_buying_signal": False,
                "user_name": None,
                "learned_facts": []
            }

    def get_personalized_recommendations(self, intent, max_products=8):
        """Get personalized product recommendations based on user intent"""

        recommendations = []
        ghost_products = []  # Products found via GHOST
        categories_to_check = set()

        # Check if user asked for specific products not in our database
        specific_products = intent.get("specific_products", [])
        searching_for = []  # Track what we're asking GHOST to find

        for product_query in specific_products:
            if not self.check_if_product_in_database(product_query):
                searching_for.append(product_query)
                # Ask GHOST to find it on Amazon
                found = self.ask_ghost_for_product(product_query)
                if found:
                    ghost_products.extend(found)

        # Map goals to categories
        for goal in intent.get("health_goals", ["longevity"]):
            if goal in self.goal_mapping:
                categories_to_check.update(self.goal_mapping[goal])

        # Add experience-based categories
        exp_level = intent.get("experience_level", "beginner")
        if exp_level in self.goal_mapping:
            categories_to_check.update(self.goal_mapping[exp_level])

        # Get budget max
        budget_tier = intent.get("budget_tier", "moderate")
        budget_max = self.budget_tiers.get(budget_tier, self.budget_tiers["moderate"])["max"]

        # Collect products from relevant categories
        for category in categories_to_check:
            if category in self.products:
                for product in self.products[category]:
                    if product["price"] <= budget_max:
                        product["_category"] = category
                        product["_match_score"] = self._calculate_match_score(product, intent)
                        recommendations.append(product)

        # Sort by match score and rating
        recommendations.sort(key=lambda x: (x["_match_score"], x["rating"]), reverse=True)

        # Remove duplicates and limit
        seen = set()
        unique_recs = []
        for rec in recommendations:
            if rec["name"] not in seen:
                seen.add(rec["name"])
                unique_recs.append(rec)
                if len(unique_recs) >= max_products:
                    break

        # Add GHOST-found products at the beginning (they're what user specifically asked for)
        if ghost_products:
            unique_recs = ghost_products + unique_recs
            unique_recs = unique_recs[:max_products]  # Limit total

        # If we searched for something, also add complementary products to keep them engaged
        if searching_for:
            for query in searching_for:
                complementary = self.get_complementary_products(query, unique_recs, max_extras=2)
                unique_recs.extend(complementary)

        return unique_recs

    def _calculate_match_score(self, product, intent):
        """Calculate how well a product matches user intent"""
        score = 0

        # Rating boost
        score += product["rating"] * 2

        # Price efficiency (lower price = higher score for budget users)
        if intent.get("budget_tier") == "budget":
            score += (100 - product["price"]) / 10

        # Specific product mention boost
        product_name_lower = product["name"].lower()
        for specific in intent.get("specific_products", []):
            if specific.lower() in product_name_lower:
                score += 10

        # Best seller/premium boost
        if "Best Seller" in product.get("category", "") or "Premium" in product.get("category", ""):
            score += 3

        return score

    def is_health_related(self, query):
        """
        Check if a product query is health/wellness related.

        BOOMER only searches Amazon for health products.
        Off-topic requests get redirected to AskMarket.
        """
        query_lower = query.lower()

        # Health/wellness keywords - these are OK to search
        health_keywords = [
            # Supplements & vitamins
            "vitamin", "supplement", "mineral", "capsule", "tablet", "powder",
            "nmn", "nad", "resveratrol", "collagen", "omega", "fish oil",
            "probiotic", "prebiotic", "enzyme", "antioxidant", "coq10",
            "magnesium", "zinc", "iron", "calcium", "potassium",
            "b12", "b-12", "d3", "d-3", "k2", "k-2", "folate", "biotin",

            # Health conditions & goals
            "longevity", "anti-aging", "antiaging", "aging", "health",
            "energy", "sleep", "stress", "anxiety", "mood", "brain",
            "memory", "focus", "cognitive", "joint", "bone", "muscle",
            "heart", "cardio", "blood pressure", "cholesterol", "blood sugar",
            "immune", "immunity", "gut", "digestive", "liver", "kidney",

            # Skin & beauty (health-related)
            "skin", "wrinkle", "collagen", "retinol", "hyaluronic",
            "moisturizer", "serum", "anti-aging cream", "sunscreen", "spf",

            # Fitness & wellness
            "protein", "amino", "creatine", "bcaa", "pre-workout", "post-workout",
            "fitness", "exercise", "workout", "recovery", "muscle",
            "weight loss", "metabolism", "fat burner", "keto",

            # Health devices
            "blood pressure monitor", "glucose", "thermometer", "pulse oximeter",
            "fitness tracker", "scale", "massage", "tens", "red light",

            # Brands known for health products
            "thorne", "life extension", "jarrow", "now foods", "nordic naturals",
            "garden of life", "nature made", "solgar", "pure encapsulations",
            "nutricost", "bulk supplements", "sports research", "doctor's best",

            # General health terms
            "wellness", "natural", "organic", "herbal", "holistic",
            "medical", "therapeutic", "clinical", "pharmaceutical"
        ]

        # Check if query contains any health keyword
        for keyword in health_keywords:
            if keyword in query_lower:
                return True

        # Use GPT for edge cases - quick check
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You determine if a product is health/wellness related. Answer only 'yes' or 'no'."},
                    {"role": "user", "content": f"Is this product health, wellness, supplement, skincare, or fitness related? Product: {query}"}
                ],
                max_tokens=5,
                temperature=0
            )
            answer = response.choices[0].message.content.strip().lower()
            return "yes" in answer
        except:
            return False

    def ask_ghost_for_product(self, product_query):
        """
        BOOMER asks GHOST to find an Amazon product

        This is called when user asks for something not in our database.
        GHOST returns affiliate-compliant Amazon search links.

        FILTER: Only health/wellness products allowed.
        Off-topic requests return None (handled elsewhere).
        """
        if not GHOST_AVAILABLE:
            return None

        # Check if this is a health-related product
        if not self.is_health_related(product_query):
            print(f"[BOOMER] '{product_query}' is not health-related - skipping Amazon search")
            return None  # Will trigger redirect to AskMarket

        try:
            print(f"[BOOMER] Asking GHOST to find: {product_query}")
            result = ghost_find_amazon_product(product_query, max_results=2)

            if result.get("success") and result.get("products"):
                print(f"[BOOMER] GHOST found {len(result['products'])} products")
                return result["products"]
            return None

        except Exception as e:
            print(f"[BOOMER] Error asking GHOST: {e}")
            return None

    def get_complementary_products(self, original_query, current_products, max_extras=3):
        """
        Get complementary products to show while we find what they asked for.

        Example: User asks for "Jarrow MK-7" (not in database)
        → We show them related products: Vitamin D3, Calcium, Bone Support

        This keeps them engaged and might lead to additional sales!
        """

        # Determine what category the query might relate to
        query_lower = original_query.lower()

        # Map query keywords to complementary categories
        complementary_map = {
            # If they want vitamin K → suggest bone/heart health
            "vitamin k": ["vitamin_d", "omega3", "calcium", "magnesium"],
            "mk-7": ["vitamin_d", "omega3", "magnesium"],
            "mk7": ["vitamin_d", "omega3", "magnesium"],

            # If they want specific brands not in DB → suggest similar categories
            "jarrow": ["multivitamin", "probiotics", "omega3"],
            "now foods": ["vitamin_d", "magnesium", "omega3"],
            "life extension": ["nmn", "resveratrol", "coq10"],
            "thorne": ["magnesium", "vitamin_d", "multivitamin"],

            # Skin/beauty products → suggest collagen and related
            "skin": ["collagen", "resveratrol", "omega3"],
            "wrinkle": ["collagen", "resveratrol", "vitamin_d"],
            "cream": ["collagen", "omega3", "vitamin_d"],
            "beauty": ["collagen", "resveratrol", "probiotics"],
            "anti-aging": ["collagen", "nmn", "resveratrol", "senolytics"],

            # Joint/bone → suggest related
            "joint": ["joint", "collagen", "omega3", "vitamin_d"],
            "bone": ["vitamin_d", "magnesium", "collagen"],
            "arthritis": ["joint", "omega3", "collagen"],

            # Energy → mitochondrial support
            "energy": ["coq10", "nmn", "pqq", "ala"],
            "fatigue": ["coq10", "nmn", "vitamin_d", "magnesium"],

            # Sleep
            "sleep": ["sleep", "magnesium"],
            "melatonin": ["sleep", "magnesium"],

            # Gut health
            "probiotic": ["probiotics", "spermidine"],
            "digestive": ["probiotics", "berberine"],
            "gut": ["probiotics", "omega3"],

            # Heart health
            "heart": ["omega3", "coq10", "resveratrol"],
            "cholesterol": ["omega3", "berberine", "resveratrol"],
            "blood pressure": ["omega3", "coq10", "magnesium"],

            # Brain/cognitive
            "brain": ["brain", "omega3", "nmn"],
            "memory": ["brain", "omega3", "resveratrol"],
            "focus": ["brain", "nmn", "coq10"],
        }

        # Find matching complementary categories
        categories_to_suggest = set()
        for keyword, categories in complementary_map.items():
            if keyword in query_lower:
                categories_to_suggest.update(categories)

        # Default fallback: suggest popular longevity products
        if not categories_to_suggest:
            categories_to_suggest = {"collagen", "omega3", "vitamin_d", "magnesium"}

        # Get products from those categories
        complementary = []
        current_names = {p.get("name", "").lower() for p in current_products}

        for category in categories_to_suggest:
            if category in self.products:
                for product in self.products[category][:2]:  # Top 2 from each
                    if product["name"].lower() not in current_names:
                        product["_complementary"] = True
                        product["_why"] = f"Popular {category.replace('_', ' ')} choice"
                        complementary.append(product)
                        if len(complementary) >= max_extras:
                            break
            if len(complementary) >= max_extras:
                break

        return complementary[:max_extras]

    def check_if_product_in_database(self, query):
        """Check if we have this product or similar in our database"""
        query_lower = query.lower()

        for category, products in self.products.items():
            for product in products:
                if query_lower in product["name"].lower():
                    return True
                # Check for brand names
                for keyword in query_lower.split():
                    if len(keyword) > 3 and keyword in product["name"].lower():
                        return True
        return False

    def build_stack(self, intent):
        """Build a complete supplement stack based on goals"""

        stack = {
            "foundation": [],
            "core": [],
            "advanced": [],
            "total_price": 0
        }

        # Foundation (everyone needs these)
        foundation_cats = ["vitamin_d", "omega3", "magnesium"]
        for cat in foundation_cats:
            if cat in self.products:
                # Get best value option
                product = min(self.products[cat], key=lambda x: x["price"])
                stack["foundation"].append(product)
                stack["total_price"] += product["price"]

        # Core (based on main goals)
        main_goals = intent.get("health_goals", ["longevity"])[:2]
        core_cats = set()
        for goal in main_goals:
            if goal in self.goal_mapping:
                core_cats.update(self.goal_mapping[goal][:2])

        for cat in list(core_cats)[:3]:
            if cat in self.products and cat not in foundation_cats:
                # Get highest rated
                product = max(self.products[cat], key=lambda x: x["rating"])
                stack["core"].append(product)
                stack["total_price"] += product["price"]

        # Advanced (only for advanced users)
        if intent.get("experience_level") == "advanced":
            advanced_cats = ["spermidine", "senolytics", "pqq"]
            for cat in advanced_cats[:2]:
                if cat in self.products:
                    product = max(self.products[cat], key=lambda x: x["rating"])
                    stack["advanced"].append(product)
                    stack["total_price"] += product["price"]

        return stack

    def generate_sales_response(self, message, user_email=None):
        """Generate a complete sales response with recommendations"""

        # Analyze intent (also handles name extraction and memory)
        intent = self.analyze_user_intent(message, user_email)

        # Get recommendations
        recommendations = self.get_personalized_recommendations(intent)

        # Build stack if they seem interested in comprehensive approach
        stack = None
        if any(g in ["longevity", "anti-aging", "advanced"] for g in intent.get("health_goals", [])):
            stack = self.build_stack(intent)

        # Get user context from memory for personalized response
        user_context = ""
        user_name = None
        if user_email:
            user = self.memory.get_user(user_email)
            if user:
                user_name = user.get("name")
                user_context = self.memory.get_user_context(user_email)

        # Generate personalized response using GPT
        products_json = json.dumps([{
            "name": p["name"],
            "price": p["price"],
            "rating": p["rating"],
            "category": p.get("category", ""),
            "amazon_link": f"https://amazon.com/dp/{p['amazon']}?tag=paulstxmbur-20" if "amazon" in p else None
        } for p in recommendations], indent=2)

        stack_json = json.dumps(stack, indent=2) if stack else "null"

        prompt = f"""You are BOOMER, the friendly and knowledgeable longevity supplement advisor for Longevity Futures.

User asked: "{message}"

IMPORTANT: You specialize in health, longevity, and wellness products ONLY.
If the user asks about non-health products (electronics, furniture, etc.), politely explain that you focus on longevity/health and suggest they visit askmarket.store for other products.

{"USER CONTEXT (what we know about them): " + user_context if user_context else "This is a new user."}

User Intent Analysis:
- Health Goals: {intent.get('health_goals', [])}
- Experience Level: {intent.get('experience_level', 'beginner')}
- Budget: {intent.get('budget_tier', 'moderate')}
- Urgency: {intent.get('urgency', 'medium')}
- Ready to Buy: {intent.get('is_buying_signal', False)}

Recommended Products:
{products_json}

{"Stack Suggestion:" + stack_json if stack else ""}

Write a helpful, persuasive response that:
1. {"Address them by name (" + user_name + ") naturally in your response" if user_name else "If this is their first time, welcome them warmly"}
2. If they're returning, acknowledge you remember them and their goals
3. Acknowledges their health goals
4. Explains WHY these products will help (briefly, with science)
5. Recommends 2-4 top products with prices and links
6. If they're a beginner, suggest starting with 1-2 products
7. If they're advanced, mention the stack option
8. Include a subtle call-to-action
9. Be warm, helpful, not pushy

Format with markdown. Include product links.
Keep response under 300 words.
"""

        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are BOOMER, an expert longevity advisor. Be helpful, knowledgeable, and subtly persuasive. Use science to back recommendations. If you know the user's name, use it naturally."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )

        response_text = response.choices[0].message.content

        # Save conversation to memory
        if user_email:
            self.memory.add_conversation(
                user_email,
                message,
                response_text,
                intent,
                recommendations
            )

        return {
            "response": response_text,
            "products": recommendations[:5],
            "stack": stack,
            "intent": intent,
            "user_name": user_name
        }

    def format_products_html(self, products, amazon_tag="paulstxmbur-20"):
        """Format products as HTML cards for web display"""

        html = '<div class="boomer-recommendations" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0;">'

        for product in products[:6]:
            stars = "★" * int(product['rating']) + "☆" * (5 - int(product['rating']))

            if 'amazon' in product:
                link = f"https://amazon.com/dp/{product['amazon']}?tag={amazon_tag}"
            else:
                link = "https://www.awin1.com/cread.php?awinmid=87875&awinaffid=2656702&ued=https%3A%2F%2Fwww.i-supplements.com"

            html += f'''
            <div style="background: white; border-radius: 12px; padding: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); border-left: 4px solid #10b981;">
                <h4 style="margin: 0 0 10px 0; color: #1a1a2e; font-size: 1em;">{product['name']}</h4>
                <p style="color: #10b981; font-size: 1.3em; font-weight: bold; margin: 5px 0;">${product['price']}</p>
                <p style="color: #f59e0b; margin: 5px 0;">{stars}</p>
                <span style="background: #f0fdf4; color: #166534; padding: 3px 10px; border-radius: 15px; font-size: 0.8em;">{product.get('category', 'Supplement')}</span>
                <a href="{link}" target="_blank" style="display: block; background: linear-gradient(135deg, #10b981, #059669); color: white; text-align: center; padding: 12px; border-radius: 8px; text-decoration: none; margin-top: 15px; font-weight: 600;">View on Amazon</a>
            </div>
            '''

        html += '</div>'
        return html


# Singleton instance
boomer = BoomerAgent()


def get_boomer_response(message, user_email=None):
    """Main entry point for BOOMER responses"""
    return boomer.generate_sales_response(message, user_email)


if __name__ == "__main__":
    # Test BOOMER
    print("=" * 60)
    print("BOOMER - LONGEVITY SALES AI TEST")
    print("=" * 60)

    test_messages = [
        "I'm 45 and want to start with anti-aging supplements, budget around $100",
        "What's the best NMN supplement?",
        "I want to build a complete longevity stack, money is not an issue",
        "Help me sleep better and have more energy"
    ]

    for msg in test_messages:
        print(f"\nUser: {msg}")
        print("-" * 40)
        result = get_boomer_response(msg)
        print(result["response"])
        print(f"\nProducts recommended: {len(result['products'])}")
        print("=" * 60)
