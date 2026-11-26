import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import all models to ensure they are registered with the Base metadata
from app.database import Base, engine
from app.models.user import User
from app.models.post import Post
from app.models.category import Category
from app.models.comment import Comment
from app.models.tag import Tag

try:
    print("Dropping all existing database tables...")
    Base.metadata.drop_all(bind=engine)
    print("Creating database tables with new numeric ID schema...")
    Base.metadata.create_all(bind=engine)
    print("Database schema successfully reset!")
except Exception as e:
    print(f"Error resetting database: {e}")
    sys.exit(1)
