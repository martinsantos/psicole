from database import db  # Importación absoluta
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from flask_login import UserMixin  # Import UserMixin
from enum import Enum, auto

class SecurityEventType(Enum):
    LOGIN_SUCCESS = "Inicio de sesión exitoso"
    LOGIN_FAILED = "Intento de inicio de sesión fallido"
    PASSWORD_CHANGE = "Cambio de contraseña"
    PROFILE_UPDATE = "Actualización de perfil"
    ACCOUNT_LOCKED = "Cuenta bloqueada"
    ACCOUNT_UNLOCKED = "Cuenta desbloqueada"
    SESSION_START = "Sesión iniciada"
    SESSION_END = "Sesión finalizada"
    PASSWORD_RESET_REQUEST = "Solicitud de restablecimiento de contraseña"
    PASSWORD_RESET = "Restablecimiento de contraseña exitoso"
    EMAIL_VERIFICATION_SENT = "Correo de verificación enviado"
    EMAIL_VERIFIED = "Correo verificado"
    SECURITY_QUESTION_ANSWERED = "Pregunta de seguridad respondida"
    SESSION_REVOKED = "Sesión revocada"
    USER_CREATED = "Usuario creado"
    USER_DELETED = "Usuario eliminado"
    ROLE_CHANGED = "Rol de usuario modificado"

class Role(db.Model):
    __tablename__ = 'roles'
    id = Column(Integer, primary_key=True)
    name = Column(String(64), unique=True, nullable=False)
    users = relationship('User', backref='role', lazy='dynamic')

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f'<Role {self.name}>'

class User(UserMixin, db.Model): # Add UserMixin
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    role_id = Column(Integer, ForeignKey('roles.id'))

    def __init__(self, username, password_hash, email, role_id=None):
        self.username = username
        self.password_hash = password_hash
        self.email = email
        if role_id:
            self.role_id = role_id

    # Flask-Login methods
    # get_id is provided by UserMixin by default, using self.id
    # is_authenticated: provided by UserMixin, returns True if user is logged in
    # is_active: can be customized, e.g. if users can be deactivated. Default is True.
    # is_anonymous: provided by UserMixin, returns True if user is not logged in.

    def __repr__(self):
        return f'<User {self.username}>'


class SecurityEvent(db.Model):
    __tablename__ = 'security_events'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    event_type = Column(String(50), nullable=False)
    ip_address = Column(String(45))  # IPv6 puede tener hasta 45 caracteres
    user_agent = Column(Text)
    details = Column(JSON)  # Para almacenar información adicional
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relación con el usuario
    user = relationship('User', backref='security_events')
    
    def __init__(self, user_id, event_type, ip_address=None, user_agent=None, details=None):
        self.user_id = user_id
        self.event_type = event_type
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.details = details or {}
    
    def __repr__(self):
        return f'<SecurityEvent {self.event_type} - User {self.user_id}>'


class UserSession(db.Model):
    __tablename__ = 'user_sessions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    session_id = Column(String(255), unique=True, nullable=False)
    ip_address = Column(String(45))  # IPv6 puede tener hasta 45 caracteres
    user_agent = Column(Text)
    is_active = Column(Boolean, default=True)
    last_activity = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relación con el usuario
    user = relationship('User', backref='sessions')
    
    def __init__(self, user_id, session_id, ip_address=None, user_agent=None, expires_at=None):
        self.user_id = user_id
        self.session_id = session_id
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.expires_at = expires_at or (datetime.utcnow() + timedelta(days=30))  # 30 días por defecto
    
    def is_expired(self):
        return datetime.utcnow() > self.expires_at
    
    def __repr__(self):
        return f'<UserSession {self.session_id} - User {self.user_id}>'


class SecurityQuestion(db.Model):
    __tablename__ = 'security_questions'
    
    id = Column(Integer, primary_key=True)
    question = Column(String(255), nullable=False, unique=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relación con las respuestas de los usuarios
    user_answers = relationship('UserSecurityAnswer', backref='question', lazy='dynamic')
    
    def __init__(self, question, is_active=True):
        self.question = question
        self.is_active = is_active
    
    def __repr__(self):
        return f'<SecurityQuestion {self.question[:50]}>'


class UserSecurityAnswer(db.Model):
    __tablename__ = 'user_security_answers'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    question_id = Column(Integer, ForeignKey('security_questions.id'), nullable=False)
    answer_hash = Column(String(255), nullable=False)  # Almacenar hash de la respuesta
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relación con el usuario
    user = relationship('User', backref='security_answers')
    
    def __init__(self, user_id, question_id, answer_hash):
        self.user_id = user_id
        self.question_id = question_id
        self.answer_hash = answer_hash
    
    def __repr__(self):
        return f'<UserSecurityAnswer User {self.user_id} - Question {self.question_id}>'
