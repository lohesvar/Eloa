from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timezone

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    tasks = db.relationship('Task', backref='user', lazy=True, cascade='all, delete-orphan')
    analytics_logs = db.relationship('AnalyticsLog', backref='user', lazy=True, cascade='all, delete-orphan')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Task(db.Model):
    __tablename__ = 'task'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    title = db.Column(db.String(250), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(20), nullable=False, default='daily') # 'long_term', 'short_term', 'daily'
    priority = db.Column(db.String(10), nullable=False, default='medium') # 'high', 'medium', 'low'
    status = db.Column(db.String(20), nullable=False, default='pending') # 'pending', 'completed'
    due_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Measurable vs Non-measurable Task Performance
    is_measurable = db.Column(db.Boolean, default=False)
    target_value = db.Column(db.Float, nullable=True)
    actual_value = db.Column(db.Float, nullable=True)
    unit = db.Column(db.String(50), nullable=True) # 'hours', 'pages', 'reps', 'km', 'mins', etc.
    progress_assessment = db.Column(db.String(30), nullable=True, default='not_started') # 'not_started', 'started', 'partially_completed', 'completed', 'excellent'
    notes = db.Column(db.Text, nullable=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def is_overdue(self):
        if self.due_date and self.status == 'pending':
            return self.due_date < date.today()
        return False

    @property
    def performance_percentage(self):
        if self.is_measurable and self.target_value and self.target_value > 0:
            if self.actual_value is not None:
                val = (self.actual_value / self.target_value) * 100.0
                return round(val, 1)
            return 0.0
        
        # Non-measurable fallback mapping
        mapping = {
            'excellent': 100.0,
            'completed': 100.0,
            'partially_completed': 60.0,
            'started': 30.0,
            'not_started': 0.0
        }
        if self.status == 'completed':
            return 100.0 if not self.progress_assessment or self.progress_assessment == 'not_started' else mapping.get(self.progress_assessment, 100.0)
        return mapping.get(self.progress_assessment, 0.0)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'description': self.description or '',
            'category': self.category,
            'priority': self.priority,
            'status': self.status,
            'due_date': self.due_date.strftime('%Y-%m-%d') if self.due_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'is_measurable': self.is_measurable,
            'target_value': self.target_value,
            'actual_value': self.actual_value,
            'unit': self.unit or '',
            'progress_assessment': self.progress_assessment or 'not_started',
            'notes': self.notes or '',
            'is_overdue': self.is_overdue,
            'performance_percentage': self.performance_percentage
        }


class AnalyticsLog(db.Model):
    __tablename__ = 'analytics_log'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id', ondelete='SET NULL'), nullable=True)
    log_date = db.Column(db.Date, nullable=False, default=date.today)
    category = db.Column(db.String(20), nullable=False, default='daily')
    performance_percentage = db.Column(db.Float, nullable=False, default=0.0)
    status = db.Column(db.String(20), nullable=False, default='completed')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'task_id': self.task_id,
            'log_date': self.log_date.strftime('%Y-%m-%d'),
            'category': self.category,
            'performance_percentage': self.performance_percentage,
            'status': self.status
        }
