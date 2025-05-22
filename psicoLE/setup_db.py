#!/usr/bin/env python3
import os
import sys
from werkzeug.security import generate_password_hash

# Add the current directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Now import the app and models
from main import app, db
from auth.models import User, Role

def init_db():
    print("Initializing database...")
    
    # Create the database directory if it doesn't exist
    os.makedirs('instance', exist_ok=True)
    
    with app.app_context():
        # Drop all tables and recreate them
        print("Creating database tables...")
        db.drop_all()
        db.create_all()
        
        # Create admin role
        print("Creating admin role...")
        admin_role = Role(name='admin')
        db.session.add(admin_role)
        db.session.commit()
        
        # Create admin user
        username = "admin"
        email = "admin@example.com"
        password = "admin123"
        
        print("Creating admin user...")
        admin_user = User(
            username=username,
            email=email,
            is_active=True
        )
        admin_user.set_password(password)
        admin_user.role = admin_role
        
        db.session.add(admin_user)
        db.session.commit()
        
        print("\n¡Usuario administrador creado exitosamente!")
        print("======================================")
        print(f"Usuario: {username}")
        print(f"Correo electrónico: {email}")
        print(f"Contraseña: {password}")
        print("\n¡IMPORTANTE! Por favor, cambia esta contraseña después de iniciar sesión.")
        print("======================================\n")

if __name__ == "__main__":
    init_db()
    print("Base de datos inicializada correctamente.")
