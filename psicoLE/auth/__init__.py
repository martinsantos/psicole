"""Authentication and authorization package.

This package provides user authentication and authorization functionality.
"""

from flask import Blueprint, current_app, redirect, url_for, flash, request, session
from flask_login import LoginManager, current_user, user_logged_in, user_logged_out
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os

# Initialize extensions
from flask_principal import Principal

login_manager = LoginManager()
mail = Mail()
principal = Principal()

# Import association tables first to avoid circular imports
from . import associations

# Models dictionary to store all models
models = {}

# SQLAlchemy instance will be initialized in init_app
db = None

def init_models():
    """Initialize models after db is available.
    
    This function ensures all models are imported and registered with SQLAlchemy.
    It also initializes the models dictionary for easy access to model classes.
    """
    global models
    
    if models:  # Already initialized
        return models
    
    try:
        # Import all models to ensure they are registered with SQLAlchemy
        # Import order is important to avoid circular imports
        
        # First import the models that don't have relationships
        from .models import SecurityEventType
        
        # Then import models with relationships
        from .models import (
            User, Role, PasswordResetToken, EmailVerificationToken,
            SecurityEvent, UserSession, UserSecurityAnswer, SecurityQuestion
        )
        
        # Import security models
        from .security_models import (
            TokenBlacklist, PasswordHistory, FailedLoginAttempt,
            UserConsent, UserDevice, UserActivity, UserNotification, 
            UserPreference, Group, Permission
        )
        
        # Initialize models dictionary
        models = {
            'User': User,
            'Role': Role,
            'SecurityQuestion': SecurityQuestion,
            'UserSecurityAnswer': UserSecurityAnswer,
            'SecurityEvent': SecurityEvent,
            'UserSession': UserSession,
            'TokenBlacklist': TokenBlacklist,
            'PasswordHistory': PasswordHistory,
            'FailedLoginAttempt': FailedLoginAttempt,
            'UserConsent': UserConsent,
            'UserDevice': UserDevice,
            'UserActivity': UserActivity,
            'UserNotification': UserNotification,
            'UserPreference': UserPreference,
            'Group': Group,
            'Permission': Permission,
            'SecurityEventType': SecurityEventType,
            'PasswordResetToken': PasswordResetToken,
            'EmailVerificationToken': EmailVerificationToken
        }
        
        # Make sure all models are properly configured
        from sqlalchemy import inspect
        
        # Force SQLAlchemy to configure all mappers
        from sqlalchemy.orm import configure_mappers
        configure_mappers()
        
        # Initialize models dictionary
        models = {
            'User': User,
            'Role': Role,
            'PasswordResetToken': PasswordResetToken,
            'EmailVerificationToken': EmailVerificationToken,
            'SecurityEvent': SecurityEvent,
            'UserSession': UserSession,
            'SecurityEventType': SecurityEventType,
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
            'Group': Group,
            'Permission': Permission
        }
        
        # Configure all mappers to ensure relationships are set up
        from sqlalchemy.orm import configure_mappers
        configure_mappers()
        
        return models
        
    except Exception as e:
        if current_app:
            current_app.logger.error(f'Error initializing models: {str(e)}')
            if current_app.debug:
                import traceback
                current_app.logger.error(traceback.format_exc())
        else:
            print(f'Error initializing models: {str(e)}')
            import traceback
            traceback.print_exc()
            
        # Don't raise here to allow the app to start
        return {}
    finally:
        # Clean up any database sessions
        if db.session:
            db.session.remove()

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

        raise

def init_app(app, db_instance=None):
    """Initialize authentication extensions with app context."""
    global db, models
    
    try:
        # Use the provided db instance or create a new one
        if db_instance is not None:
            db = db_instance
        else:
            from flask_sqlalchemy import SQLAlchemy
            db = SQLAlchemy(app)
        
        # Initialize Flask-Login
        login_manager.login_view = 'login.login'
        login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'
        login_manager.login_message_category = 'info'
        login_manager.refresh_view = 'auth.reauthenticate'
        login_manager.needs_refresh_message = (
            'Por razones de seguridad, por favor vuelve a iniciar sesión para acceder a esta página.'
        )
        
        # Initialize extensions
        login_manager.init_app(app)
        mail.init_app(app)
        principal.init_app(app)
        
        # Import and register blueprints
        from . import forms
        from .views.login import login_bp as login_blueprint
        
        # Register the main auth blueprint
        app.register_blueprint(auth_bp)
        
        # Register login routes
        app.register_blueprint(login_blueprint, url_prefix='/auth')
        
        # Initialize models before admin
        with app.app_context():
            init_models()
        
        # Initialize admin
        from .admin import init_admin as init_auth_admin
        init_auth_admin(app, db)
        
        # Configure session timeout
        @app.before_request
        def before_request():
            if current_user.is_authenticated:
                current_user.last_seen = datetime.utcnow()
                db.session.commit()
                session.permanent = True
                app.permanent_session_lifetime = timedelta(minutes=SESSION_TIMEOUT_MINUTES)
                session.modified = True
        
        # Initialize models with the database
        with app.app_context():
            try:
                # Import models here to avoid circular imports
                from .security_models import create_association_tables, create_default_roles_and_permissions
                
                # Create association tables
                global user_roles, user_groups, user_permissions, group_permissions
                user_roles, user_groups, user_permissions, group_permissions = create_association_tables()
                
                # Initialize models and relationships
                init_models()
                
                # Create database tables if they don't exist
                db.create_all()
                
                # Create default roles and permissions if they don't exist
                create_default_roles_and_permissions()
                
                # Create default security questions if they don't exist
                from .models import SecurityQuestion
                default_questions = [
                    "¿Cuál es el nombre de tu primera mascota?",
                    "¿Cuál es el nombre de tu colegio de primaria?",
                    "¿Cuál es el nombre de tu ciudad de nacimiento?",
                    "¿Cuál es el nombre de tu mejor amigo de la infancia?",
                    "¿Cuál es tu comida favorita?"
                ]
                
                for question in default_questions:
                    if not SecurityQuestion.query.filter_by(question_text=question).first():
                        db.session.add(SecurityQuestion(question_text=question))
                
                db.session.commit()
                
            except Exception as e:
                app.logger.error(f"Error during database initialization: {str(e)}")
                if app.debug:
                    import traceback
                    app.logger.error(traceback.format_exc())
                raise
        
        return app
        
    except Exception as e:
        if 'app' in locals():
            app.logger.error(f"Error initializing auth: {str(e)}")
            if app.debug:
                import traceback
                app.logger.error(traceback.format_exc())
        else:
            print(f"Error initializing auth before app was available: {str(e)}")
            import traceback
            traceback.print_exc()
        raise
        
        # Register event handlers
        user_logged_in.connect(_on_user_logged_in, app)
        user_logged_out.connect(_on_user_logged_out, app)
        
        # Add template globals
        app.jinja_env.globals['current_user'] = current_user
        app.jinja_env.globals['SecurityEventType'] = SecurityEventType
        
        # Create default admin user if it doesn't exist
        with app.app_context():
            from .models import User, Role
            from werkzeug.security import generate_password_hash
            
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                admin_role = Role.query.filter_by(name='admin').first()
                if admin_role:
                    try:
                        admin = User(
                            username='admin',
                            email='admin@example.com',
                            role_id=admin_role.id,
                            password=generate_password_hash('admin123'),
                            is_active=True,
                            email_verified=True
                        )
                        db.session.add(admin)
                        db.session.commit()
                        app.logger.info('Created default admin user')
                    except Exception as e:
                        app.logger.error(f'Error creating admin user: {str(e)}')
                        if app.debug:
                            import traceback
                            app.logger.error(traceback.format_exc())
                        db.session.rollback()
        
        # Register blueprints
        app.register_blueprint(auth_bp, url_prefix='/auth')
        
        return app

# Import views after creating the blueprint to avoid circular imports
from . import views, forms

# Import the login blueprint
from .views.login import login_bp as login_blueprint

# Register the login blueprint with the auth blueprint
def init_app(app, db_instance=None):
    """Initialize the authentication module."""
    global db
    
    if db_instance is not None:
        db = db_instance
    
    # Initialize models
    init_models()
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(login_blueprint, url_prefix='/auth')
    
    # Initialize Flask-Login
    login_manager.init_app(app)
    
    # Initialize Flask-Mail
    mail.init_app(app)
    
    # Initialize Flask-Principal
    principal.init_app(app)
    
    # Register error handlers
    from . import errors
    app.register_error_handler(403, errors.forbidden)
    app.register_error_handler(404, errors.not_found)
    app.register_error_handler(500, errors.internal_server_error)