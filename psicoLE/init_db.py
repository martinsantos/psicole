#!/usr/bin/env python3
import os
from werkzeug.security import generate_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask import Flask

# Configuración de la aplicación
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///psicole.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'dev-key-change-in-production'

# Inicializar la base de datos
db = SQLAlchemy(app)

# Definir modelos
class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    users = db.relationship('User', backref='role', lazy='dynamic')
    
    def __init__(self, name):
        self.name = name
        
    def __repr__(self):
        return f'<Role {self.name}>'

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    email = db.Column(db.String(120), unique=True, index=True)
    password_hash = db.Column(db.String(128))
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
    # Eliminar el archivo de base de datos existente si existe
    db_path = 'psicole.db'
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            print(f"Base de datos existente eliminada: {os.path.abspath(db_path)}")
        except Exception as e:
            print(f"Error al eliminar la base de datos existente: {e}")
            return
    
    # Crear todas las tablas
    with app.app_context():
        try:
            # Crear tablas
            db.create_all()
            print("Tablas creadas exitosamente.")
            
            # Verificar si el rol de administrador ya existe
            admin_role = Role.query.filter_by(name='admin').first()
            if not admin_role:
                admin_role = Role(name='admin')
                db.session.add(admin_role)
                db.session.commit()
                print("Rol 'admin' creado exitosamente.")
            else:
                print("El rol 'admin' ya existe.")
            
            # Verificar si el usuario administrador ya existe
            username = "admin"
            email = "admin@example.com"
            password = "admin123"  # Cambiar en producción
            
            admin_user = User.query.filter((User.username == username) | (User.email == email)).first()
            
            if not admin_user:
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
                print("\nEl usuario administrador ya existe en la base de datos.")
            
            # Verificar que el usuario se creó correctamente
            user = User.query.filter_by(username=username).first()
            if user and user.verify_password(password):
                print("Verificación exitosa: El usuario puede autenticarse correctamente.")
            else:
                print("Advertencia: No se pudo verificar el usuario.")
                
        except Exception as e:
            print(f"Error durante la inicialización de la base de datos: {e}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    init_db()
