from functools import wraps
from datetime import datetime, timedelta
import functools

from flask import flash, redirect, url_for, request, session, current_app, jsonify, abort
from flask_login import current_user, login_required
from werkzeug.exceptions import TooManyRequests

from .models import SecurityEvent, SecurityEventType, db

# Rate limiting storage (in a production environment, use Redis or similar)
_rate_limit_store = {}


def anonymous_required(f):
    """
    Redirects to the index page if the user is already authenticated.
    Use this decorator for views that should only be accessible to anonymous users,
    like login and registration pages.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated:
            flash('You are already logged in.', 'info')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

def roles_required(*role_names):
    """
    Ensures the current user is logged in and has at least one of the specified roles.
    Redirects to login if not authenticated, or to an unauthorized page if role not matched.
    Usage: @roles_required('admin', 'staff')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login', next=request.path))
            
            # Check if user has a role assigned
            if not current_user.role:
                flash('You do not have a role assigned. Access denied.', 'danger')
                return redirect(url_for('auth.unauthorized')) # Or a specific error page

            # Check if the user's role is one of the allowed roles
            if current_user.role.name not in role_names:
                flash(f'You do not have the required permission ({", ".join(role_names)}) to access this page.', 'danger')
                return redirect(url_for('auth.unauthorized')) # Or a specific error page
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def password_required(f):
    """
    Decorator that requires the user to confirm their password before proceeding.
    The password confirmation is valid for a configurable amount of time.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Skip password check if not logged in (shouldn't happen with login_required)
        if not current_user.is_authenticated:
            return current_app.login_manager.unauthorized()
            
        # Check if password was recently confirmed
        last_confirm = session.get('password_confirmed_at')
        confirm_timeout = current_app.config.get('PASSWORD_CONFIRMATION_TIMEOUT', 1800)  # 30 minutes default
        
        if last_confirm and (datetime.utcnow() - datetime.fromisoformat(last_confirm)).total_seconds() < confirm_timeout:
            # Password was recently confirmed, allow access
            return f(*args, **kwargs)
            
        # Store the current URL to redirect back after password confirmation
        session['next_after_password_confirm'] = request.url
        
        # Redirect to password confirmation page
        flash('Por favor, confirma tu contraseña para continuar.', 'info')
        return redirect(url_for('auth.confirm_password'))
    return decorated_function


def mfa_required(f):
    """
    Decorator that requires multi-factor authentication for the route.
    If MFA is not set up, redirects to MFA setup page.
    """
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        # Skip MFA check if not required for the user's role
        if not current_user.mfa_required():
            return f(*args, **kwargs)
            
        # Check if MFA is enabled for the user
        if not current_user.mfa_enabled:
            session['next_after_mfa'] = request.url
            flash('Debes configurar la autenticación en dos pasos para acceder a esta página.', 'warning')
            return redirect(url_for('auth.mfa_setup.setup_mfa'))
            
        # Check if MFA was recently verified
        mfa_verified_at = session.get('mfa_verified_at')
        mfa_timeout = current_app.config.get('MFA_VERIFICATION_TIMEOUT', 3600)  # 1 hour default
        
        if mfa_verified_at and (datetime.utcnow() - datetime.fromisoformat(mfa_verified_at)).total_seconds() < mfa_timeout:
            # MFA was recently verified, allow access
            return f(*args, **kwargs)
            
        # Store the current URL to redirect back after MFA verification
        session['next_after_mfa'] = request.url
        
        # Redirect to MFA verification page
        flash('Se requiere verificación en dos pasos para acceder a esta página.', 'info')
        return redirect(url_for('auth.mfa.verify_mfa'))
    return decorated_function


def rate_limit(key_func, limit, per=60, scope_func=None, error_message=None):
    """
    Decorator to rate limit API endpoints.
    
    Args:
        key_func: Function that returns a string key to identify the requester
        limit: Maximum number of requests allowed in the time period
        per: Time period in seconds (default: 60)
        scope_func: Optional function to determine the rate limit scope
        error_message: Custom error message (can include {limit} and {time} placeholders)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Skip rate limiting in development
            if current_app.config.get('TESTING', False):
                return f(*args, **kwargs)
                
            # Generate rate limit key
            key = key_func()
            if not key:
                # If key is None, skip rate limiting
                return f(*args, **kwargs)
                
            # Add scope to the key if scope_func is provided
            if scope_func:
                scope = scope_func()
                if scope:
                    key = f"{key}:{scope}"
            
            # Get current timestamp
            now = datetime.utcnow()
            
            # Initialize rate limit data if not exists
            if key not in _rate_limit_store:
                _rate_limit_store[key] = {
                    'count': 0,
                    'reset_time': now + timedelta(seconds=per)
                }
            
            # Reset counter if the time window has passed
            if now > _rate_limit_store[key]['reset_time']:
                _rate_limit_store[key] = {
                    'count': 0,
                    'reset_time': now + timedelta(seconds=per)
                }
            
            # Increment request count
            _rate_limit_store[key]['count'] += 1
            
            # Check if rate limit is exceeded
            if _rate_limit_store[key]['count'] > limit:
                if error_message:
                    message = error_message.format(
                        limit=limit,
                        time=int((_rate_limit_store[key]['reset_time'] - now).total_seconds())
                    )
                else:
                    message = f'Demasiadas solicitudes. Límite de {limit} solicitudes por {per} segundos.'
                
                # Log the security event
                if current_user.is_authenticated:
                    security_event = SecurityEvent(
                        user_id=current_user.id,
                        event_type=SecurityEventType.RATE_LIMIT_EXCEEDED,
                        ip_address=request.remote_addr,
                        user_agent=request.headers.get('User-Agent'),
                        details={
                            'endpoint': request.endpoint,
                            'method': request.method,
                            'limit': limit,
                            'period': per
                        }
                    )
                    db.session.add(security_event)
                    try:
                        db.session.commit()
                    except:
                        db.session.rollback()
                
                # Return 429 Too Many Requests
                response = jsonify({
                    'error': 'rate_limit_exceeded',
                    'message': message,
                    'retry_after': int((_rate_limit_store[key]['reset_time'] - now).total_seconds())
                })
                response.status_code = 429
                response.headers['Retry-After'] = str(int((_rate_limit_store[key]['reset_time'] - now).total_seconds()))
                return response
            
            # Add rate limit headers to the response
            response = f(*args, **kwargs)
            response.headers['X-RateLimit-Limit'] = str(limit)
            response.headers['X-RateLimit-Remaining'] = str(limit - _rate_limit_store[key]['count'])
            response.headers['X-RateLimit-Reset'] = str(int(_rate_limit_store[key]['reset_time'].timestamp()))
            
            return response
        return decorated_function
    return decorator


def track_security_event(event_type, **details):
    """
    Decorator to track security-related events.
    
    Args:
        event_type: Type of security event (from SecurityEventType)
        **details: Additional details to include in the event
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Execute the wrapped function
            response = f(*args, **kwargs)
            
            # Only track if user is authenticated
            if current_user.is_authenticated:
                security_event = SecurityEvent(
                    user_id=current_user.id,
                    event_type=event_type,
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent'),
                    details=details
                )
                db.session.add(security_event)
                try:
                    db.session.commit()
                except:
                    db.session.rollback()
            
            return response
        return decorated_function
    return decorator


def check_account_status(f):
    """
    Decorator to check if the user's account is active and not locked.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return f(*args, **kwargs)
            
        # Check if account is locked
        if current_user.is_locked():
            flash('Tu cuenta está temporalmente bloqueada. Intenta de nuevo más tarde o restablece tu contraseña.', 'danger')
            return redirect(url_for('auth.login'))
            
        # Check if account is active
        if not current_user.is_active:
            flash('Tu cuenta ha sido desactivada. Por favor, contacta al administrador.', 'danger')
            return redirect(url_for('auth.login'))
            
        return f(*args, **kwargs)
    return decorated_function


def prevent_concurrent_logins(f):
    """
    Decorator to prevent multiple concurrent logins from the same user.
    Only allows one active session per user.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated and 'session_id' in session:
            # Get the current session ID
            current_session_id = session['session_id']
            
            # Get the most recent active session for the user
            active_session = UserSession.query.filter_by(
                user_id=current_user.id,
                is_active=True
            ).order_by(UserSession.last_activity.desc()).first()
            
            # If there's a more recent session, log the user out
            if active_session and active_session.session_id != current_session_id:
                # Log the security event
                security_event = SecurityEvent(
                    user_id=current_user.id,
                    event_type=SecurityEventType.CONCURRENT_SESSION,
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent'),
                    details={
                        'session_id': current_session_id,
                        'active_session_id': active_session.session_id
                    }
                )
                
                db.session.add(security_event)
                db.session.commit()
                
                # Log the user out
                logout_user()
                session.clear()
                
                flash('Has iniciado sesión desde otro dispositivo o navegador. Por seguridad, se ha cerrado esta sesión.', 'warning')
                return redirect(url_for('auth.login'))
        
        return f(*args, **kwargs)
    return decorated_function
