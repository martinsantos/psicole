#!/usr/bin/env python3
"""Create an admin user."""
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

from app import create_app
from database import db

# Import models after db is available
from auth.models import User, Role

app = create_app()

with app.app_context():
    # Create admin role if it doesn't exist
    admin_role = Role.query.filter_by(name='admin').first()
    if not admin_role:
        admin_role = Role(name='admin', description='Administrator with full access')
        admin_role.is_system_role = True
        db.session.add(admin_role)
        db.session.commit()
        print("Rol de administrador creado exitosamente!")
    
    # Check if admin user already exists
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        # Create admin user
        admin_user = User(
            username='admin',
            email='admin@example.com',
            first_name='Admin',
            last_name='User',
            is_active=True,
            is_superuser=True,
            is_staff=True,
            email_verified=True,
            role_id=admin_role.id
        )
        admin_user.set_password('admin123')  # Default password, change in production
        
        db.session.add(admin_user)
        db.session.commit()
        print("Usuario administrador creado exitosamente!")
        print("=" * 50)
        print("Credenciales de acceso:")
        print(f"Usuario: admin")
        print(f"Contraseña: admin123")
        print("=" * 50)
        print("\n¡IMPORTANTE! Por favor cambia la contraseña después del primer inicio de sesión.")
    else:
        print("El usuario administrador ya existe en la base de datos.")
        print(f"Usuario: admin")
        print("Para restablecer la contraseña, usa la opción 'Olvidé mi contraseña' en la página de inicio de sesión.")
