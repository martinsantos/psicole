from datetime import datetime, timedelta
import secrets
import enum
from flask import current_app, request
from flask_login import UserMixin, AnonymousUserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import relationship, backref
from sqlalchemy import event, Enum
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired


class SecurityEventType(enum.Enum):
    """Types of security events to track."""
    LOGIN_SUCCESS = 'login_success'
    LOGIN_FAILED = 'login_failed'
    PASSWORD_CHANGED = 'password_changed'
    EMAIL_VERIFIED = 'email_verified'
    PASSWORD_RESET_REQUESTED = 'password_reset_requested'
    PASSWORD_RESET = 'password_reset'
    ACCOUNT_LOCKED = 'account_locked'
    ACCOUNT_UNLOCKED = 'account_unlocked'
    SESSION_CREATED = 'session_created'
    SESSION_REVOKED = 'session_revoked'
    ROLE_CHANGED = 'role_changed'
    PROFILE_UPDATED = 'profile_updated'

# Import the database instance from the auth package
from . import db

class Permission:
    """Permission bits for different user roles."""
    FOLLOW = 0x01
    COMMENT = 0x02
    WRITE_ARTICLES = 0x04
    MODERATE_COMMENTS = 0x08
    ADMINISTER = 0x80

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False, index=True)
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)
    users = db.relationship('User', backref='role', lazy='dynamic')

    def __init__(self, **kwargs):
        super(Role, self).__init__(**kwargs)
        if self.permissions is None:
            self.permissions = 0

    @staticmethod
    def insert_roles():
        """Insert default roles with permissions."""
        roles = {
            'user': [
                Permission.FOLLOW,
                Permission.COMMENT,
                Permission.WRITE_ARTICLES
            ],
            'moderator': [
                Permission.FOLLOW,
                Permission.COMMENT,
                Permission.WRITE_ARTICLES,
                Permission.MODERATE_COMMENTS
            ],
            'administrator': [
                Permission.FOLLOW,
                Permission.COMMENT,
                Permission.WRITE_ARTICLES,
                Permission.MODERATE_COMMENTS,
                Permission.ADMINISTER
            ]
        }
        
        default_role = 'user'
        
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            
            # Reset permissions
            role.reset_permissions()
            
            # Add permissions
            for perm in roles[r]:
                role.add_permission(perm)
            
            # Set default role
            role.default = (role.name == default_role)
            
            db.session.add(role)
        
        db.session.commit()
    
    def add_permission(self, perm):
        """Add a permission to this role."""
        if not self.has_permission(perm):
            self.permissions += perm
    
    def remove_permission(self, perm):
        """Remove a permission from this role."""
        if self.has_permission(perm):
            self.permissions -= perm
    
    def reset_permissions(self):
        """Reset all permissions."""
        self.permissions = 0
    
    def has_permission(self, perm):
        """Check if role has a specific permission."""
        return self.permissions & perm == perm
    
    def __repr__(self):
        return f'<Role {self.name}>'

class SecurityEvent(db.Model):
    """Track security-related events for users."""
    __tablename__ = 'security_events'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    event_type = db.Column(Enum(SecurityEventType), nullable=False, index=True)
    ip_address = db.Column(db.String(45))  # IPv6 can be up to 45 chars
    user_agent = db.Column(db.Text)
    details = db.Column(db.Text)  # JSON string with additional details
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    user = relationship('User', back_populates='security_events')
    
    def __init__(self, user_id, event_type, ip_address=None, user_agent=None, details=None):
        self.user_id = user_id
        self.event_type = event_type
        self.ip_address = ip_address or request.remote_addr if request else None
        self.user_agent = user_agent or (request.user_agent.string if request and hasattr(request, 'user_agent') else None)
        self.details = str(details) if details else None


class UserSession(db.Model):
    """Track user sessions for security and analytics."""
    __tablename__ = 'user_sessions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    session_id = db.Column(db.String(64), nullable=False, index=True)
    ip_address = db.Column(db.String(45))  # IPv6 can be up to 45 chars
    user_agent = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    
    user = relationship('User', back_populates='sessions')
    
    def is_expired(self):
        return datetime.utcnow() > self.expires_at

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    # Account information
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    is_active = db.Column(db.Boolean, default=True, index=True)
    is_verified = db.Column(db.Boolean, default=False, index=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    last_login = db.Column(db.DateTime, index=True)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)
    
    # Security fields
    login_attempts = db.Column(db.Integer, default=0, nullable=False)
    account_locked_until = db.Column(db.DateTime, nullable=True)
    mfa_enabled = db.Column(db.Boolean, default=False, nullable=False)
    mfa_secret = db.Column(db.String(32), nullable=True)  # Base32 secret for TOTP
    
    # Relationships
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    password_reset_tokens = relationship('PasswordResetToken', back_populates='user', cascade='all, delete-orphan')
    email_verification_tokens = relationship('EmailVerificationToken', back_populates='user', cascade='all, delete-orphan')
    sessions = relationship('UserSession', back_populates='user', cascade='all, delete-orphan')
    security_events = relationship('SecurityEvent', back_populates='user', cascade='all, delete-orphan', order_by='desc(SecurityEvent.created_at)')
    
    # Token blacklist for JWT
    tokens_blacklist = relationship('TokenBlacklist', back_populates='user', cascade='all, delete-orphan')
    
    # User preferences
    preferences = db.Column(db.JSON, default=dict, nullable=False)
    
    # Track password history for security
    password_history = relationship('PasswordHistory', back_populates='user', cascade='all, delete-orphan')
    
    # Track failed login attempts
    failed_login_attempts = relationship('FailedLoginAttempt', back_populates='user', cascade='all, delete-orphan')
    
    # Track active sessions
    active_sessions = relationship('UserSession', 
                                 primaryjoin="and_(User.id==UserSession.user_id, "
                                            "UserSession.is_active==True)",
                                 viewonly=True)
    
    # Track security questions for account recovery
    security_questions = relationship('SecurityQuestion', back_populates='user', cascade='all, delete-orphan')
    
    # Track user consents (GDPR, terms of service, etc.)
    consents = relationship('UserConsent', back_populates='user', cascade='all, delete-orphan')
    
    # Track user devices for device recognition
    devices = relationship('UserDevice', back_populates='user', cascade='all, delete-orphan')
    
    # Track user activity
    activities = relationship('UserActivity', back_populates='user', cascade='all, delete-orphan')
    
    # Track user notifications
    notifications = relationship('UserNotification', back_populates='user', cascade='all, delete-orphan')
    
    # Track user roles (for role-based access control)
    roles = relationship('Role', secondary='user_roles', back_populates='users')
    
    # Track user groups (for group-based access control)
    groups = relationship('Group', secondary='user_groups', back_populates='users')
    
    # Track user permissions (direct permissions)
    permissions = relationship('Permission', secondary='user_permissions', back_populates='users')
    
    # Track user preferences
    user_preferences = relationship('UserPreference', back_populates='user', cascade='all, delete-orphan')
    
    # Track user sessions
    user_sessions = relationship('UserSession', back_populates='user', cascade='all, delete-orphan')
    
    # Track security events
    security_events = relationship('SecurityEvent', back_populates='user', cascade='all, delete-orphan')
    
    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            if self.email == current_app.config.get('ADMIN_EMAIL'):
                self.role = Role.query.filter_by(permissions=0xff).first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()
    
    def set_password(self, password):
        """Set password hash from plaintext password."""
        self.password_hash = generate_password_hash(
            password,
            method='pbkdf2:sha256',
            salt_length=16
        )
    
    def check_password(self, password):
        """Check if the provided password matches the stored hash."""
        return check_password_hash(self.password_hash, password)
    
    def can(self, permissions):
        """Check if user has the required permissions."""
        return self.role is not None and \
               (self.role.permissions & permissions) == permissions
    
    def is_administrator(self):
        """Check if user has administrator privileges."""
        return self.can(Permission.ADMINISTER)
        
    def has_role(self, role_name):
        """Check if user has a specific role."""
        if isinstance(role_name, str):
            return self.role and self.role.name.lower() == role_name.lower()
        return False
        
    def has_any_role(self, *role_names):
        """Check if user has any of the specified roles."""
        if not self.role or not role_names:
            return False
        return self.role.name.lower() in [name.lower() for name in role_names]
        
    def get_full_name(self):
        """Return the user's full name."""
        if hasattr(self, 'first_name') and hasattr(self, 'last_name'):
            return f"{self.first_name} {self.last_name}".strip()
        return self.username or self.email.split('@')[0]
    
    def generate_auth_token(self, expiration=3600):
        """Generate authentication token for API access."""
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        return s.dumps({'id': self.id})

    @staticmethod
    def verify_auth_token(token, max_age=3600):
        """Verify authentication token and return user if valid."""
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token, max_age=max_age)
        except (BadSignature, SignatureExpired):
            return None
        return User.query.get(data['id'])
    
    def ping(self):
        """Update last seen timestamp."""
        self.last_seen = datetime.utcnow()
        db.session.add(self)
        db.session.commit()
    
    def __repr__(self):
        return f'<User {self.username}>'


class AnonymousUser(AnonymousUserMixin):
    """Anonymous user class with default permissions."""
    def can(self, permissions):
        return False
    
    def is_administrator(self):
        return False


class PasswordResetToken(db.Model):
    """Store password reset tokens for users."""
    __tablename__ = 'password_reset_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(128), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    
    # Relationships
    user = relationship('User', back_populates='password_reset_tokens')
    
    def is_expired(self):
        """Check if the token has expired."""
        return datetime.utcnow() > self.expires_at
    
    @classmethod
    def generate_token(cls, user, expires_in=3600):
        """Generate a new password reset token for the user."""
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        token = s.dumps({'user_id': user.id, 'exp': expires_in})
        
        # Create and save the token
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        reset_token = cls(
            token=token,
            user_id=user.id,
            expires_at=expires_at
        )
        db.session.add(reset_token)
        db.session.commit()
        
        return token
    
    @classmethod
    def verify_token(cls, token, max_age=3600):
        """Verify a password reset token and return the user if valid."""
        if not token:
            return None
            
        # First check if token exists in the database
        reset_token = cls.query.filter_by(token=token).first()
        if not reset_token or reset_token.is_expired():
            return None
            
        # Verify the token signature and expiration
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token, max_age=max_age)
        except (BadSignature, SignatureExpired):
            return None
            
        # Return the user
        return User.query.get(data['user_id'])


class EmailVerificationToken(db.Model):
    """Store email verification tokens for users."""
    __tablename__ = 'email_verification_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(128), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    new_email = db.Column(db.String(120), nullable=True)  # For email change requests
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    
    # Relationships
    user = relationship('User', back_populates='email_verification_tokens')
    
    def is_expired(self):
        """Check if the token has expired."""
        return datetime.utcnow() > self.expires_at
    
    @classmethod
    def generate_token(cls, user, expires_in=86400, new_email=None):
        """Generate a new email verification token for the user."""
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        token_data = {'user_id': user.id, 'exp': expires_in}
        if new_email:
            token_data['new_email'] = new_email
        token = s.dumps(token_data)
        
        # Create and save the token
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        verification_token = cls(
            token=token,
            user_id=user.id,
            new_email=new_email,
            expires_at=expires_at
        )
        db.session.add(verification_token)
        db.session.commit()
        
        return token
    
    @classmethod
    def verify_token(cls, token, max_age=86400):
        """Verify an email verification token and return the user if valid."""
        verification_token = cls.query.filter_by(token=token).first()
        
        if verification_token is None or verification_token.is_expired():
            return None
            
        return verification_token


# Import login_manager from auth/__init__.py
from . import login_manager

# Set the anonymous user class for Flask-Login
login_manager.anonymous_user = AnonymousUser

# Ensure all models are imported for SQLAlchemy to work properly
__all__ = ['User', 'Role', 'Permission', 'PasswordResetToken', 'EmailVerificationToken']
