from flask import Blueprint, current_app, redirect, url_for, flash, request, session
from flask_login import LoginManager, current_user, user_logged_in, user_logged_out
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()

# Import admin after db is initialized
from .admin import init_admin as init_auth_admin

# Import security models after db is initialized
from .security_models import (
    TokenBlacklist, PasswordHistory, FailedLoginAttempt, SecurityQuestion,
    UserConsent, UserDevice, UserActivity, UserNotification, UserPreference,
    Group, Permission, user_roles, user_groups, user_permissions, group_permissions
)

# Import models after db is defined to avoid circular imports
from .models import User, Role, PasswordResetToken, EmailVerificationToken, UserSession, SecurityEvent

# Security configuration
MAX_LOGIN_ATTEMPTS = 5
ACCOUNT_LOCKOUT_MINUTES = 30
SESSION_TIMEOUT_MINUTES = 30
PASSWORD_HISTORY_LIMIT = 5
MFA_REQUIRED_ROLES = ['admin', 'staff']

# Session configuration
PERMANENT_SESSION_LIFETIME = timedelta(minutes=SESSION_TIMEOUT_MINUTES)
SESSION_REFRESH_EACH_REQUEST = True

# Login manager configuration
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'
login_manager.login_message_category = 'info'
login_manager.refresh_view = 'auth.reauthenticate'
login_manager.needs_refresh_message = 'Por favor, vuelve a iniciar sesión para acceder a esta página.'
login_manager.needs_refresh_message_category = 'info'
login_manager.session_protection = 'strong'  # or 'basic' or None

# Track login activity
@user_logged_in.connect_via(current_app._get_current_object())
def on_user_logged_in(sender, user, **extra):
    """Track successful logins."""
    user.last_login = datetime.utcnow()
    user.login_attempts = 0  # Reset login attempts on successful login
    user.account_locked_until = None  # Unlock account if it was locked
    
    # Create a new session
    session_id = session.sid
    user_agent = request.headers.get('User-Agent', '')
    ip_address = request.remote_addr
    
    # Create a new session record
    new_session = UserSession(
        user_id=user.id,
        session_id=session_id,
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=datetime.utcnow() + PERMANENT_SESSION_LIFETIME,
        is_active=True
    )
    
    # Log the security event
    security_event = SecurityEvent(
        user_id=user.id,
        event_type=SecurityEventType.LOGIN_SUCCESS,
        ip_address=ip_address,
        user_agent=user_agent,
        details={'session_id': session_id}
    )
    
    try:
        db.session.add(new_session)
        db.session.add(security_event)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f'Error tracking login: {str(e)}')
        db.session.rollback()

@user_logged_out.connect_via(current_app._get_current_object())
def on_user_logged_out(sender, user, **extra):
    """Track user logouts."""
    if user and user.is_authenticated:
        # Mark session as inactive
        session_id = session.sid
        user_session = UserSession.query.filter_by(
            user_id=user.id,
            session_id=session_id,
            is_active=True
        ).first()
        
        if user_session:
            user_session.is_active = False
            user_session.last_seen = datetime.utcnow()
            
            # Log the security event
            security_event = SecurityEvent(
                user_id=user.id,
                event_type=SecurityEventType.SESSION_REVOKED,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', ''),
                details={'session_id': session_id}
            )
            
            try:
                db.session.add(security_event)
                db.session.commit()
            except Exception as e:
                current_app.logger.error(f'Error tracking logout: {str(e)}')
                db.session.rollback()

# Create the auth blueprint with template folder
auth_bp = Blueprint(
    'auth',
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/auth/static'
)

# Login manager configuration
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'
login_manager.login_message_category = 'info'
login_manager.session_protection = 'strong'

# Import models after db is defined to avoid circular imports
# Models will be imported when needed in the views

# Import models after db is defined to avoid circular imports
# Get the directory of the current module
current_dir = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(current_dir, 'templates')

# Create the auth blueprint with template folder
auth_bp.template_folder = template_dir
auth_bp.url_prefix = '/auth'
auth_bp.static_folder = 'static'
auth_bp.static_url_path = '/auth/static'

# Import models after db is defined to avoid circular imports
# Models will be imported when needed in the views

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login."""
    if user_id is not None:
        return User.query.get(int(user_id))
    return None

@login_manager.unauthorized_handler
def unauthorized():
    """Handle unauthorized access attempts."""
    if current_user.is_authenticated:
        flash('No tienes permiso para acceder a esta página.', 'warning')
        return redirect(url_for('main.index'))
    else:
        flash('Por favor inicia sesión para acceder a esta página.', 'info')
        return redirect(url_for('auth.login', next=request.full_path))

def init_app(app):
    """Initialize authentication extensions with app context."""
    # Initialize Flask extensions with the app
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.refresh_view = 'auth.reauthenticate'
    
    # Set up user loader
    login_manager.user_loader(load_user)
    login_manager.unauthorized_handler(unauthorized)
    
    # Register blueprints
    from . import views, forms  # Import here to avoid circular imports
    
    # Register the auth blueprint
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    # Initialize admin interface after db is set up
    with app.app_context():
        # Create database tables if they don't exist
        db.create_all()
        
        # Create default roles if they don't exist
        from .models import Role
        Role.insert_roles()
        
        # Initialize admin interface with the app and db
        from .admin import init_admin as init_auth_admin
        init_auth_admin(app, db)
    
    return app

# Import views after creating the blueprint to avoid circular imports
from . import views, forms