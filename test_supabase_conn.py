import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv()

from app import create_app
from models import db, User, Task
from sqlalchemy import text

def test_connection():
    print("=" * 60)
    print("      ELOA SUPABASE DATABASE CONNECTION TEST       ")
    print("=" * 60)

    db_url = os.environ.get('SUPABASE_DB_URL') or os.environ.get('DATABASE_URL')
    
    if not db_url or '[YOUR-PASSWORD]' in db_url:
        print("\n[X] RESULT: SUPABASE IS NOT CONNECTED YET!")
        print("    Reason: DATABASE_URL environment variable is missing or contains placeholder '[YOUR-PASSWORD]'.")
        print("\n    To Fix:")
        print("    1. Set DATABASE_URL in your .env or server environment variables:")
        print("       DATABASE_URL=postgresql://postgres.uawshbzmbnjzwajiyyfs:YOUR_PASSWORD@aws-0-ap-south-1.pooler.supabase.com:6543/postgres")
        print("    2. Re-run this script: python test_supabase_conn.py\n")
        return False

    print(f"\n[+] Detected DATABASE_URL: {db_url[:35]}... (Masked password)")
    
    app = create_app()
    with app.app_context():
        try:
            # 1. Execute test query
            res = db.session.execute(text("SELECT version();")).fetchone()
            print(f"[✓] Successfully connected to PostgreSQL / Supabase!")
            print(f"    Server Version: {res[0][:60]}...")

            # 2. Ensure tables exist
            db.create_all()
            print("[✓] Checked database schema: 'user', 'task', and 'analytics_log' tables exist.")

            # 3. Read test
            user_count = User.query.count()
            task_count = Task.query.count()
            print(f"[✓] Active database records: {user_count} User(s), {task_count} Task(s).")

            print("\n" + "=" * 60)
            print("[SUCCESS] SUPABASE CONNECTION VERIFIED & DEPLOYMENT READY!")
            print("=" * 60 + "\n")
            return True

        except Exception as e:
            print(f"\n[X] CONNECTION ERROR: Failed to connect to Supabase database.")
            print(f"    Error details: {e}")
            print("\n    Please verify your Supabase database password, host, and port (6543 for pooler).\n")
            return False

if __name__ == '__main__':
    test_connection()
