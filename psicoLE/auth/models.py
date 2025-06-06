from database import db  # Importación absoluta
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Text, JSON, Table
from sqlalchemy.orm import relationship, backref
from datetime import datetime, timedelta
from flask_login import UserMixin  # Import UserMixin
from .security_models import Permission, SecurityQuestion, get_role_permissions_association  # Import models and functions from security_models
from . import associations  # Import association tables
from enum import Enum, auto
from werkzeug.security import generate_password_hash, check_password_hash


def init_models():
    """
    Initialize model relationships after all models are defined.
    
    This function is kept for backward compatibility and to handle any
    remaining setup that can't be done at the class level.
    
    Returns:
        dict: A dictionary containing all model classes for easy access.
    """
    from .security_models import (
        TokenBlacklist, PasswordHistory, FailedLoginAttempt,
        UserConsent, UserDevice, UserActivity, UserNotification, UserPreference,
        Group, Permission
    )
    
    # All relationships are now defined in their respective model classes
    # This function is kept for backward compatibility
    
    # Return a dictionary of all models for easy access
    return {
        'User': User,
        'Role': Role,
        'PasswordResetToken': PasswordResetToken,
        'EmailVerificationToken': EmailVerificationToken,
        'SecurityEvent': SecurityEvent,
        'UserSession': UserSession,
        'UserSecurityAnswer': UserSecurityAnswer,
        'SecurityQuestion': SecurityQuestion,
        'TokenBlacklist': TokenBlacklist,
        'PasswordHistory': PasswordHistory,
        'FailedLoginAttempt': FailedLoginAttempt,
        'UserConsent': UserConsent,
        'UserDevice': UserDevice,
        'UserActivity': UserActivity,
        'UserNotification': UserNotification,
        'UserPreference': UserPreference,
        'TokenBlacklist': TokenBlacklist,
        'PasswordHistory': PasswordHistory,
        'FailedLoginAttempt': FailedLoginAttempt,
        'UserConsent': UserConsent,
        'UserDevice': UserDevice,
        'UserActivity': UserActivity,
        'UserNotification': UserNotification,
        'UserPreference': UserPreference,
        'Group': Group,
        'Permission': Permission
    }

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
    """Role model for user permissions and access control."""
    __tablename__ = 'roles'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(64), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_system_role = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    users = relationship('User', back_populates='role', lazy='dynamic')
    permissions = relationship(
        'Permission',
        secondary=lambda: get_role_permissions_association(),
        back_populates='roles',
        lazy='dynamic',
        viewonly=False
    )
    
    def __init__(self, name, description=None):
        self.name = name
        self.description = description or f"Role for {name}"
    
    def add_permission(self, permission):
        """Add a permission to this role."""
        if permission not in self.permissions:
            self.permissions.append(permission)
    
    def remove_permission(self, permission):
        """Remove a permission from this role."""
        if permission in self.permissions:
            self.permissions.remove(permission)
    
    def has_permission(self, permission_name):
        """Check if this role has the specified permission."""
        return any(p.name == permission_name for p in self.permissions)
    
    @classmethod
    def get_by_name(cls, name):
        """Get a role by name."""
        return cls.query.filter_by(name=name).first()
    
    def to_dict(self):
        """Convert role to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<Role {self.name}>'

class User(UserMixin, db.Model):
    """
    User model for authentication and authorization.
    
    This model represents a user in the system with authentication and authorization
    capabilities. It includes methods for password management, account status,
    and permission checking.
    """
    __tablename__ = 'users'
    
    # Basic user information
    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)  # Increased length for hashed passwords
    email = Column(String(255), unique=True, nullable=False, index=True)  # Increased length for email
    first_name = Column(String(100), nullable=True, index=True)
    last_name = Column(String(100), nullable=True, index=True)
    phone_number = Column(String(20), nullable=True, index=True)
    avatar_url = Column(String(255), nullable=True)
    timezone = Column(String(50), default='UTC', nullable=False)
    locale = Column(String(10), default='en_US', nullable=False)
    
    # Account status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_superuser = Column(Boolean, default=False, nullable=False, index=True)
    is_staff = Column(Boolean, default=False, nullable=False, index=True)
    
    # Email verification
    email_verified = Column(Boolean, default=False, nullable=False, index=True)
    email_verified_at = Column(DateTime, nullable=True)
    email_verification_token = Column(String(100), nullable=True, index=True)
    
    # Security fields
    last_login = Column(DateTime, nullable=True)
    last_login_ip = Column(String(45), nullable=True)
    last_activity = Column(DateTime, nullable=True)
    last_password_change = Column(DateTime, nullable=True)
    password_changed_at = Column(DateTime, nullable=True)
    login_attempts = Column(Integer, default=0, nullable=False)
    account_locked_until = Column(DateTime, nullable=True, index=True)
    must_change_password = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_seen = Column(DateTime, nullable=True)
    
    # Relationships
    role_id = Column(Integer, ForeignKey('roles.id'), index=True, nullable=True)
    role = relationship('Role', back_populates='users')
    
    # Security answers and questions
    security_answers = relationship('UserSecurityAnswer', back_populates='user', lazy='dynamic')
    security_questions = relationship(
        'SecurityQuestion',
        secondary='user_security_answers',
        viewonly=True,
        lazy='dynamic',
        back_populates='users',
        overlaps='user_answers,security_questions'
    )
    
    # Groups and permissions - using string literals for table names
    groups = relationship(
        'Group',
        secondary='user_groups',
        primaryjoin='User.id == user_groups.c.user_id',
        secondaryjoin='Group.id == user_groups.c.group_id',
        back_populates='users',
        lazy='dynamic'
    )
    permissions = relationship(
        'Permission',
        secondary='user_permissions',
        primaryjoin='User.id == user_permissions.c.user_id',
        secondaryjoin='Permission.id == user_permissions.c.permission_id',
        back_populates='users',
        lazy='dynamic'
    )
    
    # Security related - using string references to avoid circular imports
    password_history = relationship('PasswordHistory', back_populates='user', lazy='dynamic')
    failed_login_attempts = relationship('FailedLoginAttempt', back_populates='user', lazy='dynamic')
    tokens_blacklist = relationship('TokenBlacklist', back_populates='user')
    
    # User data - using string references to avoid circular imports
    consents = relationship('UserConsent', back_populates='user', lazy='dynamic')
    devices = relationship('UserDevice', back_populates='user', lazy='dynamic')
    activities = relationship('UserActivity', back_populates='user', order_by='UserActivity.created_at.desc()', lazy='dynamic')
    notifications = relationship('UserNotification', back_populates='user', order_by='UserNotification.created_at.desc()', lazy='dynamic')
    user_preferences = relationship('UserPreference', back_populates='user', lazy='dynamic')
    sessions = relationship('UserSession', back_populates='user', order_by='UserSession.last_activity.desc()', lazy='dynamic')
    
    # Audit logs (if using a separate audit log model)
    audit_logs = None  # Will be set up if using an audit log model
    
    def __init__(self, username, email, password=None, **kwargs):
        """
        Initialize a new user.
        
        Args:
            username (str): Unique username
            email (str): User's email address
            password (str, optional): Plain text password (will be hashed)
            **kwargs: Additional user attributes
        """
        from werkzeug.security import generate_password_hash
        
        self.username = username
        self.email = email
        self.first_name = kwargs.get('first_name')
        self.last_name = kwargs.get('last_name')
        self.phone_number = kwargs.get('phone_number')
        self.timezone = kwargs.get('timezone', 'UTC')
        self.locale = kwargs.get('locale', 'en_US')
        self.is_active = kwargs.get('is_active', True)
        self.email_verified = kwargs.get('email_verified', False)
        self.role_id = kwargs.get('role_id')
        
        # Set password if provided
        if password:
            self.set_password(password)
        
        # Set timestamps
        now = datetime.utcnow()
        self.created_at = now
        self.updated_at = now
        
        # Set last activity to now
        self.update_activity()
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def get_id(self):
        """Return the user's ID as a string (required by Flask-Login)."""
        return str(self.id)
    
    @property
    def full_name(self):
        """Return the user's full name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username
    
    @property
    def is_authenticated(self):
        """Check if the user is authenticated (required by Flask-Login)."""
        return True
    
    @property
    def is_anonymous(self):
        """Check if the user is anonymous (required by Flask-Login)."""
        return False
    
    @property
    def is_active_account(self):
        """Check if the user's account is active and not locked."""
        if not self.is_active:
            return False
            
        if self.account_locked_until and self.account_locked_until > datetime.utcnow():
            return False
            
        return True
    
    def set_password(self, password):
        """Set the user's password (hashes the password)."""
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)
        self.password_changed_at = datetime.utcnow()
        self.must_change_password = False
    
    def check_password(self, password):
        """Check if the provided password matches the user's hashed password."""
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)
    
    def update_activity(self, ip_address=None):
        """Update the user's last activity timestamp and IP address."""
        self.last_activity = datetime.utcnow()
        if ip_address:
            self.last_login_ip = ip_address
    
    def increment_login_attempts(self):
        """Increment the user's failed login attempts counter."""
        self.login_attempts += 1
        if self.login_attempts >= 5:  # Lock account after 5 failed attempts
            self.lock_account()
    
    def reset_login_attempts(self):
        """Reset the user's failed login attempts counter."""
        self.login_attempts = 0
    
    def lock_account(self, minutes=30):
        """Lock the user's account for the specified number of minutes."""
        self.account_locked_until = datetime.utcnow() + timedelta(minutes=minutes)
    
    def unlock_account(self):
        """Unlock the user's account."""
        self.account_locked_until = None
        self.login_attempts = 0
    
    def has_role(self, role_name):
        """Check if the user has the specified role."""
        if not self.role:
            return False
        return self.role.name == role_name
    
    def has_permission(self, permission_name):
        """Check if the user has the specified permission."""
        # Check direct permissions
        if self.permissions and any(p.name == permission_name for p in self.permissions):
            return True
            
        # Check role permissions
        if self.role and self.role.has_permission(permission_name):
            return True
            
        # Check group permissions
        if self.groups:
            for group in self.groups:
                if group.has_permission(permission_name):
                    return True
                    
        return False
    
    def to_dict(self):
        """Convert the user object to a dictionary."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'is_active': self.is_active,
            'email_verified': self.email_verified,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'role': self.role.name if self.role else None,
            'is_locked': self.account_locked_until is not None if self.account_locked_until else False
        }
    
    # Flask-Login methods
    # get_id is provided by UserMixin by default, using self.id
    # is_authenticated: provided by UserMixin, returns True if user is logged in
    # is_active: can be customized, e.g. if users can be deactivated. Default is True.
    # is_anonymous: provided by UserMixin, returns True if user is not logged in.

    def is_administrator(self):
        """Check if user has admin role."""
        return self.role and self.role.name.lower() == 'admin'
    
    def has_role(self, role_name):
        """Check if user has the specified role."""
        return self.role and self.role.name.lower() == role_name.lower()
    
    def set_password(self, password):
        """Set user password."""
        from werkzeug.security import generate_password_hash
        # Use pbkdf2:sha256 method which is more widely supported
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
    
    def check_password(self, password):
        """Check if the provided password is correct."""
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)
    
    def is_account_locked(self):
        """Check if the user's account is currently locked."""
        if self.account_locked_until is None:
            return False
        from datetime import datetime
        return datetime.utcnow() < self.account_locked_until
    
    def lock_account(self, minutes=30):
        """Lock the user's account for the specified number of minutes."""
        from datetime import datetime, timedelta
        self.account_locked_until = datetime.utcnow() + timedelta(minutes=minutes)
    
    def unlock_account(self):
        """Unlock the user's account."""
        self.account_locked_until = None
        self.login_attempts = 0
    
    def increment_login_attempts(self):
        """Increment the login attempt counter."""
        self.login_attempts += 1
    
    def reset_login_attempts(self):
        """Reset the login attempt counter."""
        self.login_attempts = 0
    
    def __repr__(self):
        return f'<User {self.username}>'


class PasswordResetToken(db.Model):
    """Modelo para almacenar tokens de restablecimiento de contraseña."""
    __tablename__ = 'password_reset_tokens'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    token = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)
    
    # Relación con el usuario
    user = relationship('User', backref='password_reset_tokens')
    
    def __init__(self, user_id, token, expires_in_hours=24):
        self.user_id = user_id
        self.token = token
        self.expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
    
    def is_expired(self):
        return datetime.utcnow() > self.expires_at
    
    def mark_as_used(self):
        self.is_used = True
        db.session.add(self)
        db.session.commit()
    
    def is_valid(self):
        return not self.is_expired() and not self.is_used
    
    def __repr__(self):
        return f'<PasswordResetToken {self.token} - User {self.user_id}>'


class EmailVerificationToken(db.Model):
    """Modelo para almacenar tokens de verificación de correo electrónico."""
    __tablename__ = 'email_verification_tokens'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, unique=True)
    token = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)
    
    # Relación con el usuario
    user = relationship('User', backref='email_verification_tokens')
    
    def __init__(self, user_id, token, expires_in_hours=72):
        self.user_id = user_id
        self.token = token
        self.expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
    
    def is_expired(self):
        return datetime.utcnow() > self.expires_at
    
    def mark_as_used(self):
        self.is_used = True
        db.session.add(self)
        db.session.commit()
    
    def is_valid(self):
        return not self.is_expired() and not self.is_used
    
    def __repr__(self):
        return f'<EmailVerificationToken {self.token} - User {self.user_id}>'


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
    user = relationship('User', backref='user_sessions')
    
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


class UserSecurityAnswer(db.Model):
    """Modelo para almacenar las respuestas de los usuarios a las preguntas de seguridad."""
    __tablename__ = 'user_security_answers'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey('security_questions.id', ondelete='CASCADE'), nullable=False, index=True)
    answer_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships - using string references to avoid circular imports
    user = relationship('User', back_populates='security_answers')
    question = relationship('SecurityQuestion', back_populates='user_answers', overlaps='user_answers,security_questions')
    
    # Add indexes for better query performance
    __table_args__ = (
        db.Index('idx_user_question', 'user_id', 'question_id', unique=True),
    )
    
    def __init__(self, user_id, question_id, answer_hash):
        """
        Inicializa una nueva respuesta de seguridad de usuario.
        
        Args:
            user_id (int): ID del usuario
            question_id (int): ID de la pregunta de seguridad
            answer_hash (str): Hash de la respuesta del usuario
        """
        self.user_id = user_id
        self.question_id = question_id
        self.answer_hash = answer_hash
    
    def set_answer(self, answer):
        """
        Establece la respuesta del usuario, hasheándola automáticamente.
        
        Args:
            answer (str): Respuesta en texto plano
        """
        from werkzeug.security import generate_password_hash
        self.answer_hash = generate_password_hash(answer)
    
    def check_answer(self, answer):
        """
        Verifica si la respuesta proporcionada coincide con la almacenada.
        
        Args:
            answer (str): Respuesta a verificar
            
        Returns:
            bool: True si la respuesta es correcta, False en caso contrario
        """
        from werkzeug.security import check_password_hash
        return check_password_hash(self.answer_hash, answer)
    
    def to_dict(self):
        """
        Convierte el objeto a un diccionario.
        
        Returns:
            dict: Representación en diccionario de la respuesta de seguridad
        """
        return {
            'id': self.id,
            'user_id': self.user_id,
            'question_id': self.question_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def get_user_answers(cls, user_id):
        """
        Obtiene todas las respuestas de seguridad de un usuario.
        
        Args:
            user_id (int): ID del usuario
            
        Returns:
            list: Lista de objetos UserSecurityAnswer
        """
        return cls.query.filter_by(user_id=user_id).all()
    
    @classmethod
    def get_user_answer_for_question(cls, user_id, question_id):
        """
        Obtiene la respuesta de un usuario para una pregunta específica.
        
        Args:
            user_id (int): ID del usuario
            question_id (int): ID de la pregunta
            
        Returns:
            UserSecurityAnswer or None: La respuesta del usuario o None si no existe
        """
        return cls.query.filter_by(user_id=user_id, question_id=question_id).first()
    
    def __repr__(self):
        return f'<UserSecurityAnswer {self.id} for User {self.user_id} Question {self.question_id}>'


# SecurityQuestion model has been moved to security_models.py to avoid circular imports
