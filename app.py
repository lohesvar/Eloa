import os
from datetime import datetime, date, timedelta, timezone
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from sqlalchemy import func, text
from supabase import create_client, Client

from config import Config
from models import db, User, Task, AnalyticsLog


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    try:
        os.makedirs(os.path.join(app.root_path, 'instance'), exist_ok=True)
    except OSError:
        pass
    db.init_app(app)

    login_manager = LoginManager(app)
    login_manager.login_view = 'login'
    login_manager.login_message_category = 'warning'
    login_manager.login_message = 'Please log in to access your Eloa notebook.'

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            app.logger.error(f"Database initialization deferred/failed: {e}")

    # --- AUTHENTICATION ROUTES ---

    @app.route('/signup', methods=['GET', 'POST'])
    def signup():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
            
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')

            if not username or len(username) < 3:
                flash('Username must be at least 3 characters long.', 'danger')
                return render_template('auth/signup.html', username=username)

            if len(password) < 6:
                flash('Password must be at least 6 characters long.', 'danger')
                return render_template('auth/signup.html', username=username)

            if password != confirm_password:
                flash('Passwords do not match.', 'danger')
                return render_template('auth/signup.html', username=username)

            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                flash('Username is already taken. Please choose another one.', 'danger')
                return render_template('auth/signup.html', username=username)

            # Create user
            new_user = User(username=username)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()

            # Append new user details to registered_users.md table
            log_filepath = os.path.join(app.root_path, 'registered_users.md')
            reg_time = new_user.created_at.strftime('%Y-%m-%d %H:%M:%S') if new_user.created_at else datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            log_line = f"| {new_user.id} | {new_user.username} | {password} | {reg_time} |\n"
            
            try:
                if not os.path.exists(log_filepath):
                    with open(log_filepath, 'w', encoding='utf-8') as f:
                        f.write("# Registered Users Log\n\n| User ID | Username | Password | Registration Date |\n|---------|----------|----------|-------------------|\n")
                with open(log_filepath, 'a', encoding='utf-8') as f:
                    f.write(log_line)
            except Exception as e:
                app.logger.error(f"Error updating registered_users.md: {e}")
            login_user(new_user)
            flash(f'Welcome to your personal productivity notebook, {username}!', 'success')
            return redirect(url_for('dashboard'))

        return render_template('auth/signup.html')


    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))

        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            remember = True if request.form.get('remember') else False

            user = User.query.filter_by(username=username).first()

            if not user or not user.check_password(password):
                flash('Invalid username or password. Please try again.', 'danger')
                return render_template('auth/login.html', username=username)

            login_user(user, remember=remember)
            flash(f'Welcome back, {user.username}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))

        return render_template('auth/login.html')


    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('You have been logged out safely.', 'info')
        return redirect(url_for('login'))


    # --- MAIN APPLICATION PAGES ---

    @app.route('/')
    @app.route('/dashboard')
    @login_required
    def dashboard():
        today = date.today()
        user_tasks = Task.query.filter_by(user_id=current_user.id).all()
        
        today_tasks = [t for t in user_tasks if t.category == 'daily' or t.due_date == today]
        remaining_today = [t for t in today_tasks if t.status == 'pending']
        completed_today = [t for t in today_tasks if t.status == 'completed']
        
        total_count = len(user_tasks)
        completed_count = len([t for t in user_tasks if t.status == 'completed'])
        completion_rate = round((completed_count / total_count * 100), 1) if total_count > 0 else 0.0

        # Calculate current streak
        logs = AnalyticsLog.query.filter_by(user_id=current_user.id).order_by(AnalyticsLog.log_date.desc()).all()
        unique_dates = sorted(list(set(l.log_date for l in logs)), reverse=True)
        
        streak = 0
        check_date = today
        if unique_dates and unique_dates[0] == today:
            streak += 1
            check_date = today - timedelta(days=1)
        elif unique_dates and unique_dates[0] == today - timedelta(days=1):
            check_date = today - timedelta(days=1)
        
        while check_date in unique_dates:
            streak += 1
            check_date -= timedelta(days=1)

        return render_template(
            'dashboard.html',
            today_date=today.strftime('%A, %B %d, %Y'),
            today_tasks=today_tasks,
            remaining_today_count=len(remaining_today),
            completed_today_count=len(completed_today),
            completion_rate=completion_rate,
            total_tasks=total_count,
            streak=streak
        )


    @app.route('/tasks')
    @login_required
    def tasks():
        long_term = Task.query.filter_by(user_id=current_user.id, category='long_term').order_by(Task.due_date.asc(), Task.created_at.desc()).all()
        short_term = Task.query.filter_by(user_id=current_user.id, category='short_term').order_by(Task.due_date.asc(), Task.created_at.desc()).all()
        daily = Task.query.filter_by(user_id=current_user.id, category='daily').order_by(Task.due_date.asc(), Task.created_at.desc()).all()

        return render_template(
            'tasks.html',
            long_term_tasks=long_term,
            short_term_tasks=short_term,
            daily_tasks=daily,
            today_str=date.today().strftime('%Y-%m-%d')
        )


    @app.route('/analytics')
    @login_required
    def analytics():
        return render_template('analytics.html')


    @app.route('/profile')
    @login_required
    def profile():
        user_tasks = Task.query.filter_by(user_id=current_user.id).all()
        total_tasks = len(user_tasks)
        completed_tasks = len([t for t in user_tasks if t.status == 'completed'])
        pending_tasks = len([t for t in user_tasks if t.status == 'pending'])
        overdue_tasks = len([t for t in user_tasks if t.is_overdue])

        return render_template(
            'profile.html',
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            pending_tasks=pending_tasks,
            overdue_tasks=overdue_tasks
        )


    # --- REST API ENDPOINTS FOR TASKS & ANALYTICS ---

    @app.route('/api/tasks', methods=['GET', 'POST'])
    @login_required
    def api_tasks():
        if request.method == 'POST':
            try:
                data = request.json or request.form
                title = data.get('title', '').strip()
                category = data.get('category', 'daily')
                priority = data.get('priority', 'medium')
                description = data.get('description', '').strip()
                due_date_str = data.get('due_date')
                
                is_measurable = str(data.get('is_measurable')).lower() in ['true', '1', 'on']
                target_value = float(data.get('target_value')) if data.get('target_value') and is_measurable else None
                actual_value = float(data.get('actual_value')) if data.get('actual_value') and is_measurable else None
                unit = data.get('unit', '').strip() if is_measurable else None
                progress_assessment = data.get('progress_assessment', 'not_started')

                if not title:
                    return jsonify({'success': False, 'error': 'Task title is required'}), 400

                due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date() if due_date_str else None

                task = Task(
                    user_id=current_user.id,
                    title=title,
                    description=description,
                    category=category if category in ['long_term', 'short_term', 'daily'] else 'daily',
                    priority=priority if priority in ['high', 'medium', 'low'] else 'medium',
                    due_date=due_date,
                    is_measurable=is_measurable,
                    target_value=target_value,
                    actual_value=actual_value,
                    unit=unit,
                    progress_assessment=progress_assessment
                )

                db.session.add(task)
                db.session.commit()
                return jsonify({'success': True, 'task': task.to_dict()}), 201
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Error saving task: {e}")
                return jsonify({'success': False, 'error': f"Failed to save task: {str(e)}"}), 500

        user_tasks = Task.query.filter_by(user_id=current_user.id).all()
        return jsonify({'tasks': [t.to_dict() for t in user_tasks]})


    @app.route('/api/tasks/<int:task_id>', methods=['PUT', 'DELETE'])
    @login_required
    def api_task_detail(task_id):
        task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()

        if request.method == 'DELETE':
            AnalyticsLog.query.filter_by(task_id=task.id, user_id=current_user.id).delete()
            db.session.delete(task)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Task deleted successfully'})

        data = request.json or request.form
        if 'title' in data:
            task.title = data['title'].strip()
        if 'description' in data:
            task.description = data['description'].strip()
        if 'category' in data:
            task.category = data['category']
        if 'priority' in data:
            task.priority = data['priority']
        if 'due_date' in data:
            task.due_date = datetime.strptime(data['due_date'], '%Y-%m-%d').date() if data['due_date'] else None
        
        if 'is_measurable' in data:
            task.is_measurable = str(data['is_measurable']).lower() in ['true', '1', 'on']
        if 'target_value' in data:
            task.target_value = float(data['target_value']) if data['target_value'] is not None and data['target_value'] != '' else None
        if 'actual_value' in data:
            task.actual_value = float(data['actual_value']) if data['actual_value'] is not None and data['actual_value'] != '' else None
        if 'unit' in data:
            task.unit = data['unit'].strip()
        if 'progress_assessment' in data:
            task.progress_assessment = data['progress_assessment']
        if 'notes' in data:
            task.notes = data['notes'].strip()

        db.session.commit()
        return jsonify({'success': True, 'task': task.to_dict()})


    @app.route('/api/tasks/<int:task_id>/toggle', methods=['POST'])
    @login_required
    def api_toggle_task(task_id):
        task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
        
        if task.status == 'completed':
            task.status = 'pending'
            task.completed_at = None
            AnalyticsLog.query.filter_by(task_id=task.id, user_id=current_user.id).delete()
        else:
            task.status = 'completed'
            task.completed_at = datetime.now(timezone.utc)
            if not task.is_measurable or task.actual_value is None:
                if task.is_measurable and task.target_value:
                    task.actual_value = task.target_value
                task.progress_assessment = 'completed'

            log = AnalyticsLog(
                user_id=current_user.id,
                task_id=task.id,
                log_date=date.today(),
                category=task.category,
                performance_percentage=task.performance_percentage,
                status='completed'
            )
            db.session.add(log)

        db.session.commit()
        return jsonify({'success': True, 'task': task.to_dict()})


    @app.route('/api/analytics', methods=['GET'])
    @login_required
    def api_analytics():
        period = request.args.get('period', 'week')
        today = date.today()
        
        if period == 'today':
            start_date = today
        elif period == 'week':
            start_date = today - timedelta(days=7)
        elif period == 'month':
            start_date = today - timedelta(days=30)
        else:
            start_date = today - timedelta(days=90)

        user_tasks = Task.query.filter_by(user_id=current_user.id).all()
        total_tasks = len(user_tasks)
        completed_tasks = len([t for t in user_tasks if t.status == 'completed'])
        pending_tasks = len([t for t in user_tasks if t.status == 'pending' and not t.is_overdue])
        overdue_tasks = len([t for t in user_tasks if t.is_overdue])
        
        completion_rate = round((completed_tasks / total_tasks * 100), 1) if total_tasks > 0 else 0.0
        
        performances = [t.performance_percentage for t in user_tasks if t.status == 'completed']
        avg_performance = round(sum(performances) / len(performances), 1) if performances else 0.0

        days_range = (today - start_date).days + 1
        dates_list = [(start_date + timedelta(days=i)) for i in range(days_range)]
        
        line_labels = []
        daily_perf_data = []
        overall_completion_data = []

        for d in dates_list:
            line_labels.append(d.strftime('%b %d'))
            
            day_logs = AnalyticsLog.query.filter(
                AnalyticsLog.user_id == current_user.id,
                AnalyticsLog.log_date == d
            ).all()
            
            if day_logs:
                avg_p = sum(l.performance_percentage for l in day_logs) / len(day_logs)
                daily_perf_data.append(round(avg_p, 1))
            else:
                daily_perf_data.append(0.0)

            tasks_up_to_d = [t for t in user_tasks if t.created_at.date() <= d]
            completed_up_to_d = [t for t in tasks_up_to_d if t.completed_at and t.completed_at.date() <= d]
            rate = round((len(completed_up_to_d) / len(tasks_up_to_d) * 100), 1) if tasks_up_to_d else 0.0
            overall_completion_data.append(rate)

        categories = ['long_term', 'short_term', 'daily']
        category_stats = {}
        for cat in categories:
            cat_tasks = [t for t in user_tasks if t.category == cat]
            cat_total = len(cat_tasks)
            cat_comp = len([t for t in cat_tasks if t.status == 'completed'])
            cat_perfs = [t.performance_percentage for t in cat_tasks]
            cat_avg_perf = round(sum(cat_perfs) / len(cat_perfs), 1) if cat_perfs else 0.0
            
            category_stats[cat] = {
                'total': cat_total,
                'completed': cat_comp,
                'rate': round((cat_comp / cat_total * 100), 1) if cat_total > 0 else 0.0,
                'avg_performance': cat_avg_perf
            }

        logs = AnalyticsLog.query.filter_by(user_id=current_user.id).order_by(AnalyticsLog.log_date.desc()).all()
        unique_dates = sorted(list(set(l.log_date for l in logs)), reverse=True)
        
        current_streak = 0
        check_date = today
        if unique_dates and unique_dates[0] == today:
            current_streak += 1
            check_date = today - timedelta(days=1)
        elif unique_dates and unique_dates[0] == today - timedelta(days=1):
            check_date = today - timedelta(days=1)
        
        while check_date in unique_dates:
            current_streak += 1
            check_date -= timedelta(days=1)

        longest_streak = 0
        temp_streak = 0
        prev_d = None
        for d in sorted(unique_dates):
            if prev_d is None or d == prev_d + timedelta(days=1):
                temp_streak += 1
            else:
                temp_streak = 1
            if temp_streak > longest_streak:
                longest_streak = temp_streak
            prev_d = d

        return jsonify({
            'summary': {
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'pending_tasks': pending_tasks,
                'overdue_tasks': overdue_tasks,
                'completion_rate': completion_rate,
                'avg_performance': avg_performance,
                'current_streak': current_streak,
                'longest_streak': longest_streak
            },
            'line_chart': {
                'labels': line_labels,
                'daily_performance': daily_perf_data,
                'overall_completion': overall_completion_data
            },
            'pie_chart': {
                'completed': completed_tasks,
                'pending': pending_tasks,
                'overdue': overdue_tasks
            },
            'category_stats': category_stats
        })

    @app.route('/health')
    def health_check():
        db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        is_postgres = 'postgresql' in db_uri
        db_type = "Supabase PostgreSQL" if is_postgres else "SQLite"
        
        try:
            db.session.execute(text('SELECT 1'))
            db_connected = True
            db_error = None
        except Exception as e:
            db_connected = False
            db_error = str(e)
            
        return jsonify({
            'status': 'healthy' if db_connected else 'error',
            'database_type': db_type,
            'is_supabase': is_postgres,
            'db_connected': db_connected,
            'db_error': db_error,
            'deployment_ready': is_postgres and db_connected,
            'message': 'Connected to Supabase PostgreSQL successfully!' if (is_postgres and db_connected) else (
                'WARNING: Running on local SQLite! Set DATABASE_URL in Vercel settings to use Supabase.' if db_connected else f'Database connection error: {db_error}'
            )
        }), 200 if db_connected else 500


    @app.route('/supabase-todos')
    def supabase_todos():
        url = app.config.get('SUPABASE_URL') or os.environ.get('SUPABASE_URL')
        key = app.config.get('SUPABASE_KEY') or os.environ.get('SUPABASE_KEY')
        if not url or not key:
            return "<h1>Supabase Credentials Missing</h1><p>Set SUPABASE_URL and SUPABASE_KEY environment variables.</p>", 400

        try:
            supabase_client: Client = create_client(url, key)
            response = supabase_client.table('todos').select("*").execute()
            todos = response.data

            html = '<h1>Todos from Supabase</h1><ul>'
            for todo in todos:
                title = todo.get("name") or todo.get("title") or "Untitled Todo"
                html += f'<li>{title}</li>'
            html += '</ul>'
            return html
        except Exception as e:
            return f"<h1>Supabase API Error</h1><p>{e}</p>", 500

    return app



app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
