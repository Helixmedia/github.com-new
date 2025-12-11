"""
Stripe Payment Integration
Handles subscriptions for Basic ($1.99) and Unlimited ($4.99) tiers
"""

import stripe
import os
from dotenv import load_dotenv

load_dotenv()

# Stripe configuration
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

# Subscription tiers
SUBSCRIPTION_TIERS = {
    'basic': {
        'name': 'Basic Plan',
        'price': 1.99,
        'price_cents': 199,
        'questions_per_month': 100,
        'stripe_price_id': os.getenv('STRIPE_BASIC_PRICE_ID'),
        'features': [
            '100 questions per month',
            'All product recommendations',
            'Priority support',
            'Cancel anytime'
        ]
    },
    'unlimited': {
        'name': 'Unlimited Plan',
        'price': 4.99,
        'price_cents': 499,
        'questions_per_month': 'unlimited',
        'stripe_price_id': os.getenv('STRIPE_UNLIMITED_PRICE_ID'),
        'features': [
            'Unlimited questions',
            'All product recommendations',
            'Priority support',
            'Early access to new features',
            'Cancel anytime'
        ]
    }
}

class StripePayments:
    def __init__(self):
        if not stripe.api_key:
            print("[WARNING] Stripe API key not configured. Set STRIPE_SECRET_KEY in .env")

    def create_checkout_session(self, email, tier, success_url, cancel_url):
        """
        Create a Stripe Checkout session for subscription

        Args:
            email: User's email
            tier: 'basic' or 'unlimited'
            success_url: Where to redirect after successful payment
            cancel_url: Where to redirect if user cancels

        Returns:
            dict with session_id and checkout_url
        """

        if tier not in SUBSCRIPTION_TIERS:
            return None, "Invalid tier"

        tier_info = SUBSCRIPTION_TIERS[tier]

        if not tier_info['stripe_price_id']:
            return None, "Stripe price not configured. Run setup first."

        try:
            session = stripe.checkout.Session.create(
                customer_email=email,
                payment_method_types=['card'],
                line_items=[{
                    'price': tier_info['stripe_price_id'],
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=success_url + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=cancel_url,
                metadata={
                    'tier': tier,
                    'email': email
                }
            )

            return {
                'session_id': session.id,
                'checkout_url': session.url
            }, None

        except stripe.error.StripeError as e:
            return None, str(e)

    def create_products_and_prices(self):
        """
        One-time setup: Create Stripe products and prices
        Call this once to set up your Stripe account

        Returns product and price IDs to add to .env
        """

        try:
            # Create Basic tier product
            basic_product = stripe.Product.create(
                name='Basic Plan',
                description='100 AI-powered product recommendations per month'
            )

            basic_price = stripe.Price.create(
                product=basic_product.id,
                unit_amount=199,  # $1.99
                currency='usd',
                recurring={'interval': 'month'}
            )

            # Create Unlimited tier product
            unlimited_product = stripe.Product.create(
                name='Unlimited Plan',
                description='Unlimited AI-powered product recommendations'
            )

            unlimited_price = stripe.Price.create(
                product=unlimited_product.id,
                unit_amount=499,  # $4.99
                currency='usd',
                recurring={'interval': 'month'}
            )

            print("\n" + "="*70)
            print("STRIPE PRODUCTS CREATED SUCCESSFULLY!")
            print("="*70)
            print("\nAdd these to your .env file:\n")
            print(f"STRIPE_BASIC_PRICE_ID={basic_price.id}")
            print(f"STRIPE_UNLIMITED_PRICE_ID={unlimited_price.id}")
            print("\n" + "="*70)

            return {
                'basic': {
                    'product_id': basic_product.id,
                    'price_id': basic_price.id
                },
                'unlimited': {
                    'product_id': unlimited_product.id,
                    'price_id': unlimited_price.id
                }
            }

        except stripe.error.StripeError as e:
            print(f"Error creating products: {str(e)}")
            return None

    def verify_payment(self, session_id):
        """
        Verify a payment was successful

        Returns:
            dict with customer info and subscription details
        """
        try:
            session = stripe.checkout.Session.retrieve(session_id)

            if session.payment_status == 'paid':
                return {
                    'paid': True,
                    'customer_email': session.customer_email,
                    'customer_id': session.customer,
                    'subscription_id': session.subscription,
                    'tier': session.metadata.get('tier'),
                    'amount_paid': session.amount_total / 100  # Convert cents to dollars
                }, None
            else:
                return None, "Payment not completed"

        except stripe.error.StripeError as e:
            return None, str(e)

    def cancel_subscription(self, subscription_id):
        """Cancel a subscription"""
        try:
            subscription = stripe.Subscription.delete(subscription_id)
            return True, "Subscription cancelled"
        except stripe.error.StripeError as e:
            return False, str(e)

    def get_subscription_status(self, subscription_id):
        """Get current subscription status"""
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            return {
                'status': subscription.status,
                'current_period_end': subscription.current_period_end,
                'cancel_at_period_end': subscription.cancel_at_period_end
            }, None
        except stripe.error.StripeError as e:
            return None, str(e)

def handle_webhook(payload, sig_header):
    """
    Handle Stripe webhooks
    Call this from your webhook endpoint
    """
    endpoint_secret = os.getenv('STRIPE_WEBHOOK_SECRET')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError:
        return None, "Invalid payload"
    except stripe.error.SignatureVerificationError:
        return None, "Invalid signature"

    # Handle different event types
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        return {
            'event': 'payment_successful',
            'email': session.get('customer_email'),
            'tier': session['metadata'].get('tier'),
            'site': session['metadata'].get('site'),
            'product': session['metadata'].get('product'),
            'username': session['metadata'].get('username', 'Seeker'),
            'amount': session.get('amount_total', 0) / 100,
            'customer_id': session.get('customer'),
            'subscription_id': session.get('subscription')
        }, None

    elif event['type'] == 'customer.subscription.created':
        # Handle new subscriptions (including re-subscriptions after cancellation)
        subscription = event['data']['object']
        customer_id = subscription.get('customer')

        # Get customer email from Stripe
        try:
            customer = stripe.Customer.retrieve(customer_id)
            email = customer.get('email')
        except:
            email = None

        return {
            'event': 'payment_successful',
            'email': email,
            'tier': 'unlimited',
            'site': 'eventfollowers',
            'product': 'subscription',
            'username': 'Seeker',
            'amount': subscription['items']['data'][0]['price']['unit_amount'] / 100 if subscription.get('items', {}).get('data') else 4.99,
            'customer_id': customer_id,
            'subscription_id': subscription['id']
        }, None

    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        return {
            'event': 'subscription_cancelled',
            'subscription_id': subscription['id'],
            'customer_id': subscription['customer']
        }, None

    elif event['type'] == 'invoice.payment_failed':
        invoice = event['data']['object']
        return {
            'event': 'payment_failed',
            'customer_id': invoice['customer'],
            'subscription_id': invoice['subscription']
        }, None

    return {'event': event['type']}, None


if __name__ == "__main__":
    print("\n" + "="*70)
    print("STRIPE INTEGRATION SETUP")
    print("="*70)

    # Check if API key is configured
    if not stripe.api_key:
        print("\n[ERROR] Stripe API key not found!")
        print("\nTo set up Stripe:")
        print("1. Go to https://dashboard.stripe.com/register")
        print("2. Create account (or login)")
        print("3. Get your API keys from: https://dashboard.stripe.com/apikeys")
        print("4. Add to .env file:")
        print("   STRIPE_SECRET_KEY=sk_test_...")
        print("   STRIPE_WEBHOOK_SECRET=whsec_...")
        print("\nThen run this script again to create products.")
    else:
        print("\n[OK] Stripe API key configured")
        print("\nWhat would you like to do?")
        print("1. Create Stripe products and prices (first-time setup)")
        print("2. Test checkout session creation")
        print("3. Exit")

        choice = input("\nEnter choice (1-3): ")

        if choice == "1":
            print("\nCreating Stripe products...")
            stripe_payments = StripePayments()
            result = stripe_payments.create_products_and_prices()

        elif choice == "2":
            print("\nTesting checkout session...")
            stripe_payments = StripePayments()
            session, error = stripe_payments.create_checkout_session(
                email="test@example.com",
                tier="basic",
                success_url="http://localhost:5000/success",
                cancel_url="http://localhost:5000/cancel"
            )

            if session:
                print(f"\n[OK] Checkout session created!")
                print(f"Session ID: {session['session_id']}")
                print(f"Checkout URL: {session['checkout_url']}")
                print("\nOpen this URL to test payment:")
                print(session['checkout_url'])
            else:
                print(f"\n[ERROR] {error}")

        else:
            print("\nExiting...")
