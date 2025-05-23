from datetime import datetime, timedelta
from sqlalchemy.orm import relationship, backref
from database import db  # Importación absoluta

"""Security models for the authentication system.

This module defines the security-related models for the application,
including user roles, permissions, and security events.
"""

from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Text, JSON, Table
from sqlalchemy.orm import relationship, backref
from database import db  # Importación absoluta

# Initialize tables as None - will be set by create_association_tables()
user_roles = None
user_groups = None
user_permissions = None
group_permissions = None

# Association tables will be created after all models are defined
token_blacklist = None
password_history = None
failed_login_attempts = None
security_questions = None
user_consents = None
user_devices = None
user_activities = None
user_notifications = None
user_preferences = None
groups = None
permissions = None

def create_association_tables():
    """Crea las tablas de asociación después de que los modelos estén definidos."""
    global user_roles, user_groups, user_permissions, group_permissions
    
    # Tabla de asociación para usuarios y roles
    user_roles = db.Table('user_roles',
        db.Column('user_id', db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        db.Column('role_id', db.Integer, db.ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
        db.Column('assigned_at', db.DateTime, default=datetime.utcnow, nullable=False),
        db.Column('assigned_by', db.Integer, db.ForeignKey('users.id', ondelete='SET NULL')),
        db.Column('expires_at', db.DateTime, nullable=True),
        db.Column('is_active', db.Boolean, default=True, nullable=False)
    )
    
    # Tabla de asociación para usuarios y grupos
    user_groups = db.Table('user_groups',
        db.Column('user_id', db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        db.Column('group_id', db.Integer, db.ForeignKey('groups.id', ondelete='CASCADE'), primary_key=True),
        db.Column('assigned_at', db.DateTime, default=datetime.utcnow, nullable=False),
        db.Column('assigned_by', db.Integer, db.ForeignKey('users.id', ondelete='SET NULL')),
        db.Column('expires_at', db.DateTime, nullable=True),
        db.Column('is_active', db.Boolean, default=True, nullable=False)
    )
    
    # Tabla de asociación para usuarios y permisos directos
    user_permissions = db.Table('user_permissions',
        db.Column('user_id', db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        db.Column('permission_id', db.Integer, db.ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True),
        db.Column('granted_at', db.DateTime, default=datetime.utcnow, nullable=False),
        db.Column('granted_by', db.Integer, db.ForeignKey('users.id', ondelete='SET NULL')),
        db.Column('expires_at', db.DateTime, nullable=True),
        db.Column('is_active', db.Boolean, default=True, nullable=False)
    )
    
    # Tabla de asociación para grupos y permisos
    group_permissions = db.Table('group_permissions',
        db.Column('group_id', db.Integer, db.ForeignKey('groups.id', ondelete='CASCADE'), primary_key=True),
        db.Column('permission_id', db.Integer, db.ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True),
        db.Column('granted_at', db.DateTime, default=datetime.utcnow, nullable=False),
        db.Column('granted_by', db.Integer, db.ForeignKey('users.id', ondelete='SET NULL')),
        db.Column('expires_at', db.DateTime, nullable=True),
        db.Column('is_active', db.Boolean, default=True, nullable=False)
    )
    
    return user_roles, user_groups, user_permissions, group_permissions

# Inicializar las tablas como None
user_roles = None
user_groups = None
user_permissions = None
group_permissions = None

# Models
class TokenBlacklist(db.Model):
    """Track invalidated authentication tokens."""
    __tablename__ = 'token_blacklist'
    
    # Relationships will be set up in init_models
    user = None  # Will be set in init_models
    
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, index=True)
    token_type = db.Column(db.String(10), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    revoked_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    
    user = db.relationship('User', back_populates='tokens_blacklist')


class PasswordHistory(db.Model):
    """Store password history to prevent password reuse."""
    __tablename__ = 'password_history'
    
    # Relationships will be set up in init_models
    user = None  # Will be set in init_models
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', back_populates='password_history')


class FailedLoginAttempt(db.Model):
    """Track failed login attempts for security monitoring."""
    __tablename__ = 'failed_login_attempts'
    
    # Relationships will be set up in init_models
    user = None  # Will be set in init_models
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    attempted_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    user = db.relationship('User', back_populates='failed_login_attempts')


class SecurityQuestion(db.Model):
    """Security questions for account recovery."""
    __tablename__ = 'security_questions'
    
    # Relationships will be set up in init_models
    user = None  # Will be set in init_models
    user_answers = None  # Will be set in init_models
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    question = db.Column(db.String(255), nullable=False)
    answer_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', back_populates='security_questions')


class UserConsent(db.Model):
    """Track user consents (GDPR, terms of service, etc.)."""
    __tablename__ = 'user_consents'
    
    # Relationships will be set up in init_models
    user = None  # Will be set in init_models
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    consent_type = db.Column(db.String(50), nullable=False)  # e.g., 'terms', 'privacy_policy'
    granted = db.Column(db.Boolean, default=True, nullable=False)
    granted_at = db.Column(db.DateTime, default=datetime.utcnow)
    revoked_at = db.Column(db.DateTime, nullable=True)
    version = db.Column(db.String(20), nullable=False)  # Version of the terms/policy
    
    user = db.relationship('User', back_populates='consents')


class UserDevice(db.Model):
    """Track user devices for device recognition."""
    __tablename__ = 'user_devices'
    
    # Relationships will be set up in init_models
    user = None  # Will be set in init_models
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    device_id = db.Column(db.String(64), nullable=False, index=True)
    device_name = db.Column(db.String(100))
    device_type = db.Column(db.String(50))  # e.g., 'mobile', 'tablet', 'desktop'
    os = db.Column(db.String(50))
    browser = db.Column(db.String(50))
    last_used = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_trusted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', back_populates='devices')


class UserActivity(db.Model):
    """Track user activities for analytics and security."""
    __tablename__ = 'user_activities'
    
    # Relationships will be set up in init_models
    user = None  # Will be set in init_models
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    activity_type = db.Column(db.String(50), nullable=False, index=True)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    details = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    user = db.relationship('User', back_populates='activities')


class UserNotification(db.Model):
    """User notifications."""
    __tablename__ = 'user_notifications'
    
    # Relationships will be set up in init_models
    user = None  # Will be set in init_models
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False, index=True)
    notification_type = db.Column(db.String(50), index=True)  # e.g., 'info', 'warning', 'success', 'error'
    action_url = db.Column(db.String(255))  # URL to take action on the notification
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    read_at = db.Column(db.DateTime, nullable=True)
    
    user = db.relationship('User', back_populates='notifications')


class UserPreference(db.Model):
    """User preferences and settings."""
    __tablename__ = 'user_preferences'
    
    # Relationships will be set up in init_models
    user = None  # Will be set in init_models
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    preference_key = db.Column(db.String(100), nullable=False, index=True)
    preference_value = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'preference_key', name='_user_preference_uc'),
    )
    
    user = db.relationship('User', back_populates='user_preferences')


class Group(db.Model):
    """User groups for group-based access control."""
    __tablename__ = 'groups'
    
    # Relationships will be set up in init_models
    users = None  # Will be set in init_models
    permissions = None  # Will be set in init_models
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    users = db.relationship('User', secondary=user_groups, back_populates='groups')
    permissions = db.relationship('Permission', secondary='group_permissions', back_populates='groups')


class Permission(db.Model):
    """Permissions for fine-grained access control."""
    __tablename__ = 'permissions'
    
    # Relationships will be set up in init_models
    users = None  # Will be set in init_models
    groups = None  # Will be set in init_models
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    resource = db.Column(db.String(100), index=True)  # e.g., 'user', 'document', 'settings'
    action = db.Column(db.String(50), index=True)  # e.g., 'create', 'read', 'update', 'delete'
    
    users = db.relationship('User', secondary=user_permissions, back_populates='permissions')
    groups = db.relationship('Group', secondary='group_permissions', back_populates='permissions')


# Las tablas de asociación se crean dinámicamente cuando se llama a create_association_tables()
# después de que todos los modelos estén definidos
