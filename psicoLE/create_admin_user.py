#!/usr/bin/env python3
import os
import sys
from werkzeug.security import generate_password_hash

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import db
from psicoLE.auth.models import User, Role

def create_admin_user():
    # Configuración de la base de datos
    basedir = os.path.abspath(os.path.dirname(__file__))
    database_path = os.path.join(basedir, 'instance', 'psicole.db')
    
    # Asegurarse de que el directorio instance existe
    os.makedirs(os.path.dirname(database_path), exist_ok=True)
    
    # Configurar la aplicación Flask
    from flask import Flask
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{database_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Inicializar la base de datos con la aplicación
    db.init_app(app)
    
    with app.app_context():
        # Asegurarse de que las tablas estén creadas
        db.create_all()
        
        # Crear roles si no existen
        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            admin_role = Role(name='admin', description='Administrator with full access')
            db.session.add(admin_role)
            db.session.commit()
            print("Rol 'admin' creado.")
        
        # Crear usuario administrador
        username = "admin"
        email = "admin@example.com"
        password = "admin123"  # Contraseña por defecto, se recomienda cambiarla después
        
        # Verificar si el usuario ya existe
        if User.query.filter_by(username=username).first():
            print(f"El usuario '{username}' ya existe.")
            return
        
        # Crear el usuario
        admin_user = User(
            username=username,
            email=email,
            is_active=True
        )
        admin_user.password = password  # Esto usará el setter para hashear la contraseña
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
    create_admin_user()
