#!/usr/bin/env python3
import os
import sys
from werkzeug.security import generate_password_hash
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Set up Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/psicole.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'dev-key-123'  # Change this in production

# Initialize database
db = SQLAlchemy(app)

# Define models
class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    users = db.relationship('User', backref='role', lazy='dynamic')

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

def init_db():
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
