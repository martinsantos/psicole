"""Script to fix the roles table by adding missing columns."""
import sqlite3
import os

def fix_roles_table():
    """Add missing columns to the roles table."""
    # Path to the SQLite database
    db_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'data',
        'psicole.db'
    )
    
    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}")
        return
    
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get the list of columns in the roles table
        cursor.execute("PRAGMA table_info(roles)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add missing columns
        if 'description' not in columns:
            print("Adding 'description' column to roles table...")
            cursor.execute("ALTER TABLE roles ADD COLUMN description TEXT")
        
        if 'created_at' not in columns:
            print("Adding 'created_at' column to roles table...")
            # First add the column without a default value
            cursor.execute("""
                ALTER TABLE roles 
                ADD COLUMN created_at TIMESTAMP
            """)
            # Then update existing rows with current timestamp
            cursor.execute("UPDATE roles SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
        
        if 'updated_at' not in columns:
            print("Adding 'updated_at' column to roles table...")
            # First add the column without a default value
            cursor.execute("""
                ALTER TABLE roles 
                ADD COLUMN updated_at TIMESTAMP
            """)
            # Then update existing rows with current timestamp
            cursor.execute("UPDATE roles SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL")
        
        if 'is_system_role' not in columns:
            print("Adding 'is_system_role' column to roles table...")
            cursor.execute("""
                ALTER TABLE roles 
                ADD COLUMN is_system_role BOOLEAN DEFAULT 0
            """)
        
        # Commit the changes
        conn.commit()
        print("Roles table updated successfully!")
        
        # Verify the changes
        cursor.execute("PRAGMA table_info(roles)")
        print("\nCurrent columns in roles table:")
        for column in cursor.fetchall():
            print(f"- {column[1]} ({column[2]})")
        
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    fix_roles_table()
