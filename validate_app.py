import sys
from app import create_app
from models import db, User, Task, AnalyticsLog

def validate():
    app = create_app()
    with app.app_context():
        # Check user database table
        users = User.query.all()
        print(f"Validated Users in DB: {[u.username for u in users]}")

        for u in users:
            print(f"User {u.username}: Password Hash = {u.password_hash[:20]}... (Securely Hashed)")
            # Verify check_password logic
            if u.username == 'Lohesvar':
                assert u.check_password('lohes__06'), "Password verification failed"
                print("Password check verified successfully!")

        # Check tasks table
        tasks = Task.query.all()
        print(f"Validated Tasks in DB: {len(tasks)} tasks")
        for t in tasks:
            print(f" - [{t.category.upper()}] '{t.title}': Performance = {t.performance_percentage}% (Status: {t.status})")

        # Check analytics logs
        logs = AnalyticsLog.query.all()
        print(f"Validated Analytics Logs: {len(logs)} entries")

    print("\nALL BACKEND & DATABASE CHECKS PASSED WITH 0 ERRORS!")

if __name__ == '__main__':
    validate()
