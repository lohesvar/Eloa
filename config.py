import os
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Load environment variables from .env if present
load_dotenv(os.path.join(BASE_DIR, '.env'))

db_url = (
    os.environ.get('SUPABASE_DB_URL') or 
    os.environ.get('DATABASE_URL') or 
    os.environ.get('POSTGRES_URL') or 
    os.environ.get('POSTGRES_URL_NON_POOLING')
)

if db_url:
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

else:
    # Use /tmp on serverless environments like Vercel if instance dir is non-writable
    tmp_dir = '/tmp' if os.path.exists('/tmp') else os.path.join(BASE_DIR, 'instance')
    os.makedirs(tmp_dir, exist_ok=True)
    db_url = f"sqlite:///{os.path.join(tmp_dir, 'notebook_todo.db')}"

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'notebook-to-do-super-secret-key-2026'
    SQLALCHEMY_DATABASE_URI = db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY')




