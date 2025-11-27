"""
PROTECTED AUTONOMOUS AGENT API SERVER
With email capture, question limits, and payment integration
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from astro_v2_openai import AstroV2OpenAI, WEBSITES
from user_manager import UserManager
from stripe_integration import StripePayments, handle_webhook
from notifications import EmailNotifier
from ghost_agent import ghost_chat, ghost_write_article, ghost_upload_article, ghost_send_email, ghost_delegate, ghost_status
import os
import uuid
from dotenv import load_dotenv
from helix_email import send_welcome_vita, send_welcome_astro, send_welcome_sage

load_dotenv()

app = Flask(__name__)
CORS(app)

# Initialize managers
user_manager = UserManager()
stripe_payments = StripePayments()
notifier = EmailNotifier()

# Initialize all three agents
print("Initializing agents...")
agents = {
    'astro': AstroV2OpenAI(WEBSITES['eventfollowers']),
    'vita': AstroV2OpenAI(WEBSITES['longevityfutures']),
    'sage': AstroV2OpenAI(WEBSITES['silentai'])
}
print("All agents initialized!")

@app.route('/api/chat/eventfollowers', methods=['POST'])
def chat_eventfollowers():
    """ASTRO - Event Followers chatbot with protection"""
    return handle_protected_chat('astro', 'eventfollowers')

@app.route('/api/chat/longevityfutures', methods=['POST'])
def chat_longevityfutures():
    """VITA - Longevity Futures chatbot with protection"""
    return handle_protected_chat('vita', 'longevityfutures')

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

    return jsonify({'success': True, 'result': result})

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


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'running',
        'agents': {
            'ghost': 'ASK Market (Master)',
            'astro': 'Event Followers',
            'vita': 'Longevity Futures',
            'sage': 'Silent-AI'
        },
        'protection': {
            'email_capture': True,
            'question_limits': True,
            'rate_limiting': True,
            'subscription_tiers': ['free', 'basic', 'unlimited']
        }
    })

@app.route('/chatbot')
def serve_chatbot():
    """Serve Astro Boy chatbot"""
    from flask import send_file
    import os
    chatbot_path = os.path.join(os.path.dirname(__file__), 'chatbot-widget-astro.html')
    return send_file(chatbot_path)

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
    print("  [GHOST] ASK Market (MASTER) -> /api/chat/ghost")
    print("  [ASTRO] Event Followers     -> /api/chat/eventfollowers")
    print("  [VITA]  Longevity Futures   -> /api/chat/longevityfutures")
    print("  [SAGE]  Silent-AI           -> /api/chat/silentai")
    print("\nGHOST Endpoints:")
    print("  /api/ghost/write    - Write articles")
    print("  /api/ghost/upload   - Upload to askmarket.store")
    print("  /api/ghost/email    - Send emails")
    print("  /api/ghost/delegate - Delegate to other agents")
    print("  /api/ghost/status   - Get GHOST status")
    print("\nServer starting on http://0.0.0.0:5000")
    print("="*70)

    app.run(host='0.0.0.0', port=5000, debug=False)
