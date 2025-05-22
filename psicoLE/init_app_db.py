#!/usr/bin/env python3
import os
import sys
from werkzeug.security import generate_password_hash
from flask import Flask
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import after setting up the path
from psicoLE.database import db
from psicoLE.auth.models import User, Role
from psicoLE.main import app  # Import the app instance

def init_db():
    # Load environment variables
    load_dotenv()
    
    # Configure the app
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///psicole.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize the database with the app
    db.init_app(app)
    
    with app.app_context():
        # Create all database tables
        print("Creating database tables...")
        db.create_all()
        
        # Create admin role if it doesn't exist
        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            print("Creating admin role...")
            admin_role = Role(name='admin')
            db.session.add(admin_role)
            db.session.commit()
        
        # Create admin user if it doesn't exist
        username = "admin"
        email = "admin@example.com"
        password = "admin123"
        
        if not User.query.filter_by(username=username).first():
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
        else:
            print("El usuario administrador ya existe.")

if __name__ == "__main__":
    print("Inicializando la base de datos de la aplicación...")
    init_db()
    print("Base de datos inicializada correctamente.")
