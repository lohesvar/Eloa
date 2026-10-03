import argparse
import os
import sys
from datetime import datetime, timezone
from app import create_app
from models import db, User, Task

def initialize_database(username=None, password=None):
    app = create_app()
    with app.app_context():
        # Ensure database tables exist (Supabase PostgreSQL or SQLite)
        db.create_all()
        print("Database tables initialized successfully!")

        if username is None:
            try:
                username = input("\nEnter username to register (or press Enter to skip): ").strip()
            except (EOFError, KeyboardInterrupt):
                username = ""
        else:
            username = username.strip()

        if username:
            existing = User.query.filter_by(username=username).first()
            if existing:
                print(f"User '{username}' already exists in database (ID: {existing.id}).")
            else:
                if password is None:
                    try:
                        password = input(f"Enter password for '{username}': ").strip()
                    except (EOFError, KeyboardInterrupt):
                        password = ""
                else:
                    password = password.strip()
                
                if not password:
                    print("Error: Password cannot be empty. User creation aborted.")
                else:
                    new_user = User(username=username)
                    new_user.set_password(password)
                    db.session.add(new_user)
                    db.session.commit()
                    print(f"User '{new_user.username}' created successfully with ID {new_user.id}!")

                    # Append user details to registered_users.md table
                    log_filepath = os.path.join(app.root_path, 'registered_users.md')
                    reg_time = new_user.created_at.strftime('%Y-%m-%d %H:%M:%S') if new_user.created_at else datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                    log_line = f"| {new_user.id} | {new_user.username} | {password} | {reg_time} |\n"
                    
                    if not os.path.exists(log_filepath):
                        with open(log_filepath, 'w', encoding='utf-8') as f:
                            f.write("# Registered Users Log\n\n| User ID | Username | Password | Registration Date |\n|---------|----------|----------|-------------------|\n")
                    with open(log_filepath, 'a', encoding='utf-8') as f:
                        f.write(log_line)
                    print(f"User '{new_user.username}' logged into registered_users.md.")

        user_count = User.query.count()
        task_count = Task.query.count()
        db_type = "Supabase PostgreSQL" if "postgresql" in app.config['SQLALCHEMY_DATABASE_URI'] else "SQLite"
        print(f"\nDatabase status ({db_type}): {user_count} User(s), {task_count} Task(s) stored.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Initialize Eloa database and optionally register a user.")
    parser.add_argument('-u', '--username', type=str, help="Username for the new user")
    parser.add_argument('-p', '--password', type=str, help="Password for the new user")
    args = parser.parse_args()
    initialize_database(username=args.username, password=args.password)

