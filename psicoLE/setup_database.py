"""Script to initialize the database and create all tables."""
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).parent.absolute())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app import create_app
from database import db

def setup_database():
    """Initialize the database and create all tables."""
    # Create the Flask application
    app = create_app()
    
    with app.app_context():
        # Create all database tables
        print("Creating database tables...")
        db.create_all()
        print("Database tables created successfully!")
        
        # Verify tables were created
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print("\nTables in the database:")
        for table in tables:
            print(f"- {table}")

if __name__ == "__main__":
    setup_database()
