import unittest, os
from app import create_app, db
from models import User, Task, AnalyticsLog
from datetime import date, timedelta
from config import Config

TEST_DB_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance', 'test_notebook.db')

from sqlalchemy.pool import StaticPool

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{TEST_DB_PATH}"
    SQLALCHEMY_ENGINE_OPTIONS = {
        "poolclass": StaticPool,
        "connect_args": {"check_same_thread": False}
    }
    WTF_CSRF_ENABLED = False


class NotebookAppTestCase(unittest.TestCase):
    def setUp(self):
        self.app_instance = create_app(TestConfig)
        self.app = self.app_instance.test_client()
        self.app_context = self.app_instance.app_context()
        self.app_context.push()
        db.drop_all()
        db.create_all()

    def tearDown(self):
        db.session.close()
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.app_context.pop()



    def test_signup_login_flow(self):
        # 1. Signup user
        res = self.app.post('/signup', data={
            'username': 'testuser',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Welcome to your personal productivity notebook', res.data)

        # 2. Test logout
        res_logout = self.app.get('/logout', follow_redirects=True)
        self.assertIn(b'logged out safely', res_logout.data)

        # 3. Test duplicate signup failure (when logged out)
        res2 = self.app.post('/signup', data={
            'username': 'testuser',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        self.assertIn(b'Username is already taken', res2.data)


        # 4. Protected route without auth
        res_protected = self.app.get('/dashboard', follow_redirects=True)
        self.assertIn(b'Please log in to access your Eloa notebook', res_protected.data)

        # 5. Login
        res_login = self.app.post('/login', data={
            'username': 'testuser',
            'password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(res_login.status_code, 200)
        self.assertIn(b'Welcome back', res_login.data)

    def test_task_crud_and_measurable_performance(self):
        # Signup & login
        self.app.post('/signup', data={'username': 'taskuser', 'password': 'password123', 'confirm_password': 'password123'})

        # Create quantifiable task (Target: 3 hours, Actual: 2.5 hours -> 83.3%)
        res = self.app.post('/api/tasks', json={
            'title': 'Study Python for 3 hours',
            'category': 'daily',
            'priority': 'high',
            'is_measurable': True,
            'target_value': 3.0,
            'actual_value': 2.5,
            'unit': 'hours',
            'due_date': str(date.today())
        })
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data['success'])
        task_id = data['task']['id']
        self.assertEqual(data['task']['performance_percentage'], 83.3)

        # Toggle completion
        res_toggle = self.app.post(f'/api/tasks/{task_id}/toggle')
        self.assertEqual(res_toggle.status_code, 200)
        toggle_data = res_toggle.get_json()
        self.assertEqual(toggle_data['task']['status'], 'completed')

        # Check analytics API reflects data
        res_analytics = self.app.get('/api/analytics?period=week')
        self.assertEqual(res_analytics.status_code, 200)
        analytics_data = res_analytics.get_json()
        self.assertGreaterEqual(analytics_data['summary']['total_tasks'], 1)

if __name__ == '__main__':
    unittest.main()
