"""Security models for the authentication system.

This module defines the security-related models for the application,
including user roles, permissions, and security events.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Text, JSON, Table, Index
from sqlalchemy.orm import relationship, backref
from database import db  # Importación absoluta
# SecurityQuestion model moved here to avoid circular imports
from . import associations  # Import association tables

# Import UserSecurityAnswer for type hints only
try:
    from .models import UserSecurityAnswer
except ImportError:
    # This is to handle the circular import issue during initialization
    UserSecurityAnswer = None

# Initialize tables
token_blacklist = None
password_history = None
failed_login_attempts = None
user_consents = None
user_devices = None
user_activities = None
user_notifications = None
user_preferences = None
groups = None
permissions = None

# Models
class TokenBlacklist(db.Model):
    """Track invalidated authentication tokens."""
    __tablename__ = 'token_blacklist'
    
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, index=True)
    token_type = db.Column(db.String(10), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    revoked_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    
    # Use string reference to avoid circular imports
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
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships using string literals for table names
    users = db.relationship(
        'User',
        secondary='user_groups',
        primaryjoin='Group.id == user_groups.c.group_id',
        secondaryjoin='User.id == user_groups.c.user_id',
        back_populates='groups',
        lazy='dynamic'
    )
    permissions = db.relationship(
        'Permission',
        secondary='group_permissions',
        primaryjoin='Group.id == group_permissions.c.group_id',
        secondaryjoin='Permission.id == group_permissions.c.permission_id',
        back_populates='groups',
        lazy='dynamic'
    )


class Permission(db.Model):
    """Permissions for fine-grained access control."""
    __tablename__ = 'permissions'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    resource = db.Column(db.String(100), index=True)
    action = db.Column(db.String(50), index=True)
    
    # Relationships using string literals for table names
    users = db.relationship(
        'User',
        secondary='user_permissions',
        primaryjoin='Permission.id == user_permissions.c.permission_id',
        secondaryjoin='User.id == user_permissions.c.user_id',
        back_populates='permissions',
        lazy='dynamic'
    )
    groups = db.relationship(
        'Group',
        secondary='group_permissions',
        primaryjoin='Permission.id == group_permissions.c.permission_id',
        secondaryjoin='Group.id == group_permissions.c.group_id',
        back_populates='permissions',
        lazy='dynamic'
    )
    roles = db.relationship(
        'Role',
        secondary=lambda: get_role_permissions_association(),
        primaryjoin='Permission.id == role_permissions.c.permission_id',
        secondaryjoin='Role.id == role_permissions.c.role_id',
        back_populates='permissions',
        lazy='dynamic',
        viewonly=False
    )


def create_default_roles_and_permissions():
    """Create default roles and permissions if they don't exist."""
    # Import here to avoid circular imports
    from .models import Role as RoleModel, User
    from . import associations
    
    try:
        # Default roles
        admin_role = RoleModel.query.filter_by(name='admin').first()
        if not admin_role:
            admin_role = RoleModel(
                name='admin',
                description='Administrator with full access to all features'
            )
            admin_role.is_system_role = True
            db.session.add(admin_role)
        
        user_role = RoleModel.query.filter_by(name='user').first()
        if not user_role:
            user_role = RoleModel(
                name='user',
                description='Regular user with basic access'
            )
            user_role.is_system_role = True
            db.session.add(user_role)
        
        # Commit roles first to get their IDs
        db.session.commit()
        
        # Default permissions
        permissions_data = [
            ('admin', 'Access to admin interface', 'admin', 'access'),
            ('manage_users', 'Manage users', 'users', 'manage'),
            ('view_users', 'View users', 'users', 'view'),
            ('manage_roles', 'Manage roles', 'roles', 'manage'),
            ('view_roles', 'View roles', 'roles', 'view'),
        ]
        
        permissions = []
        for name, description, resource, action in permissions_data:
            permission = Permission.query.filter_by(name=name).first()
            if not permission:
                permission = Permission(
                    name=name,
                    description=description,
                    resource=resource,
                    action=action
                )
                db.session.add(permission)
                permissions.append(permission)
        
        # Commit all permission changes
        db.session.commit()
        
        # Assign all permissions to admin role
        if admin_role:
            for permission in permissions:
                if not admin_role.permissions.filter_by(id=permission.id).first():
                    admin_role.permissions.append(permission)
        
        # Assign basic view permissions to user role
        if user_role:
            view_permissions = [p for p in permissions if p.action == 'view']
            for permission in view_permissions:
                if not user_role.permissions.filter_by(id=permission.id).first():
                    user_role.permissions.append(permission)
        
        # Get or create an admin user to assign role
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(
                username='admin',
                email='admin@example.com',
                password='admin123',  # This should be hashed in a real application
                is_active=True,
                email_verified=True,
                role_id=admin_role.id
            )
            db.session.add(admin_user)
        else:
            # Ensure admin user has the admin role
            admin_user.role_id = admin_role.id
        
        # Commit all changes
        db.session.commit()
        
        return True
    except Exception as e:
        db.session.rollback()
        print(f"Error in create_default_roles_and_permissions: {str(e)}")
        raise

def create_association_tables():
    """Return all association tables.
    
    Returns:
        tuple: A tuple containing (user_roles, user_groups, user_permissions, group_permissions)
    """
    from . import associations
    return (
        associations.user_roles,
        associations.user_groups,
        associations.user_permissions,
        associations.group_permissions
    )

def get_role_permissions_association():
    """Return the role_permissions association table."""
    from . import associations
    return associations.role_permissions

class SecurityQuestion(db.Model):
    """Modelo para almacenar las preguntas de seguridad disponibles."""
    __tablename__ = 'security_questions'
    
    id = Column(Integer, primary_key=True)
    question_text = Column(String(255), unique=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships - using string references to avoid circular imports
    user_answers = relationship('UserSecurityAnswer', back_populates='question')
    users = relationship(
        'User',
        secondary='user_security_answers',
        viewonly=True,
        lazy='dynamic',
        back_populates='security_questions',
        overlaps='security_answers,security_questions'
    )
    
    # Add index for better query performance
    __table_args__ = (
        db.Index('idx_question_active', 'is_active'),
    )
    
    def __init__(self, question_text, is_active=True):
        self.question_text = question_text
        self.is_active = is_active
    
    def to_dict(self):
        """Convierte el objeto a un diccionario."""
        return {
            'id': self.id,
            'question': self.question_text,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def get_active_questions(cls):
        """Obtiene todas las preguntas de seguridad activas."""
        return cls.query.filter_by(is_active=True).all()
    
    def __repr__(self):
        return f'<SecurityQuestion {self.id}: {self.question_text}>'

# Las tablas de asociación se crean dinámicamente cuando se llama a create_association_tables()
# después de que todos los modelos estén definidos
