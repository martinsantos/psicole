"""Enhanced login view with security features."""
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from flask_login import login_user, current_user
from werkzeug.security import check_password_hash

from ..models import User, FailedLoginAttempt, SecurityEvent, SecurityEventType, db
from ..security import is_ip_blocked, generate_token
from .decorators import anonymous_required
from .forms import LoginForm

# Create login blueprint
login_bp = Blueprint('login', __name__)

@login_bp.route('/login', methods=['GET', 'POST'])
@anonymous_required
def login():
    """Handle user login with enhanced security features."""
    # Check if IP is blocked
    ip_address = request.remote_addr
    if is_ip_blocked(ip_address):
        flash('Demasiados intentos fallidos. Por favor, intente más tarde.', 'danger')
        return redirect(url_for('auth.login.login'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        # Log login attempt
        login_attempt = FailedLoginAttempt(
            email=form.email.data,
            ip_address=ip_address,
            user_agent=request.headers.get('User-Agent')
        )
        
        if user is not None:
            login_attempt.user_id = user.id
            
            # Check if account is locked
            if user.account_locked_until and user.account_locked_until > datetime.utcnow():
                login_attempt.status = 'account_locked'
                db.session.add(login_attempt)
                db.session.commit()
                
                remaining_time = user.account_locked_until - datetime.utcnow()
                flash(
                    f'Cuenta bloqueada temporalmente. Intente nuevamente en {int(remaining_time.total_seconds() // 60)} minutos.',
                    'danger'
                )
                return redirect(url_for('auth.login.login'))
            
            # Check password
            if not check_password_hash(user.password_hash, form.password.data):
                login_attempt.status = 'invalid_password'
                user.login_attempts += 1
                
                # Lock account after too many failed attempts
                if user.login_attempts >= current_app.config.get('MAX_LOGIN_ATTEMPTS', 5):
                    user.account_locked_until = datetime.utcnow() + timedelta(
                        minutes=current_app.config.get('ACCOUNT_LOCKOUT_MINUTES', 30)
                    )
                    login_attempt.status = 'account_locked'
                    
                    # Log security event
                    security_event = SecurityEvent(
                        user_id=user.id,
                        event_type=SecurityEventType.ACCOUNT_LOCKED,
                        ip_address=ip_address,
                        user_agent=request.headers.get('User-Agent'),
                        details={'reason': 'too_many_failed_attempts'}
                    )
                    db.session.add(security_event)
                    
                    flash('Demasiados intentos fallidos. Su cuenta ha sido bloqueada temporalmente.', 'danger')
                else:
                    remaining_attempts = current_app.config.get('MAX_LOGIN_ATTEMPTS', 5) - user.login_attempts
                    flash(
                        f'Correo electrónico o contraseña inválidos. Le quedan {remaining_attempts} intentos.',
                        'danger'
                    )
                
                db.session.add(login_attempt)
                db.session.commit()
                return redirect(url_for('auth.login.login'))
            
            # Check if email is verified if required
            if not user.is_verified and current_app.config.get('REQUIRE_EMAIL_VERIFICATION', True):
                login_attempt.status = 'email_not_verified'
                db.session.add(login_attempt)
                db.session.commit()
                
                flash('Por favor verifica tu correo electrónico antes de iniciar sesión.', 'warning')
                return redirect(url_for('auth.unverified'))
            
            # Check if account is active
            if not user.is_active:
                login_attempt.status = 'account_inactive'
                db.session.add(login_attempt)
                db.session.commit()
                
                flash('Tu cuenta ha sido desactivada. Por favor contacta al administrador.', 'danger')
                return redirect(url_for('auth.login.login'))
            
            # Check if MFA is required
            mfa_required = False
            if hasattr(user, 'mfa_enabled') and user.mfa_enabled:
                mfa_required = True
            elif hasattr(user, 'roles'):
                mfa_required_roles = current_app.config.get('MFA_REQUIRED_ROLES', [])
                if any(role.name in mfa_required_roles for role in user.roles):
                    mfa_required = True
            
            if mfa_required:
                session['mfa_required'] = True
                session['mfa_user_id'] = user.id
                session['mfa_remember'] = form.remember_me.data
                session['next'] = request.args.get('next')
                
                # Generate and store MFA token
                mfa_token = generate_token()
                session['mfa_token'] = mfa_token
                
                # In a real app, you would send this token via email/SMS
                current_app.logger.info(f'MFA Token for {user.email}: {mfa_token}')
                
                login_attempt.status = 'mfa_required'
                db.session.add(login_attempt)
                db.session.commit()
                
                return redirect(url_for('auth.mfa.verify_mfa'))
            
            # If we get here, login is successful
            login_user(user, remember=form.remember_me.data)
            
            # Reset login attempts and update last login
            user.login_attempts = 0
            user.last_login = datetime.utcnow()
            
            # Log successful login
            login_attempt.status = 'success'
            
            # Log security event
            security_event = SecurityEvent(
                user_id=user.id,
                event_type=SecurityEventType.LOGIN_SUCCESS,
                ip_address=ip_address,
                user_agent=request.headers.get('User-Agent'),
                details={'method': 'password'}
            )
            
            db.session.add_all([login_attempt, security_event])
            db.session.commit()
            
            # Redirect to next page or dashboard
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('main.index')
                
            return redirect(next_page)
        else:
            # User not found
            login_attempt.status = 'user_not_found'
            db.session.add(login_attempt)
            db.session.commit()
            
            # Don't reveal that the user doesn't exist
            flash('Correo electrónico o contraseña inválidos', 'danger')
    
    return render_template('auth/login.html', title='Iniciar Sesión', form=form)

def is_ip_blocked(ip_address):
    """Check if an IP address is temporarily blocked due to too many failed attempts."""
    from datetime import datetime, timedelta
    
    # Count failed attempts in the last hour
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    failed_attempts = FailedLoginAttempt.query.filter(
        FailedLoginAttempt.ip_address == ip_address,
        FailedLoginAttempt.created_at > one_hour_ago,
        FailedLoginAttempt.status.in_(['invalid_password', 'user_not_found'])
    ).count()
    
    # Block if more than 10 failed attempts
    return failed_attempts >= current_app.config.get('MAX_LOGIN_ATTEMPTS_PER_IP', 10)
