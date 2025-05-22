#!/usr/bin/env python3
import os
import sys
import sqlite3
from pathlib import Path

def create_database():
    # Ensure the instance directory exists
    instance_path = Path('instance')
    instance_path.mkdir(exist_ok=True, mode=0o755)
    
    # Set the database path
    db_path = instance_path / 'psicole.db'
    
    # Remove existing database if it exists
    if db_path.exists():
        print(f"Removing existing database at {db_path}")
        db_path.unlink()
    
    print(f"Creating new database at {db_path}")
    
    # Connect to the database (this will create it)
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Create tables
    print("Creating tables...")
    
    # Roles table
    cursor.execute('''
    CREATE TABLE roles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(64) UNIQUE NOT NULL
    )
    ''')
    
    # Users table
    cursor.execute('''
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username VARCHAR(64) UNIQUE NOT NULL,
        email VARCHAR(120) UNIQUE NOT NULL,
        password_hash VARCHAR(128) NOT NULL,
        is_active BOOLEAN DEFAULT 1,
        role_id INTEGER,
        FOREIGN KEY (role_id) REFERENCES roles (id)
    )
    ''')
    
    # Create indexes
    cursor.execute('CREATE INDEX ix_users_username ON users (username)')
    cursor.execute('CREATE INDEX ix_users_email ON users (email)')
    
    # Create admin role
    print("Creating admin role...")
    cursor.execute(
        "INSERT INTO roles (name) VALUES (?)",
        ('admin',)
    )
    admin_role_id = cursor.lastrowid
    
    # Create admin user
    print("Creating admin user...")
    from werkzeug.security import generate_password_hash
    password_hash = generate_password_hash('admin123', method='pbkdf2:sha256')
    
    cursor.execute(
        """
        INSERT INTO users (username, email, password_hash, is_active, role_id)
        VALUES (?, ?, ?, ?, ?)
        """,
        ('admin', 'admin@example.com', password_hash, 1, admin_role_id)
    )
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    # Set permissions
    os.chmod(db_path, 0o666)
    
    print("\n¡Base de datos inicializada correctamente!")
    print("======================================")
    print("Usuario: admin")
    print("Correo electrónico: admin@example.com")
    print("Contraseña: admin123")
    print("\n¡IMPORTANTE! Por favor, cambia esta contraseña después de iniciar sesión.")
    print("======================================\n")

if __name__ == "__main__":
    print("Inicializando la base de datos...")
    create_database()
