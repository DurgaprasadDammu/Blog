import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    # Get table info for users
    print("Checking users table schema in PostgreSQL...")
    res = conn.execute(text("""
        SELECT column_name, data_type, is_nullable, column_default 
        FROM information_schema.columns 
        WHERE table_name = 'users';
    """)).fetchall()
    for row in res:
        print(row)
