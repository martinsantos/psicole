#!/usr/bin/env python3
import os
from werkzeug.security import generate_password_hash
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, ForeignKey, Boolean, Float, DateTime, Text
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime

# Configuración de la aplicación
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/psicole.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'clave-secreta-temporal'

# Inicializar la base de datos
db = SQLAlchemy(app)

# Definir modelos básicos
class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.String(255))
    users = db.relationship('User', backref='role', lazy='dynamic')

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True, nullable=False)
    email = db.Column(db.String(120), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    
    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')
    
    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
    
    def verify_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)

def init_db():
    # Crear el directorio instance si no existe
    os.makedirs('instance', exist_ok=True)
    
    # Eliminar la base de datos existente si existe
    if os.path.exists('instance/psicole.db'):
        os.remove('instance/psicole.db')
    
    # Crear todas las tablas
    with app.app_context():
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
        password = "admin123"  # Cambiar en producción
        
        # Verificar si el usuario ya existe
        if not User.query.filter_by(username=username).first():
            admin_user = User(
                username=username,
                email=email,
                is_active=True
            )
            admin_user.password = password
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
    print("Inicializando la base de datos...")
    init_db()
    print("Base de datos inicializada correctamente.")
