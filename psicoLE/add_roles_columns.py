"""Script to add missing columns to the roles table."""
import sys
import os
from sqlalchemy import text
from app import create_app
from database import db

def add_roles_columns():
    """Add missing columns to the roles table."""
    app = create_app()
    
    with app.app_context():
        # Check if the columns exist
        conn = db.engine.connect()
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('roles')]
        
        # Add missing columns
        if 'description' not in columns:
            print("Adding 'description' column to roles table...")
            db.session.execute(text("ALTER TABLE roles ADD COLUMN description TEXT"))
        
        if 'created_at' not in columns:
            print("Adding 'created_at' column to roles table...")
            db.session.execute(text("ALTER TABLE roles ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
        
        if 'updated_at' not in columns:
            print("Adding 'updated_at' column to roles table...")
            db.session.execute(text("ALTER TABLE roles ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
        
        if 'is_system_role' not in columns:
            print("Adding 'is_system_role' column to roles table...")
            db.session.execute(text("ALTER TABLE roles ADD COLUMN is_system_role BOOLEAN DEFAULT FALSE"))
        
        # Commit the changes
        db.session.commit()
        print("Roles table updated successfully!")

if __name__ == "__main__":
    add_roles_columns()
