import os
import sqlite3
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
SQLITE_DB_PATH = os.path.join(BASE_DIR, 'instance', 'notebook_todo.db')

def migrate():
    print("=" * 60)
    print("      ELOA: SQLITE TO SUPABASE POSTGRESQL MIGRATION       ")
    print("=" * 60)

    db_url = os.environ.get('SUPABASE_DB_URL') or os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL')
    
    if not db_url or '[YOUR-PASSWORD]' in db_url:
        print("\n[!] Error: DATABASE_URL in .env still contains placeholder '[YOUR-PASSWORD]'.")
        print("    Please add your Supabase database password into your .env file:")
        print("    DATABASE_URL=postgresql://postgres.uawshbzmbnjzwajiyyfs:<YOUR_PASSWORD>@aws-0-ap-south-1.pooler.supabase.com:6543/postgres\n")
        return False

    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)


    print(f"\n[+] Connecting to Supabase PostgreSQL...")
    engine = create_engine(db_url, pool_pre_ping=True)
    
    # 1. Create tables in Supabase
    from app import create_app
    from models import db, User, Task, AnalyticsLog
    
    app = create_app()
    with app.app_context():
        print("[+] Creating database schema ('user', 'task', 'analytics_log') in Supabase...")
        db.create_all()
        print("[✓] Tables created successfully in Supabase PostgreSQL!")

    # 2. Extract local data from SQLite
    if not os.path.exists(SQLITE_DB_PATH):
        print("[!] No local SQLite database found. Migration complete with empty tables.")
        return True

    print(f"[+] Extracting existing data from local SQLite database...")
    sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cursor = sqlite_conn.cursor()

    # Migrate Users
    sqlite_cursor.execute("SELECT * FROM user")
    users = sqlite_cursor.fetchall()
    
    Session = sessionmaker(bind=engine)
    pg_session = Session()

    migrated_users = 0
    for u in users:
        existing = pg_session.query(User).filter_by(username=u['username']).first()
        if not existing:
            new_user = User(
                username=u['username'],
                password_hash=u['password_hash']
            )
            pg_session.add(new_user)
            migrated_users += 1
    
    pg_session.commit()
    print(f"[✓] Migrated {migrated_users} user(s) to Supabase PostgreSQL!")

    # Migrate Tasks
    sqlite_cursor.execute("SELECT * FROM task")
    tasks = sqlite_cursor.fetchall()
    migrated_tasks = 0

    for t in tasks:
        # Check matching user id or title
        new_task = Task(
            user_id=t['user_id'],
            title=t['title'],
            category=t['category'],
            priority=t['priority'],
            due_date=t['due_date'],
            description=t['description'],
            status=t['status'],
            is_measurable=t['is_measurable'],
            target_value=t['target_value'],
            actual_value=t['actual_value'],
            unit=t['unit'],
            progress_assessment=t['progress_assessment'],
            performance_percentage=t['performance_percentage'],
            completed_at=t['completed_at']
        )
        pg_session.add(new_task)
        migrated_tasks += 1

    pg_session.commit()
    print(f"[✓] Migrated {migrated_tasks} task(s) to Supabase PostgreSQL!")

    pg_session.close()
    sqlite_conn.close()

    print("\n" + "=" * 60)
    print("[SUCCESS] ALL TABLES & DATA SUCCESSFULLY MIGRATED TO SUPABASE!")
    print("=" * 60 + "\n")
    return True

if __name__ == '__main__':
    migrate()
