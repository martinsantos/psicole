import sqlite3

def check_schema():
    # Connect to the SQLite database
    conn = sqlite3.connect('psicole.db')
    cursor = conn.cursor()
    
    # Get the list of all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print("Tables in the database:")
    for table in tables:
        table_name = table[0]
        print(f"\nTable: {table_name}")
        
        # Get table info
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        
        print("Columns:")
        for column in columns:
            print(f"  - {column[1]} ({column[2]})")
    
    # Close the connection
    conn.close()

if __name__ == "__main__":
    check_schema()
