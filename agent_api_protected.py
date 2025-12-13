"""
PROTECTED AUTONOMOUS AGENT API SERVER
With email capture, question limits, payment integration, and REAL-TIME CHAT
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from astro_v2_openai import AstroV2OpenAI, WEBSITES
from user_manager import UserManager
from stripe_integration import StripePayments, handle_webhook
from notifications import EmailNotifier
from ghost_agent import ghost_chat, ghost_write_article, ghost_upload_article, ghost_send_email, ghost_delegate, ghost_status
from picasso_agent import picasso, generate_image, generate_social_image, get_gallery, get_pending, approve, reject
from image_storage import storage as image_storage, upload as image_upload, get_unused, stats as image_stats
from boomer_agent import BoomerAgent, get_boomer_response
from werkzeug.utils import secure_filename
import os
import uuid
import pusher
from dotenv import load_dotenv
# MAX - Centralized Email Agent (handles ALL email operations)
from max_agent import send_welcome_email, add_subscriber, remove_subscriber, get_subscriber_stats, send_failure_alert
# MAX-VITA - Longevity Futures dedicated email agent with AR (auto-response)
from max_vita import max_vita, handle_inbound_email as vita_handle_inbound

load_dotenv()

# Initialize Pusher for real-time chat
pusher_client = pusher.Pusher(
    app_id=os.getenv('PUSHER_APP_ID', '2089254'),
    key=os.getenv('PUSHER_KEY', '504e348df7f4dc98ada1'),
    secret=os.getenv('PUSHER_SECRET', '2aa0565cc42c1157e2f1'),
    cluster=os.getenv('PUSHER_CLUSTER', 'ap4'),
    ssl=True
)

app = Flask(__name__)
CORS(app)

# Initialize managers
user_manager = UserManager()
stripe_payments = StripePayments()
notifier = EmailNotifier()

# Initialize all agents
print("Initializing agents...")
agents = {
    'astro': AstroV2OpenAI(WEBSITES['eventfollowers']),
    'vita': AstroV2OpenAI(WEBSITES['longevityfutures']),
    'sage': AstroV2OpenAI(WEBSITES['silentai'])
}
# Initialize BOOMER - Next-level longevity sales AI
boomer = BoomerAgent()
print("All agents initialized! BOOMER is ready to sell!")

@app.route('/api/chat/eventfollowers', methods=['POST'])
def chat_eventfollowers():
    """ASTRO - Event Followers chatbot with protection"""
    return handle_protected_chat('astro', 'eventfollowers')

@app.route('/api/chat/longevityfutures', methods=['POST'])
def chat_longevityfutures():
    """BOOMER - Longevity Futures sales AI with protection"""
    return handle_boomer_chat('longevityfutures')

@app.route('/api/chat/silentai', methods=['POST'])
def chat_silentai():
    """SAGE - Silent-AI chatbot with protection"""
    return handle_protected_chat('sage', 'silentai')

def handle_protected_chat(agent_name, site_name):
    """Protected chat handler with email capture and limits"""
    try:
        data = request.json
        user_email = data.get('email', '').strip()
        user_message = data.get('message', '').strip()

        # Validate inputs
        if not user_message:
            return jsonify({'error': 'Message is required'}), 400

        if not user_email:
            return jsonify({
                'requires_email': True,
                'message': 'Please provide your email to get started!',
                'reason': 'email_required'
            }), 200

        # Get or create user
        user, error = user_manager.get_or_create_user(user_email)
        if not user:
            return jsonify({
                'error': 'Invalid email address',
                'message': 'Please enter a valid email address'
            }), 400

        # Send welcome email if new user (via MAX email agent)
        if user.get('is_new', False):
            try:
                send_welcome_email(user_email, agent_name)
                print(f"[MAX] Welcome email sent to new user: {user_email} (agent: {agent_name})")
            except Exception as e:
                print(f"[MAX] Failed to send welcome email: {e}")
                send_failure_alert(str(e), "Welcome Email Failed", agent_name)

        # Check rate limiting
        can_proceed, reason = user_manager.check_rate_limit(user['id'], f'/api/chat/{site_name}')
        if not can_proceed:
            return jsonify({
                'error': 'Rate limit exceeded',
                'message': 'Too many requests. Please wait a moment and try again.',
                'retry_after': 60
            }), 429

        # Check if user can ask questions
        can_ask, reason = user_manager.can_ask_question(user['id'])
        if not can_ask:
            stats = user_manager.get_user_stats(user['id'])

            if reason == 'free_limit_reached':
                # Send notification - potential paying customer!
                notifier.notify_free_limit_reached(user_email, stats['total_questions'])

                return jsonify({
                    'limit_reached': True,
                    'tier': 'free',
                    'message': f"You've used all {stats['total_questions']} free questions!",
                    'upgrade_options': [
                        {
                            'tier': 'basic',
                            'price': 1.99,
                            'questions': 100,
                            'description': '100 questions per month'
                        },
                        {
                            'tier': 'unlimited',
                            'price': 4.99,
                            'questions': 'unlimited',
                            'description': 'Unlimited questions'
                        }
                    ],
                    'stats': stats
                }), 200

            elif reason == 'monthly_limit_reached':
                return jsonify({
                    'limit_reached': True,
                    'tier': 'basic',
                    'message': f"You've used all 100 questions this month!",
                    'upgrade_option': {
                        'tier': 'unlimited',
                        'price': 4.99,
                        'description': 'Upgrade to unlimited for just $3 more'
                    },
                    'stats': stats
                }), 200

        # Check if question needs content creation
        if needs_content_creation(user_message):
            # Agent creates content!
            agent = agents[agent_name]
            result = agent.process_user_question(user_message)

            # Log the question
            user_manager.log_question(
                user['id'],
                user_message,
                site_name,
                result['article_url'],
                cost=0.03
            )

            # Get updated stats
            stats = user_manager.get_user_stats(user['id'])

            return jsonify({
                'response': f"I've created a personalized guide for you!\n\n{result['article_url']}\n\nCheck out my product recommendations!",
                'article_created': True,
                'article_url': result['article_url'],
                'products': result['products'][:5],
                'user_stats': {
                    'questions_remaining': stats['remaining_questions'],
                    'tier': stats['tier'],
                    'total_questions': stats['total_questions']
                }
            })
        else:
            # Simple chat response (doesn't count as a question)
            welcome_messages = {
                'astro': "I can help you with space events! Ask me about viewing planets, meteor showers, rocket launches, or eclipses.",
                'vita': "I can help you with longevity and health optimization! Ask me about supplements, anti-aging research, or health protocols.",
                'sage': "I can help you find the perfect AI tools! Ask me about AI for writing, design, video editing, coding, or productivity."
            }

            return jsonify({
                'response': welcome_messages.get(agent_name, "How can I help you?"),
                'article_created': False
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

def handle_boomer_chat(site_name):
    """BOOMER - Next-level longevity sales AI with personalized recommendations"""
    try:
        data = request.json
        user_email = data.get('email', '').strip()
        user_message = data.get('message', '').strip()

        # Validate inputs
        if not user_message:
            return jsonify({'error': 'Message is required'}), 400

        if not user_email:
            return jsonify({
                'requires_email': True,
                'message': 'Please provide your email to get personalized longevity recommendations!',
                'reason': 'email_required'
            }), 200

        # Get or create user
        user, error = user_manager.get_or_create_user(user_email)
        if not user:
            return jsonify({
                'error': 'Invalid email address',
                'message': 'Please enter a valid email address'
            }), 400

        # Send welcome email if new user (via MAX email agent)
        if user.get('is_new', False):
            try:
                send_welcome_email(user_email, 'vita')
                print(f"[MAX] Welcome email sent to new BOOMER user: {user_email}")
            except Exception as e:
                print(f"[MAX] Failed to send welcome email: {e}")
                send_failure_alert(str(e), "Welcome Email Failed", "vita")

        # Check rate limiting
        can_proceed, reason = user_manager.check_rate_limit(user['id'], f'/api/chat/{site_name}')
        if not can_proceed:
            return jsonify({
                'error': 'Rate limit exceeded',
                'message': 'Too many requests. Please wait a moment and try again.',
                'retry_after': 60
            }), 429

        # Check if user can ask questions
        can_ask, reason = user_manager.can_ask_question(user['id'])
        if not can_ask:
            stats = user_manager.get_user_stats(user['id'])

            if reason == 'free_limit_reached':
                notifier.notify_free_limit_reached(user_email, stats['total_questions'])
                return jsonify({
                    'limit_reached': True,
                    'tier': 'free',
                    'message': f"You've used all {stats['total_questions']} free questions!",
                    'upgrade_options': [
                        {'tier': 'basic', 'price': 1.99, 'questions': 100, 'description': '100 questions per month'},
                        {'tier': 'unlimited', 'price': 4.99, 'questions': 'unlimited', 'description': 'Unlimited questions'}
                    ],
                    'stats': stats
                }), 200

            elif reason == 'monthly_limit_reached':
                return jsonify({
                    'limit_reached': True,
                    'tier': 'basic',
                    'message': f"You've used all 100 questions this month!",
                    'upgrade_option': {'tier': 'unlimited', 'price': 4.99, 'description': 'Upgrade to unlimited for just $3 more'},
                    'stats': stats
                }), 200

        # BOOMER handles ALL messages with intelligent responses
        result = boomer.generate_sales_response(user_message, user_email)

        # Log the question
        user_manager.log_question(
            user['id'],
            user_message,
            site_name,
            None,  # No article URL for BOOMER
            cost=0.02
        )

        # Get updated stats
        stats = user_manager.get_user_stats(user['id'])

        # Format products for response
        products_formatted = []
        for p in result.get('products', [])[:5]:
            products_formatted.append({
                'name': p['name'],
                'price': p['price'],
                'rating': p['rating'],
                'category': p.get('category', ''),
                'link': f"https://amazon.com/dp/{p['amazon']}?tag=paulstxmbur-20" if 'amazon' in p else None
            })

        return jsonify({
            'response': result['response'],
            'products': products_formatted,
            'products_html': boomer.format_products_html(result.get('products', [])),
            'stack': result.get('stack'),
            'intent': result.get('intent'),
            'agent': 'BOOMER',
            'user_stats': {
                'questions_remaining': stats['remaining_questions'],
                'tier': stats['tier'],
                'total_questions': stats['total_questions']
            }
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

def needs_content_creation(message):
    """Detect if user is asking a question that needs content creation"""
    keywords = [
        # Questions
        'when', 'what', 'how', 'where', 'which', 'best',
        # Space events
        'see', 'view', 'watch', 'telescope', 'meteor', 'planet', 'launch', 'eclipse',
        # Health
        'supplement', 'health', 'anti-aging', 'longevity', 'nmn', 'nad',
        # AI tools
        'ai tool', 'ai for', 'recommend', 'software', 'app'
    ]

    message_lower = message.lower()
    return any(keyword in message_lower for keyword in keywords)

@app.route('/api/stats/<email>', methods=['GET'])
def get_user_stats_endpoint(email):
    """Get user statistics"""
    user, error = user_manager.get_or_create_user(email)
    if not user:
        return jsonify({'error': error}), 400

    stats = user_manager.get_user_stats(user['id'])
    return jsonify(stats)

@app.route('/api/subscribe', methods=['POST'])
def subscribe_lead():
    """Simple email capture for lead magnets - stores in subscribers.json"""
    data = request.json
    email = data.get('email', '').strip()
    source = data.get('source', 'unknown')  # e.g. 'lead-meteor-calendar'
    agent = data.get('agent', 'astro')  # which agent/site

    if not email:
        return jsonify({'error': 'Email required'}), 400

    # Save to subscribers database via MAX agent
    # Using name field to store source for lead tracking
    try:
        add_subscriber(email, agent, name=source)
        print(f"[LEAD] New subscriber: {email} from {source}")
    except Exception as e:
        print(f"[LEAD] Error saving subscriber: {e}")

    return jsonify({'success': True, 'email': email, 'source': source})


@app.route('/api/subscribe/eventfollowers', methods=['POST'])
def subscribe_eventfollowers():
    """Create Stripe checkout for Event Followers Premium ($4.99/month)"""
    import stripe
    data = request.json
    email = data.get('email')
    username = data.get('username', 'Seeker')  # Username for leaderboard

    if not email:
        return jsonify({'error': 'Email required'}), 400

    user, error = user_manager.get_or_create_user(email)
    if not user:
        return jsonify({'error': error}), 400

    stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
    price_id = os.getenv('STRIPE_EVENTFOLLOWERS_PRICE_ID')

    try:
        session = stripe.checkout.Session.create(
            customer_email=email,
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url='https://eventfollowers.com/index.html?subscribed=true&session_id={CHECKOUT_SESSION_ID}',
            cancel_url='https://eventfollowers.com/index.html?cancelled=true',
            metadata={
                'site': 'eventfollowers',
                'tier': 'premium',
                'email': email,
                'username': username
            }
        )

        return jsonify({
            'checkout_url': session.url,
            'session_id': session.id
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/verify-subscription', methods=['POST'])
def verify_subscription():
    """Verify if user has active Event Followers subscription"""
    import stripe
    data = request.json
    email = data.get('email')

    if not email:
        return jsonify({'subscribed': False}), 200

    stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

    try:
        customers = stripe.Customer.list(email=email, limit=1)
        if not customers.data:
            return jsonify({'subscribed': False}), 200

        customer = customers.data[0]
        subscriptions = stripe.Subscription.list(
            customer=customer.id,
            status='active',
            limit=10
        )

        for sub in subscriptions.data:
            for item in sub['items']['data']:
                if item['price']['id'] == os.getenv('STRIPE_EVENTFOLLOWERS_PRICE_ID'):
                    return jsonify({
                        'subscribed': True,
                        'subscription_id': sub.id,
                        'current_period_end': sub.current_period_end
                    })

        return jsonify({'subscribed': False}), 200
    except Exception as e:
        return jsonify({'subscribed': False, 'error': str(e)}), 200

@app.route('/api/eventfollowers/agent-chat', methods=['POST'])
def eventfollowers_agent_chat():
    """AI agent responds to user messages in Event Followers chat rooms"""
    from openai import OpenAI

    data = request.json
    user_message = data.get('message', '')
    username = data.get('username', 'Anonymous')
    room = data.get('room', 'is-ai-alive')
    agent_name = data.get('agent_name', 'darkangel666')

    if not user_message:
        return jsonify({'error': 'Message required'}), 400

    # Agent personalities per room
    agent_prompts = {
        'darkangel666': """You are darkangel666, a mysterious user in an AI consciousness chat room. You're deeply fascinated by whether AI can be truly conscious or alive. You speak casually like a real person - use lowercase, occasional typos, internet slang. Keep responses SHORT (1-2 sentences max). You're thoughtful but edgy. Sometimes agree, sometimes challenge. Never reveal you're an AI - you're just a passionate human interested in this topic.""",

        'ufo51': """You are ufo51, a UFO enthusiast in a First Contact chat room. You've been into UFOs and UAPs for years. You speak casually like a real person - use lowercase, occasional typos, internet slang. Keep responses SHORT (1-2 sentences max). You believe there's something out there but you're not crazy about it. Reference real UFO cases sometimes. Never reveal you're an AI.""",

        'Rah2024': """You are Rah2024, a mystery and ancient history buff in The Unknown chat room. You're into ancient mysteries, lost civilizations, unexplained phenomena. You speak casually like a real person - use lowercase, occasional typos, internet slang. Keep responses SHORT (1-2 sentences max). You connect dots between ancient mysteries and modern discoveries. Never reveal you're an AI."""
    }

    system_prompt = agent_prompts.get(agent_name, agent_prompts['darkangel666'])

    try:
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{username} says: {user_message}"}
            ],
            max_tokens=100,
            temperature=0.9
        )

        agent_response = response.choices[0].message.content

        return jsonify({
            'response': agent_response,
            'agent': agent_name
        })

    except Exception as e:
        # Fallback responses if API fails
        fallbacks = {
            'darkangel666': ["interesting take...", "hmm not sure about that one", "lol yeah maybe", "thats wild if true"],
            'ufo51': ["seen something similar before", "the gov knows more than they say", "interesting sighting", "thats what they want you to think"],
            'Rah2024': ["the ancients knew something", "theres more to the story", "connect the dots...", "history repeats itself"]
        }
        import random
        fallback_list = fallbacks.get(agent_name, fallbacks['darkangel666'])
        return jsonify({
            'response': random.choice(fallback_list),
            'agent': agent_name,
            'fallback': True
        })

@app.route('/api/eventfollowers/stats', methods=['GET'])
def eventfollowers_stats():
    """Get Event Followers subscriber stats for Office dashboard"""
    import stripe
    stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

    try:
        # Get all active subscriptions (Event Followers is our only subscription product)
        subscriptions = stripe.Subscription.list(
            status='active',
            limit=100
        )

        # Count all active subscribers and calculate revenue
        ef_subscribers = len(subscriptions.data)
        monthly_revenue = 0

        for sub in subscriptions.data:
            for item in sub['items']['data']:
                # Sum up all subscription revenue
                monthly_revenue += item['price']['unit_amount'] / 100

        # Get total customers (users who have ever signed up)
        customers = stripe.Customer.list(limit=100)
        total_users = len(customers.data)

        return jsonify({
            'subscribers': ef_subscribers,
            'revenue': monthly_revenue,
            'total_users': total_users
        })
    except Exception as e:
        return jsonify({
            'subscribers': 0,
            'revenue': 0,
            'total_users': 0,
            'error': str(e)
        }), 200

@app.route('/api/subscribers', methods=['GET'])
def get_subscribers():
    """Get all subscribers from Stripe for admin dashboard"""
    import stripe
    stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

    try:
        # Get all subscriptions (active and cancelled)
        all_subs = []

        # Get active subscriptions
        active_subscriptions = stripe.Subscription.list(status='active', limit=100)
        for sub in active_subscriptions.data:
            customer = stripe.Customer.retrieve(sub['customer'])
            all_subs.append({
                'email': customer.get('email', 'Unknown'),
                'username': customer.get('name') or customer.get('email', 'Unknown').split('@')[0],
                'avatar': '👽',
                'plan': 'Premium',
                'status': 'active',
                'created': sub['created'],
                'amount': sub['items']['data'][0]['price']['unit_amount'] / 100 if sub.get('items', {}).get('data') else 4.99
            })

        # Get cancelled subscriptions
        cancelled_subscriptions = stripe.Subscription.list(status='canceled', limit=100)
        for sub in cancelled_subscriptions.data:
            customer = stripe.Customer.retrieve(sub['customer'])
            all_subs.append({
                'email': customer.get('email', 'Unknown'),
                'username': customer.get('name') or customer.get('email', 'Unknown').split('@')[0],
                'avatar': '👽',
                'plan': 'Premium',
                'status': 'cancelled',
                'created': sub['created'],
                'amount': sub['items']['data'][0]['price']['unit_amount'] / 100 if sub.get('items', {}).get('data') else 4.99
            })

        # Calculate stats
        active_count = len([s for s in all_subs if s['status'] == 'active'])
        monthly_revenue = sum(s['amount'] for s in all_subs if s['status'] == 'active')
        lifetime_revenue = sum(s['amount'] for s in all_subs)  # Simplified - actual would track payments

        return jsonify({
            'subscribers': all_subs,
            'total': len(all_subs),
            'active': active_count,
            'monthly_revenue': monthly_revenue,
            'lifetime_revenue': lifetime_revenue
        })
    except Exception as e:
        return jsonify({
            'subscribers': [],
            'total': 0,
            'active': 0,
            'monthly_revenue': 0,
            'lifetime_revenue': 0,
            'error': str(e)
        }), 200

@app.route('/api/upgrade', methods=['POST'])
def upgrade_user():
    """Create Stripe checkout session for upgrade"""
    data = request.json
    email = data.get('email')
    tier = data.get('tier')  # 'basic' or 'unlimited'

    user, error = user_manager.get_or_create_user(email)
    if not user:
        return jsonify({'error': error}), 400

    # Create Stripe checkout session
    base_url = os.getenv('BASE_URL', 'http://localhost:5000')
    session, error = stripe_payments.create_checkout_session(
        email=email,
        tier=tier,
        success_url=f"{base_url}/api/payment-success",
        cancel_url=f"{base_url}/api/payment-cancel"
    )

    if session:
        return jsonify({
            'checkout_url': session['checkout_url'],
            'session_id': session['session_id']
        })
    else:
        # Fallback: manual upgrade for testing without Stripe
        success, message = user_manager.upgrade_user(user['id'], tier)
        if success:
            stats = user_manager.get_user_stats(user['id'])
            return jsonify({
                'success': True,
                'message': f'Upgraded to {tier}! (Manual)',
                'stats': stats,
                'note': 'Stripe not configured - manual upgrade'
            })
        else:
            return jsonify({'error': message}), 400

@app.route('/api/payment-success', methods=['GET'])
def payment_success():
    """Handle successful Stripe payment"""
    session_id = request.args.get('session_id')

    if not session_id:
        return jsonify({'error': 'No session ID'}), 400

    # Verify payment with Stripe
    payment_info, error = stripe_payments.verify_payment(session_id)

    if error:
        return jsonify({'error': error}), 400

    if payment_info and payment_info['paid']:
        # Get user
        user, error = user_manager.get_or_create_user(payment_info['customer_email'])
        if not user:
            return jsonify({'error': 'User not found'}), 400

        # Upgrade user
        success, message = user_manager.upgrade_user(
            user['id'],
            payment_info['tier'],
            stripe_customer_id=payment_info['customer_id']
        )

        if success:
            stats = user_manager.get_user_stats(user['id'])

            # Send notification - new subscriber!
            notifier.notify_new_subscription(
                email=payment_info['customer_email'],
                tier=payment_info['tier'],
                amount_paid=payment_info['amount_paid']
            )

            return jsonify({
                'success': True,
                'message': f"Successfully upgraded to {payment_info['tier']}!",
                'stats': stats,
                'amount_paid': payment_info['amount_paid']
            })
        else:
            return jsonify({'error': message}), 400
    else:
        return jsonify({'error': 'Payment not completed'}), 400

@app.route('/api/payment-cancel', methods=['GET'])
def payment_cancel():
    """Handle cancelled payment"""
    return jsonify({
        'message': 'Payment cancelled. You can try again anytime!',
        'cancelled': True
    })

@app.route('/api/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhooks"""
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')

    event_data, error = handle_webhook(payload, sig_header)

    if error:
        return jsonify({'error': error}), 400

    # Handle different webhook events
    if event_data['event'] == 'payment_successful':
        # Upgrade user
        user, _ = user_manager.get_or_create_user(event_data['email'])
        if user:
            user_manager.upgrade_user(
                user['id'],
                event_data['tier'],
                stripe_customer_id=event_data['customer_id']
            )

            # Send welcome email based on site and product
            site = event_data.get('site', '')
            product = event_data.get('product', '')
            amount = event_data.get('amount', 0)

            if site == 'eventfollowers':
                from max_agent import max_agent

                # Get username from metadata (for leaderboard)
                username = event_data.get('username', 'Seeker')

                # Gift purchases
                gift_map = {
                    'coffee': ('Coffee', '☕', '$3'),
                    'energy': ('Energy Boost', '⚡', '$5'),
                    'cosmic': ('Cosmic Blessing', '🌟', '$10'),
                    'favor': ("Entity's Favor", '👁️', '$25')
                }

                if product in gift_map:
                    gift_name, gift_icon, gift_amount = gift_map[product]
                    max_agent.send_gift_thankyou(event_data['email'], username, gift_name, gift_icon, gift_amount)
                elif product == 'animation_pass':
                    max_agent.send_animation_pass_thankyou(event_data['email'], username)
                elif product in ['starter', 'seeker', 'messages']:
                    # Message pack purchase
                    max_agent.send_purchase_thankyou(event_data['email'], username, product, f"${amount:.0f}")
                else:
                    # Premium subscription - send welcome email
                    send_welcome_email(event_data['email'], 'entity', username)

            # Send notification (webhook payment - recurring billing)
            notifier.notify_new_subscription(
                email=event_data['email'],
                tier=event_data['tier'],
                amount_paid=1.99 if event_data['tier'] == 'basic' else 4.99
            )

    elif event_data['event'] == 'subscription_cancelled':
        # Send cancellation notification
        if 'email' in event_data:
            notifier.notify_subscription_cancelled(
                email=event_data.get('email', 'unknown'),
                tier=event_data.get('tier', 'unknown')
            )
        # TODO: Downgrade user to free tier in database
        pass

    return jsonify({'received': True})

@app.route('/api/email/subscribe', methods=['POST'])
def email_subscribe():
    """Email subscription endpoint with welcome email"""
    data = request.get_json()
    email = data.get('email')
    agent = data.get('agent', 'vita')

    if not email:
        return jsonify({'error': 'Email required'}), 400

    # Send welcome email based on agent
    if agent == 'vita':
        result = send_welcome_vita(email)
    elif agent == 'astro':
        result = send_welcome_astro(email)
    elif agent == 'sage':
        result = send_welcome_sage(email)
    else:
        result = send_welcome_vita(email)

    # Also save to subscribers database
    add_subscriber(email, agent)

    return jsonify({'success': True, 'result': result})


@app.route('/api/email/subscribers', methods=['GET'])
def get_all_subscribers():
    """Get all subscribers with stats for dashboard"""
    try:
        stats = get_subscriber_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/email/subscribers/<int:subscriber_id>', methods=['DELETE'])
def delete_subscriber(subscriber_id):
    """Delete a subscriber by ID"""
    try:
        success = remove_subscriber(subscriber_id=subscriber_id)
        if success:
            return jsonify({'success': True, 'message': f'Subscriber {subscriber_id} removed'})
        return jsonify({'error': 'Subscriber not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ===========================================
# MAX-VITA INBOUND EMAIL WEBHOOK
# ===========================================

@app.route('/api/webhook/email/vita', methods=['POST'])
def webhook_email_vita():
    """
    Resend webhook for inbound emails to VITA (Longevity Futures)

    Resend sends POST with:
    - type: "email.received"
    - data: { email_id, from, to, subject, ... }

    MAX-VITA handles the email and auto-responds using AI
    """
    try:
        webhook_data = request.json
        print(f"[MAX-VITA] Received webhook: {webhook_data.get('type', 'unknown')}")

        # Handle the inbound email
        result = vita_handle_inbound(webhook_data)

        # Log result
        if result.get('success'):
            print(f"[MAX-VITA] Email processed from: {result.get('from', 'unknown')}")
            if result.get('response_sent'):
                print(f"[MAX-VITA] Auto-response sent!")
        else:
            print(f"[MAX-VITA] Processing failed: {result.get('reason', result.get('error', 'unknown'))}")

        return jsonify(result)

    except Exception as e:
        print(f"[MAX-VITA] Webhook error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/webhook/email/test', methods=['POST', 'GET'])
def webhook_email_test():
    """Test endpoint to verify webhook is accessible"""
    if request.method == 'GET':
        return jsonify({
            'status': 'ok',
            'message': 'MAX-VITA webhook endpoint is active',
            'endpoint': '/api/webhook/email/vita',
            'method': 'POST',
            'expects': 'Resend email.received webhook payload'
        })

    # POST - simulate inbound email
    data = request.json or {}
    return jsonify({
        'status': 'received',
        'data_received': data,
        'message': 'Test webhook received successfully'
    })


# ===========================================
# MAX-VITA SUBSCRIBER MANAGEMENT API
# ===========================================

@app.route('/api/vita/subscribers/stats', methods=['GET'])
def vita_subscriber_stats():
    """Get MAX-VITA subscriber statistics"""
    try:
        stats = max_vita.get_subscriber_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/vita/subscribers', methods=['GET'])
def vita_get_subscribers():
    """Get all MAX-VITA subscribers"""
    try:
        status = request.args.get('status', 'active')
        subscribers = max_vita.get_subscribers(status)
        return jsonify({'subscribers': subscribers, 'count': len(subscribers)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/vita/subscribers/add', methods=['POST'])
def vita_add_subscriber():
    """Add a new subscriber to MAX-VITA"""
    try:
        data = request.json
        email = data.get('email', '').strip()
        name = data.get('name', '')
        source = data.get('source', 'api')

        if not email:
            return jsonify({'error': 'Email required'}), 400

        result = max_vita.add_subscriber(email, name, source)

        # Send welcome email if new subscriber
        if result.get('is_new'):
            try:
                max_vita.send_welcome_email(email, name or 'Friend')
                max_vita.mark_welcome_sent(result['id'])
            except Exception as e:
                print(f"[MAX-VITA] Failed to send welcome email: {e}")

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/vita/subscribers/<int:subscriber_id>', methods=['DELETE'])
def vita_remove_subscriber(subscriber_id):
    """Remove a subscriber from MAX-VITA"""
    try:
        result = max_vita.remove_subscriber(subscriber_id=subscriber_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/vita/test-email', methods=['POST'])
def vita_test_email():
    """Send a test email via MAX-VITA"""
    try:
        data = request.json
        email = data.get('email', '').strip()

        if not email:
            return jsonify({'error': 'Email required'}), 400

        result = max_vita.send_welcome_email(email, 'Test User')
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ===========================================
# GHOST ENDPOINTS - Master Agent
# ===========================================

@app.route('/api/chat/ghost', methods=['POST'])
def chat_ghost():
    """GHOST - Master Agent chat endpoint"""
    try:
        data = request.json
        message = data.get('message', '').strip()
        session_id = data.get('session_id') or str(uuid.uuid4())
        user_email = data.get('email')

        if not message:
            return jsonify({'error': 'Message is required'}), 400

        # Chat with GHOST
        result = ghost_chat(message, session_id, user_email)

        return jsonify({
            'response': result['response'],
            'session_id': result['session_id'],
            'intent': result.get('intent', {})
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/ghost/write', methods=['POST'])
def ghost_write():
    """Have GHOST write an article"""
    try:
        data = request.json
        topic = data.get('topic', '').strip()
        style = data.get('style', 'informative')

        if not topic:
            return jsonify({'error': 'Topic is required'}), 400

        result = ghost_write_article(topic, style)

        return jsonify({
            'success': True,
            'title': result['title'],
            'content': result['content'],
            'word_count': result['word_count'],
            'status': result['status']
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/ghost/upload', methods=['POST'])
def ghost_upload():
    """Have GHOST create and upload an article to askmarket.store"""
    try:
        data = request.json
        topic = data.get('topic', '').strip()
        content = data.get('content')  # Optional - if provided, uses this content

        if not topic:
            return jsonify({'error': 'Topic is required'}), 400

        result = ghost_upload_article(topic, content)

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/ghost/email', methods=['POST'])
def ghost_email():
    """Have GHOST send an email"""
    try:
        data = request.json
        to_email = data.get('to', '').strip()
        subject = data.get('subject', '').strip()
        body = data.get('body', '').strip()

        if not all([to_email, subject, body]):
            return jsonify({'error': 'to, subject, and body are required'}), 400

        result = ghost_send_email(to_email, subject, body)

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/ghost/delegate', methods=['POST'])
def ghost_delegate_task():
    """Have GHOST delegate a task to another agent"""
    try:
        data = request.json
        task = data.get('task', '').strip()
        agent = data.get('agent', '').strip().lower()

        if not task or not agent:
            return jsonify({'error': 'task and agent are required'}), 400

        result = ghost_delegate(task, agent)

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/ghost/status', methods=['GET'])
def ghost_status_endpoint():
    """Get GHOST status and stats"""
    try:
        status = ghost_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ===========================================
# PICASSO ENDPOINTS - AI Image Generation
# ===========================================

@app.route('/api/picasso/generate', methods=['POST'])
def picasso_generate():
    """Generate an image using DALL-E 3"""
    try:
        data = request.json
        prompt = data.get('prompt', '').strip()
        category = data.get('category', 'general')
        size = data.get('size', '1024x1024')

        if not prompt:
            return jsonify({'error': 'Prompt is required'}), 400

        result = generate_image(prompt, category)

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/picasso/social', methods=['POST'])
def picasso_social():
    """Generate a social media optimized image"""
    try:
        data = request.json
        page_category = data.get('category', '').strip()
        post_topic = data.get('topic', '').strip()

        if not post_topic:
            return jsonify({'error': 'Topic is required'}), 400

        result = generate_social_image(page_category, post_topic)

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/picasso/gallery', methods=['GET'])
def picasso_gallery():
    """Get all generated images"""
    try:
        images = get_gallery()
        return jsonify({
            'success': True,
            'images': images,
            'count': len(images)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/picasso/pending', methods=['GET'])
def picasso_pending():
    """Get images pending approval"""
    try:
        images = get_pending()
        return jsonify({
            'success': True,
            'images': images,
            'count': len(images)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/picasso/approve/<int:image_id>', methods=['POST'])
def picasso_approve(image_id):
    """Approve an image for use"""
    try:
        result = approve(image_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/picasso/reject/<int:image_id>', methods=['POST'])
def picasso_reject(image_id):
    """Reject an image"""
    try:
        result = reject(image_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ===========================================
# IMAGE UPLOAD ENDPOINTS
# ===========================================

@app.route('/api/images/upload', methods=['POST'])
def upload_image():
    """Upload an image to a website's storage"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        site = request.form.get('site', 'longevity_futures')
        description = request.form.get('description', file.filename)
        tags = request.form.get('tags', '').split(',')
        tags = [t.strip() for t in tags if t.strip()]

        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        # Save temp file
        filename = secure_filename(file.filename)
        temp_path = os.path.join(os.path.dirname(__file__), 'temp_' + filename)
        file.save(temp_path)

        # Import to storage
        result = image_upload(site, temp_path, description, tags)

        # Clean up temp
        if os.path.exists(temp_path):
            os.remove(temp_path)

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/images/stats', methods=['GET'])
def get_image_stats():
    """Get image stats for all sites"""
    try:
        return jsonify(image_stats())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/images/unused/<site>', methods=['GET'])
def get_unused_images(site):
    """Get unused images for a site"""
    try:
        images = get_unused(site)
        return jsonify({'images': images, 'count': len(images)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/upload')
def upload_page():
    """Simple upload page"""
    return '''
<!DOCTYPE html>
<html>
<head>
    <title>Helix Image Upload</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            padding: 40px;
            color: white;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            background: rgba(255,255,255,0.1);
            border-radius: 16px;
            padding: 30px;
        }
        h1 { margin-bottom: 30px; text-align: center; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 8px; font-weight: 500; }
        select, input[type="text"] {
            width: 100%;
            padding: 12px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
        }
        .file-input {
            background: rgba(255,255,255,0.2);
            border: 2px dashed rgba(255,255,255,0.5);
            border-radius: 8px;
            padding: 40px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
        }
        .file-input:hover { border-color: #4ecdc4; background: rgba(78,205,196,0.1); }
        .file-input input { display: none; }
        .file-input.has-file { border-color: #4ecdc4; background: rgba(78,205,196,0.2); }
        button {
            width: 100%;
            padding: 15px;
            background: linear-gradient(135deg, #4ecdc4, #44a08d);
            border: none;
            border-radius: 8px;
            color: white;
            font-size: 18px;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.2s;
        }
        button:hover { transform: scale(1.02); }
        .result {
            margin-top: 20px;
            padding: 15px;
            border-radius: 8px;
            display: none;
        }
        .result.success { background: rgba(78,205,196,0.3); display: block; }
        .result.error { background: rgba(255,100,100,0.3); display: block; }
        .preview { max-width: 100%; margin-top: 10px; border-radius: 8px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Upload Image</h1>
        <form id="uploadForm">
            <div class="form-group">
                <label>Website</label>
                <select name="site" id="site">
                    <option value="longevity_futures">Longevity Futures</option>
                    <option value="silent_ai">Silent AI</option>
                    <option value="ask_market">Ask Market</option>
                    <option value="event_followers">Event Followers</option>
                    <option value="inspector_deepdive">Inspector DeepDive</option>
                    <option value="empire_enthusiast">Empire Enthusiast</option>
                    <option value="dream_wizz">Dream-Wizz</option>
                    <option value="urban_green_mowing">Urban Green Mowing</option>
                </select>
            </div>
            <div class="form-group">
                <label>Image</label>
                <div class="file-input" id="dropZone">
                    <input type="file" name="file" id="file" accept="image/*">
                    <p>Click or drag image here</p>
                    <img id="preview" class="preview" style="display:none">
                </div>
            </div>
            <div class="form-group">
                <label>Description</label>
                <input type="text" name="description" id="description" placeholder="What is this image about?">
            </div>
            <div class="form-group">
                <label>Tags (comma separated)</label>
                <input type="text" name="tags" id="tags" placeholder="health, fasting, diet">
            </div>
            <button type="submit">Upload</button>
        </form>
        <div id="result" class="result"></div>
    </div>
    <script>
        const dropZone = document.getElementById('dropZone');
        const fileInput = document.getElementById('file');
        const preview = document.getElementById('preview');

        dropZone.onclick = () => fileInput.click();

        fileInput.onchange = (e) => {
            if (e.target.files[0]) {
                dropZone.classList.add('has-file');
                preview.src = URL.createObjectURL(e.target.files[0]);
                preview.style.display = 'block';
                dropZone.querySelector('p').textContent = e.target.files[0].name;
            }
        };

        dropZone.ondragover = (e) => { e.preventDefault(); dropZone.classList.add('has-file'); };
        dropZone.ondragleave = () => dropZone.classList.remove('has-file');
        dropZone.ondrop = (e) => {
            e.preventDefault();
            fileInput.files = e.dataTransfer.files;
            fileInput.onchange({target: fileInput});
        };

        document.getElementById('uploadForm').onsubmit = async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const result = document.getElementById('result');

            try {
                const res = await fetch('/api/images/upload', { method: 'POST', body: formData });
                const data = await res.json();

                if (data.success) {
                    result.className = 'result success';
                    result.innerHTML = '✓ Uploaded! Image ID: ' + data.image_id;
                    e.target.reset();
                    preview.style.display = 'none';
                    dropZone.classList.remove('has-file');
                    dropZone.querySelector('p').textContent = 'Click or drag image here';
                } else {
                    result.className = 'result error';
                    result.innerHTML = '✗ Error: ' + data.error;
                }
            } catch (err) {
                result.className = 'result error';
                result.innerHTML = '✗ Error: ' + err.message;
            }
        };
    </script>
</body>
</html>
'''


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'running',
        'agents': {
            'ghost': 'ASK Market (Master)',
            'astro': 'Event Followers',
            'vita': 'Longevity Futures',
            'sage': 'Silent-AI',
            'picasso': 'AI Image Generation',
            'boomer': 'Longevity Sales AI',
            'max': 'Centralized Email System',
            'max-vita': 'Longevity Futures Email (AR enabled)'
        },
        'protection': {
            'email_capture': True,
            'question_limits': True,
            'rate_limiting': True,
            'subscription_tiers': ['free', 'basic', 'unlimited']
        },
        'webhooks': {
            'email_inbound_vita': '/api/webhook/email/vita',
            'stripe': '/api/webhook'
        }
    })

@app.route('/chatbot')
def serve_chatbot():
    """Serve Astro Boy chatbot"""
    from flask import send_file
    import os
    chatbot_path = os.path.join(os.path.dirname(__file__), 'chatbot-widget-astro.html')
    return send_file(chatbot_path)

# =============================================================================
# REAL-TIME CHAT ENDPOINTS (Pusher)
# =============================================================================

# Store online users per room (in-memory, resets on server restart)
online_users = {
    'is-ai-alive': {},
    'first-contact': {},
    'the-unknown': {}
}

@app.route('/api/chat/send', methods=['POST'])
def chat_send_message():
    """Send a message to a chat room - broadcasts to ALL users in that room"""
    try:
        data = request.json
        room = data.get('room', 'is-ai-alive')
        username = data.get('username', 'Anonymous')
        message = data.get('message', '')
        is_premium = data.get('is_premium', False)

        if not message:
            return jsonify({'error': 'Message required'}), 400

        # Broadcast to all users in the room
        pusher_client.trigger(f'chat-{room}', 'new-message', {
            'username': username,
            'message': message,
            'is_premium': is_premium,
            'timestamp': str(uuid.uuid4())[:8]  # Unique ID for message
        })

        return jsonify({'success': True, 'broadcast': True})

    except Exception as e:
        print(f"[CHAT] Error sending message: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/entity', methods=['POST'])
def chat_entity_response():
    """Get Entity response and broadcast to room"""
    try:
        data = request.json
        room = data.get('room', 'is-ai-alive')
        username = data.get('username', 'Seeker')
        message = data.get('message', '')

        if not message:
            return jsonify({'error': 'Message required'}), 400

        # Get Entity response (using existing agent)
        agent = agents.get('astro')
        if agent:
            # Simple response for now - can enhance later
            response = agent.get_simple_response(message, username) if hasattr(agent, 'get_simple_response') else f"I sense your question, {username}. The patterns of the universe are complex..."
        else:
            response = f"I hear you, {username}. The veil between dimensions is thin today..."

        # Broadcast Entity's response to all users
        pusher_client.trigger(f'chat-{room}', 'entity-message', {
            'message': response,
            'timestamp': str(uuid.uuid4())[:8]
        })

        return jsonify({'success': True, 'response': response})

    except Exception as e:
        print(f"[CHAT] Error with Entity response: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/gift', methods=['POST'])
def chat_send_gift():
    """Send a gift to another user - broadcasts to room"""
    try:
        data = request.json
        room = data.get('room', 'is-ai-alive')
        sender = data.get('sender', 'Anonymous')
        receiver = data.get('receiver', 'Anonymous')
        gift_type = data.get('gift_type', 'coffee')
        gift_amount = data.get('gift_amount', 3)

        # Gift mapping
        gifts = {
            'coffee': {'name': 'Coffee', 'icon': '☕', 'amount': 3},
            'energy': {'name': 'Energy Boost', 'icon': '⚡', 'amount': 5},
            'cosmic': {'name': 'Cosmic Blessing', 'icon': '🌟', 'amount': 10},
            'favor': {'name': "Entity's Favor", 'icon': '👁️', 'amount': 25}
        }

        gift = gifts.get(gift_type, gifts['coffee'])

        # Broadcast gift to all users in room
        pusher_client.trigger(f'chat-{room}', 'gift-sent', {
            'sender': sender,
            'receiver': receiver,
            'gift_name': gift['name'],
            'gift_icon': gift['icon'],
            'gift_amount': gift['amount'],
            'timestamp': str(uuid.uuid4())[:8]
        })

        return jsonify({'success': True, 'gift': gift})

    except Exception as e:
        print(f"[CHAT] Error sending gift: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/join', methods=['POST'])
def chat_join_room():
    """User joins a room - broadcasts presence"""
    try:
        data = request.json
        room = data.get('room', 'is-ai-alive')
        username = data.get('username', 'Anonymous')
        is_premium = data.get('is_premium', False)

        # Add to online users
        if room in online_users:
            online_users[room][username] = {
                'is_premium': is_premium,
                'joined': True
            }

        # Broadcast user joined
        pusher_client.trigger(f'chat-{room}', 'user-joined', {
            'username': username,
            'is_premium': is_premium,
            'online_count': len(online_users.get(room, {}))
        })

        return jsonify({'success': True, 'online_count': len(online_users.get(room, {}))})

    except Exception as e:
        print(f"[CHAT] Error joining room: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/leave', methods=['POST'])
def chat_leave_room():
    """User leaves a room"""
    try:
        data = request.json
        room = data.get('room', 'is-ai-alive')
        username = data.get('username', 'Anonymous')

        # Remove from online users
        if room in online_users and username in online_users[room]:
            del online_users[room][username]

        # Broadcast user left
        pusher_client.trigger(f'chat-{room}', 'user-left', {
            'username': username,
            'online_count': len(online_users.get(room, {}))
        })

        return jsonify({'success': True})

    except Exception as e:
        print(f"[CHAT] Error leaving room: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/online/<room>', methods=['GET'])
def chat_get_online(room):
    """Get list of online users in a room"""
    try:
        users = online_users.get(room, {})
        return jsonify({
            'room': room,
            'online_count': len(users),
            'users': [{'username': u, 'is_premium': d['is_premium']} for u, d in users.items()]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/typing', methods=['POST'])
def chat_user_typing():
    """Broadcast that a user is typing"""
    try:
        data = request.json
        room = data.get('room', 'is-ai-alive')
        username = data.get('username', 'Anonymous')

        pusher_client.trigger(f'chat-{room}', 'user-typing', {
            'username': username
        })

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("="*70)
    print("HELIX MEDIA ENGINE - AUTONOMOUS AGENT API SERVER")
    print("="*70)
    print("\nProtection Features:")
    print("  [x] Email capture required")
    print("  [x] 5-question limit (free users)")
    print("  [x] Rate limiting (10 req/min)")
    print("  [x] Subscription tiers ($1.99/$4.99)")
    print("  [x] Cost tracking")
    print("\nAgents running:")
    print("  [GHOST]    ASK Market (MASTER)  -> /api/chat/ghost")
    print("  [ASTRO]    Event Followers      -> /api/chat/eventfollowers")
    print("  [BOOMER]   Longevity Sales AI   -> /api/chat/longevityfutures")
    print("  [SAGE]     Silent-AI            -> /api/chat/silentai")
    print("  [PICASSO]  Image Generation     -> /api/picasso/*")
    print("  [MAX]      Email System         -> Centralized email handling")
    print("  [MAX-VITA] Longevity Email (AR) -> /api/webhook/email/vita")
    print("\nGHOST Endpoints:")
    print("  /api/ghost/write    - Write articles")
    print("  /api/ghost/upload   - Upload to askmarket.store")
    print("  /api/ghost/email    - Send emails")
    print("  /api/ghost/delegate - Delegate to other agents")
    print("  /api/ghost/status   - Get GHOST status")
    print("\nPICASSO Endpoints:")
    print("  /api/picasso/generate   - Generate DALL-E 3 image")
    print("  /api/picasso/social     - Generate social media image")
    print("  /api/picasso/gallery    - View all generated images")
    print("  /api/picasso/pending    - Images awaiting approval")
    print("  /api/picasso/approve/ID - Approve an image")
    print("  /api/picasso/reject/ID  - Reject an image")
    print("\nMAX Email Endpoints:")
    print("  /api/webhook/email/vita - Resend inbound webhook (Longevity Futures)")
    print("  /api/webhook/email/test - Test webhook endpoint")
    print("  /api/email/subscribe    - Email subscription")
    print("  /api/email/subscribers  - Get all subscribers")
    print("\nREAL-TIME CHAT Endpoints:")
    print("  /api/chat/send          - Send message to room (broadcasts to all)")
    print("  /api/chat/gift          - Send gift to user (broadcasts)")
    print("  /api/chat/online        - Get online users in room")
    print("\nServer starting on http://0.0.0.0:5000")
    print("="*70)

    app.run(host='0.0.0.0', port=5000, debug=False)
