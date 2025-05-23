from flask import Blueprint, current_app, redirect, url_for, flash, request, session
from flask_login import LoginManager, current_user, user_logged_in, user_logged_out
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os

# Initialize extensions
db = None  # Will be set by init_app
login_manager = LoginManager()
mail = Mail()

# Import admin after db is initialized
from .admin import init_admin as init_auth_admin

# Placeholder for association tables
user_roles = None
user_groups = None
user_permissions = None
group_permissions = None

# Dictionary to hold all models for easy access
models = {}

def init_models():
    """Initialize models after db is available."""
    global user_roles, user_groups, user_permissions, group_permissions, models
    
    try:
        # Import models after db is initialized
        from .security_models import (
            TokenBlacklist, PasswordHistory, FailedLoginAttempt, SecurityQuestion,
            UserConsent, UserDevice, UserActivity, UserNotification, UserPreference,
            Group, Permission, create_association_tables
        )
        
        # Import remaining models
        from .models import (
            User, Role, PasswordResetToken, EmailVerificationToken, 
            SecurityEvent, UserSession, SecurityEventType, UserSecurityAnswer,
            init_models as init_models_relationships
        )
        
        # Create association tables
        user_roles, user_groups, user_permissions, group_permissions = create_association_tables()
        
        # Initialize model relationships
        models = init_models_relationships()
        
        # Add SecurityEventType to models
        models['SecurityEventType'] = SecurityEventType
        
        # Update global models dictionary
        globals().update(models)
        
        return models
    except Exception as e:
        current_app.logger.error(f"Error initializing models: {str(e)}")
        raise

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
def _on_user_logged_in(sender, user, **extra):
    """Track successful logins."""
    from flask import session, request
    from datetime import datetime
    
    try:
        # Ensure we have the required global variables
        global UserSession, SecurityEvent, SecurityEventType, db, PERMANENT_SESSION_LIFETIME
        
        # Update user login information
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
        
        # Save changes to the database
        db.session.add(new_session)
        db.session.add(security_event)
        db.session.commit()
        
    except Exception as e:
        current_app.logger.error(f'Error tracking login: {str(e)}')
        if 'db' in globals() and hasattr(db, 'session'):
            db.session.rollback()

def _on_user_logged_out(sender, user, **extra):
    """Track user logouts."""
    from flask import session, request
    from datetime import datetime
    
    try:
        # Ensure we have the required global variables
        global UserSession, SecurityEvent, SecurityEventType, db
        
        if user and user.is_authenticated:
            # Mark session as inactive
            session_id = session.sid if 'sid' in dir(session) else None
            
            if not session_id:
                current_app.logger.warning('No session ID found during logout')
                return
                
            # Find the active session
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
                
                # Save changes to the database
                db.session.add(security_event)
                db.session.commit()
    
    except Exception as e:
        current_app.logger.error(f'Error tracking logout: {str(e)}')
        if 'db' in globals() and hasattr(db, 'session'):
            db.session.rollback()
        # Re-raise the exception to ensure Flask-Login is aware of the error
        raise

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
    global User
    if user_id is not None:
        return User.query.get(int(user_id))
    return None

@login_manager.unauthorized_handler
def unauthorized():
    """Handle unauthorized access attempts."""
    from flask_login import current_user
    
    if current_user.is_authenticated:
        from flask import flash, redirect, url_for, request
        flash('No tienes permiso para acceder a esta página.', 'warning')
        return redirect(url_for('main.index'))
    else:
        flash('Por favor inicia sesión para acceder a esta página.', 'info')
        return redirect(url_for('auth.login', next=request.full_path))

def init_app(app, db_instance=None):
    """Initialize authentication extensions with app context."""
    global db, models
    
    # Set the db instance if provided
    if db_instance is not None:
        db = db_instance
    
    # Initialize Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'
    login_manager.login_message_category = 'info'
    
    # Initialize Flask-Mail
    mail.init_app(app)
    
    # Register blueprints
    from . import routes
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    # Initialize admin interface
    init_auth_admin(app)
    
    # Register login/logout handlers
    user_logged_in.connect(_on_user_logged_in, app)
    user_logged_out.connect(_on_user_logged_out, app)
    
    # Initialize models if they haven't been initialized yet
    if db is not None:
        with app.app_context():
            try:
                # Initialize models and relationships
                models = init_models()
                
                # Create all database tables
                db.create_all()
                
                # Create default roles if they don't exist
                Role = models.get('Role')
                User = models.get('User')
                
                admin_role = Role.query.filter_by(name='admin').first()
                if not admin_role:
                    admin_role = Role(name='admin', description='Administrator with full access')
                    db.session.add(admin_role)
                
                user_role = Role.query.filter_by(name='user').first()
                if not user_role:
                    user_role = Role(name='user', description='Regular user with basic access')
                    db.session.add(user_role)
                
                # Create default admin user if it doesn't exist
                admin_user = User.query.filter_by(username='admin').first()
                if not admin_user:
                    from werkzeug.security import generate_password_hash
                    admin_user = User(
                        username='admin',
                        password_hash=generate_password_hash('admin'),
                        email='admin@example.com',
                        first_name='Admin',
                        last_name='User',
                        is_active=True,
                        email_verified=True
                    )
                    admin_user.role = admin_role
                    db.session.add(admin_user)
                
                db.session.commit()
                
                app.logger.info("Authentication system initialized successfully")
                
            except Exception as e:
                app.logger.error(f'Error initializing auth models: {str(e)}')
                if 'db' in locals() and db.session:
                    db.session.rollback()
                raise
    
    # Make db available globally
    globals()['db'] = db
    
    return app

# Import views after creating the blueprint to avoid circular imports
from . import views, forms