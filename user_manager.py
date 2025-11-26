"""
User Management System
Handles email capture, question tracking, and subscription status
"""

import sqlite3
import hashlib
import time
from datetime import datetime, timedelta
import re

class UserManager:
    def __init__(self, db_path='users.db'):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Create database tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                email_hash TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                subscription_tier TEXT DEFAULT 'free',
                stripe_customer_id TEXT,
                subscription_expires TIMESTAMP
            )
        ''')

        # Questions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                question TEXT NOT NULL,
                site TEXT NOT NULL,
                asked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                article_url TEXT,
                cost REAL DEFAULT 0.03,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        # Rate limiting table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rate_limits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                endpoint TEXT NOT NULL,
                request_count INTEGER DEFAULT 1,
                window_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        conn.commit()
        conn.close()
        print("[UserManager] Database initialized")

    def validate_email(self, email):
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    def hash_email(self, email):
        """Hash email for privacy"""
        return hashlib.sha256(email.lower().encode()).hexdigest()

    def get_or_create_user(self, email):
        """Get existing user or create new one"""
        if not self.validate_email(email):
            return None, "Invalid email format"

        email = email.lower().strip()
        email_hash = self.hash_email(email)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Try to find existing user
        cursor.execute('SELECT * FROM users WHERE email_hash = ?', (email_hash,))
        user = cursor.fetchone()

        if user:
            conn.close()
            return {
                'id': user[0],
                'email': user[1],
                'created_at': user[3],
                'subscription_tier': user[4],
                'stripe_customer_id': user[5],
                'subscription_expires': user[6]
            }, None

        # Create new user
        try:
            cursor.execute('''
                INSERT INTO users (email, email_hash, subscription_tier)
                VALUES (?, ?, 'free')
            ''', (email, email_hash))
            conn.commit()
            user_id = cursor.lastrowid

            conn.close()
            return {
                'id': user_id,
                'email': email,
                'created_at': datetime.now().isoformat(),
                'subscription_tier': 'free',
                'stripe_customer_id': None,
                'subscription_expires': None
            }, None
        except sqlite3.IntegrityError:
            conn.close()
            return None, "Email already exists"

    def get_question_count(self, user_id):
        """Get total questions asked by user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM questions WHERE user_id = ?', (user_id,))
        count = cursor.fetchone()[0]

        conn.close()
        return count

    def log_question(self, user_id, question, site, article_url=None, cost=0.03):
        """Log a question asked by user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO questions (user_id, question, site, article_url, cost)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, question, site, article_url, cost))

        conn.commit()
        conn.close()

    def can_ask_question(self, user_id):
        """Check if user can ask another question based on their tier"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get user subscription tier
        cursor.execute('SELECT subscription_tier, subscription_expires FROM users WHERE id = ?', (user_id,))
        result = cursor.fetchone()

        if not result:
            conn.close()
            return False, "User not found"

        tier = result[0]
        expires = result[1]

        # Check if subscription expired
        if tier != 'free' and expires:
            expires_dt = datetime.fromisoformat(expires)
            if datetime.now() > expires_dt:
                # Downgrade to free
                cursor.execute('UPDATE users SET subscription_tier = ? WHERE id = ?', ('free', user_id))
                conn.commit()
                tier = 'free'

        # Get question count
        cursor.execute('SELECT COUNT(*) FROM questions WHERE user_id = ?', (user_id,))
        total_questions = cursor.fetchone()[0]

        # Get questions this month (for paid tiers)
        cursor.execute('''
            SELECT COUNT(*) FROM questions
            WHERE user_id = ? AND asked_at >= date('now', 'start of month')
        ''', (user_id,))
        monthly_questions = cursor.fetchone()[0]

        conn.close()

        # Check limits based on tier
        if tier == 'free':
            if total_questions >= 5:
                return False, "free_limit_reached"
            return True, "ok"

        elif tier == 'basic':
            if monthly_questions >= 100:
                return False, "monthly_limit_reached"
            return True, "ok"

        elif tier == 'unlimited':
            return True, "ok"

        return False, "unknown_tier"

    def upgrade_user(self, user_id, tier, stripe_customer_id=None, months=1):
        """Upgrade user to paid tier"""
        if tier not in ['basic', 'unlimited']:
            return False, "Invalid tier"

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        expires = (datetime.now() + timedelta(days=30*months)).isoformat()

        cursor.execute('''
            UPDATE users
            SET subscription_tier = ?, stripe_customer_id = ?, subscription_expires = ?
            WHERE id = ?
        ''', (tier, stripe_customer_id, expires, user_id))

        conn.commit()
        conn.close()
        return True, "User upgraded"

    def check_rate_limit(self, user_id, endpoint, max_per_minute=10):
        """Check if user is rate limited (max requests per minute)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Clean up old rate limit records (older than 1 minute)
        one_minute_ago = (datetime.now() - timedelta(minutes=1)).isoformat()
        cursor.execute('''
            DELETE FROM rate_limits
            WHERE window_start < ?
        ''', (one_minute_ago,))

        # Get current rate limit
        cursor.execute('''
            SELECT request_count, window_start FROM rate_limits
            WHERE user_id = ? AND endpoint = ?
        ''', (user_id, endpoint))

        result = cursor.fetchone()

        if not result:
            # First request
            cursor.execute('''
                INSERT INTO rate_limits (user_id, endpoint, request_count)
                VALUES (?, ?, 1)
            ''', (user_id, endpoint))
            conn.commit()
            conn.close()
            return True, "ok"

        count, window_start = result

        if count >= max_per_minute:
            conn.close()
            return False, "rate_limit_exceeded"

        # Increment counter
        cursor.execute('''
            UPDATE rate_limits
            SET request_count = request_count + 1
            WHERE user_id = ? AND endpoint = ?
        ''', (user_id, endpoint))

        conn.commit()
        conn.close()
        return True, "ok"

    def get_user_stats(self, user_id):
        """Get user statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get user info
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()

        if not user:
            conn.close()
            return None

        # Get question stats
        cursor.execute('SELECT COUNT(*) FROM questions WHERE user_id = ?', (user_id,))
        total_questions = cursor.fetchone()[0]

        cursor.execute('''
            SELECT COUNT(*) FROM questions
            WHERE user_id = ? AND asked_at >= date('now', 'start of month')
        ''', (user_id,))
        monthly_questions = cursor.fetchone()[0]

        cursor.execute('SELECT SUM(cost) FROM questions WHERE user_id = ?', (user_id,))
        total_cost = cursor.fetchone()[0] or 0

        conn.close()

        # Calculate remaining questions
        tier = user[4]
        if tier == 'free':
            remaining = max(0, 3 - total_questions)
        elif tier == 'basic':
            remaining = max(0, 100 - monthly_questions)
        else:  # unlimited
            remaining = float('inf')

        return {
            'email': user[1],
            'tier': tier,
            'total_questions': total_questions,
            'monthly_questions': monthly_questions,
            'remaining_questions': remaining,
            'total_cost': round(total_cost, 2),
            'created_at': user[3],
            'subscription_expires': user[6]
        }


if __name__ == "__main__":
    # Test the system
    manager = UserManager()

    print("\n=== Testing User Manager ===\n")

    # Test email validation
    print("Test 1: Email Validation")
    print(f"  test@example.com: {manager.validate_email('test@example.com')}")
    print(f"  invalid-email: {manager.validate_email('invalid-email')}")

    # Test user creation
    print("\nTest 2: User Creation")
    user, error = manager.get_or_create_user('paul@test.com')
    if user:
        print(f"  Created user: {user['email']} (ID: {user['id']})")

    # Test question limits
    print("\nTest 3: Question Limits (Free Tier)")
    for i in range(5):
        can_ask, reason = manager.can_ask_question(user['id'])
        print(f"  Question {i+1}: {can_ask} ({reason})")
        if can_ask:
            manager.log_question(user['id'], f"Test question {i+1}", "eventfollowers")

    # Test stats
    print("\nTest 4: User Stats")
    stats = manager.get_user_stats(user['id'])
    print(f"  Total questions: {stats['total_questions']}")
    print(f"  Remaining: {stats['remaining_questions']}")
    print(f"  Total cost: ${stats['total_cost']}")

    # Test upgrade
    print("\nTest 5: Upgrade to Basic")
    manager.upgrade_user(user['id'], 'basic')
    can_ask, reason = manager.can_ask_question(user['id'])
    print(f"  Can ask after upgrade: {can_ask} ({reason})")

    stats = manager.get_user_stats(user['id'])
    print(f"  New tier: {stats['tier']}")
    print(f"  Remaining: {stats['remaining_questions']}")

    print("\n=== Tests Complete ===")
