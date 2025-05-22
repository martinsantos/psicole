<<<<<<< HEAD
from datetime import datetime, timedelta
import secrets
import string
from flask import (
    Blueprint, render_template, redirect, url_for, flash, 
    session, request, current_app, abort
)
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from urllib.parse import urlparse as url_parse
from flask_mail import Message
from flask_babel import _

from flask import current_app
from . import db, mail, login_manager
from .models import User, Role, PasswordResetToken, EmailVerificationToken, Permission
from .forms import (
    RegistrationForm, LoginForm, ResetPasswordRequestForm, 
    ResetPasswordForm, ChangeEmailRequestForm, ChangePasswordForm
)
from .decorators import anonymous_required
from .utils import send_password_changed_notification

# The auth_bp is imported from __init__.py
from . import auth_bp

# Token expiration time (in hours)
RESET_TOKEN_EXPIRE_HOURS = 24
VERIFICATION_TOKEN_EXPIRE_HOURS = 48

def send_email(subject, sender, recipients, text_body, html_body):
    """Helper function to send emails."""
    try:
        msg = Message(
            subject=subject,
            sender=sender,
            recipients=recipients,
            body=text_body,
            html=html_body
        )
        mail.send(msg)
        current_app.logger.info(f'Email sent to {recipients[0]}')
        return True
    except Exception as e:
        current_app.logger.error(f'Error sending email to {recipients[0]}: {str(e)}')
        return False

def generate_token(length=32):
    """Generate a secure random token."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def send_password_reset_email(user):
    """Send password reset email with token."""
    if not user or not user.is_active:
        current_app.logger.warning(f'Attempt to send password reset to inactive or non-existent user')
        return False
        
    try:
        token = generate_token()
        expires_at = datetime.utcnow() + timedelta(hours=RESET_TOKEN_EXPIRE_HOURS)
        
        # Invalidate any existing tokens
        PasswordResetToken.query.filter_by(user_id=user.id).delete()
        
        # Create new token
        reset_token = PasswordResetToken(
            token=token, 
            user_id=user.id, 
            expires_at=expires_at
        )
        db.session.add(reset_token)
        db.session.commit()
        
        # Generate secure reset URL with HTTPS
        reset_url = url_for('auth.reset_password', token=token, _external=True, _scheme='https')
        
        # Add security headers to the URL
        reset_url += '&_token=' + generate_token(16)  # Add CSRF-like token
        
        # Render email templates
        context = {
            'user': user,
            'reset_link': reset_url,
            'expire_hours': RESET_TOKEN_EXPIRE_HOURS,
            'now': datetime.utcnow(),
            'ip_address': request.remote_addr,
            'user_agent': request.user_agent.string if request.user_agent else 'Unknown'
        }
        
        subject = 'Restablecer tu contraseña - PsicoLE'
        text_body = render_template('emails/auth/reset_password.txt', **context)
        html_body = render_template('emails/auth/reset_password.html', **context)
        
        # Log the reset attempt
        current_app.logger.info(f'Password reset requested for user {user.id} from IP {request.remote_addr}')
        
        return send_email(
            subject=subject,
            sender=current_app.config['MAIL_DEFAULT_SENDER'],
            recipients=[user.email],
            text_body=text_body,
            html_body=html_body
        )
    except Exception as e:
        current_app.logger.error(f'Error sending password reset email: {str(e)}')
        db.session.rollback()
        return False

def send_verification_email(user, email=None):
    """Send email verification email with token."""
    token = generate_token()
    expires_at = datetime.utcnow() + timedelta(hours=VERIFICATION_TOKEN_EXPIRE_HOURS)
    
    # Create or update verification token
    verification_token = EmailVerificationToken.query.filter_by(user_id=user.id).first()
    if verification_token:
        verification_token.token = token
        verification_token.expires_at = expires_at
    else:
        verification_token = EmailVerificationToken(
            token=token, 
            user_id=user.id, 
            expires_at=expires_at,
            new_email=email  # Store the new email if changing email
        )
        db.session.add(verification_token)
    
    db.session.commit()
    
    # Determine email subject and template based on whether this is a new email verification or email change
    if email:
        verification_url = url_for('auth.verify_email', token=token, _external=True, _scheme='https')
        subject = 'Verifica tu nueva dirección de correo - PsicoLE'
        template = 'auth/email/change_email.html'
        txt_template = 'auth/email/change_email.txt'
        email_to_verify = email
    else:
        verification_url = url_for('auth.verify_email', token=token, _external=True, _scheme='https')
        subject = 'Verifica tu correo electrónico - PsicoLE'
        template = 'auth/email/verify_email.html'
        txt_template = 'auth/email/verify_email.txt'
        email_to_verify = user.email
    
    # Render email templates
    text_body = render_template(
        txt_template,
        user=user,
        verification_link=verification_url,
        expire_hours=VERIFICATION_TOKEN_EXPIRE_HOURS,
        now=datetime.utcnow()
    )
    
    html_body = render_template(
        template,
        user=user,
        verification_link=verification_url,
        expire_hours=VERIFICATION_TOKEN_EXPIRE_HOURS,
        now=datetime.utcnow()
    )
    
    return send_email(
        subject=subject,
        sender=current_app.config['MAIL_DEFAULT_SENDER'],
        recipients=[email_to_verify],
        text_body=text_body,
        html_body=html_body
    )

def send_email_changed_notification(user, old_email, new_email):
    """Send notification email when email is changed successfully."""
    subject = 'Notificación de cambio de correo electrónico - PsicoLE'
    
    # Render email templates
    text_body = render_template(
        'auth/email/email_changed_notification.txt',
        user=user,
        old_email=old_email,
        new_email=new_email,
        change_date=datetime.utcnow(),
        timezone='UTC',
        now=datetime.utcnow()
    )
    
    html_body = render_template(
        'auth/email/email_changed_notification.html',
        user=user,
        old_email=old_email,
        new_email=new_email,
        change_date=datetime.utcnow(),
        timezone='UTC',
        now=datetime.utcnow()
    )
    
    return send_email(
        subject=subject,
        sender=current_app.config['MAIL_DEFAULT_SENDER'],
        recipients=[old_email, new_email],
        text_body=text_body,
        html_body=html_body
    )

@auth_bp.route('/register', methods=['GET', 'POST'])
@anonymous_required
def register():
    """Handle user registration with email verification."""
    form = RegistrationForm()
    if form.validate_on_submit():
        db = current_app.extensions['sqlalchemy'].db
        
        try:
            # Check if username or email already exists
            if User.query.filter_by(username=form.username.data).first():
                flash('El nombre de usuario ya está en uso. Por favor elija otro.', 'danger')
                return redirect(url_for('auth.register'))
                
            if User.query.filter_by(email=form.email.data).first():
                flash('El correo electrónico ya está registrado. Por favor utilice otro.', 'danger')
                return redirect(url_for('auth.register'))
            
            hashed_password = generate_password_hash(form.password.data)
            
            # Assign 'professional' role by default
            professional_role = Role.query.filter_by(name='professional').first()
            if not professional_role:
                # If the role doesn't exist, create it
                professional_role = Role(name='professional', description='Professional user')
                db.session.add(professional_role)
                db.session.commit()

            # Create user with is_verified=False initially
            new_user = User(
                username=form.username.data, 
                email=form.email.data, 
                password_hash=hashed_password,
                role_id=professional_role.id,
                is_active=True,
                is_verified=False
            )
            
            db.session.add(new_user)
            db.session.commit()
            
            # Send verification email
            if send_verification_email(new_user):
                flash(
                    '¡Registro exitoso! Por favor revisa tu correo electrónico para verificar tu cuenta. '
                    'El enlace de verificación es válido por 48 horas.',
                    'info'
                )
            else:
                flash(
                    'Se ha registrado correctamente, pero no se pudo enviar el correo de verificación. '
                    'Por favor, contacta al soporte técnico.',
                    'warning'
                )
            
            # Log the user in
            login_user(new_user)
            
            # Redirect to the unverified page
            return redirect(url_for('auth.unverified'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error during registration: {str(e)}')
            flash('Ocurrió un error durante el registro. Por favor, inténtalo de nuevo más tarde.', 'danger')
    
    return render_template('auth/register.html', title='Registro', form=form)

@auth_bp.route('/unverified')
@login_required
def unverified():
    """Show unverified account notice."""
    if current_user.is_verified:
        return redirect(url_for('main.index'))

@auth_bp.route('/login', methods=['GET', 'POST'])
@anonymous_required
def login():
    """Handle user login with security features."""
    
    # Check if IP is blocked
    ip_address = request.remote_addr
    if is_ip_blocked(ip_address):
        flash('Demasiados intentos fallidos. Por favor, intente más tarde.', 'danger')
        return redirect(url_for('auth.login'))
    
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
                flash(f'Cuenta bloqueada temporalmente. Intente nuevamente en {int(remaining_time.total_seconds() // 60)} minutos.', 'danger')
                return redirect(url_for('auth.login'))
            
            # Check password
            if not user.check_password(form.password.data):
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
                    flash(f'Correo electrónico o contraseña inválidos. Le quedan {remaining_attempts} intentos.', 'danger')
                
                db.session.add(login_attempt)
                db.session.commit()
                return redirect(url_for('auth.login'))
            
            # Check if email is verified if required
            if not user.is_verified and current_app.config.get('REQUIRE_EMAIL_VERIFICATION', True):
                login_attempt.status = 'email_not_verified'
                db.session.add(login_attempt)
                db.session.commit()
                
                flash('Por favor verifica tu correo electrónico antes de iniciar sesión.', 'warning')
                        'Tu correo electrónico aún no ha sido verificado. '
                        'No se pudo enviar un nuevo enlace de verificación. Intenta más tarde o contacta al soporte.',
                        'danger'
                    )
                return redirect(url_for('auth.unverified'))
            
            # Log the user in
            login_user(user, remember=form.remember_me.data)
            
            # Update last login time
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            # Log successful login
            current_app.logger.info(f'User {user.username} logged in successfully')
            
            # Redirect to next page if it exists and is safe
            next_page = request.args.get('next')
            if next_page and url_parse(next_page).netloc == '':
                return redirect(next_page)
                
            flash(f'¡Bienvenido de nuevo, {user.username}!', 'success')
            return redirect(url_for('main.index'))
            
        # Log failed login attempt
        current_app.logger.warning(f'Failed login attempt for username/email: {form.username.data}')
        flash('Usuario o contraseña incorrectos. Intente nuevamente.', 'danger')
    
    return render_template('auth/login.html', title='Iniciar Sesión', form=form)
=======
from flask import Blueprint, render_template, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from psicoLE.database import db
from .models import User, Role
from .forms import RegistrationForm, LoginForm

auth_bp = Blueprint('auth', __name__, template_folder='templates/auth')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('hello_world')) # Or a dashboard route
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        
        # Assign 'professional' role by default
        professional_role = Role.query.filter_by(name='professional').first()
        if not professional_role:
            # This case should ideally not happen if roles are pre-populated
            flash('Default role "professional" not found. Please contact admin.', 'danger')
            return redirect(url_for('auth.register'))

        new_user = User(username=form.username.data, 
                        email=form.email.data, 
                        password_hash=hashed_password,
                        role_id=professional_role.id)
        db.session.add(new_user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('register.html', title='Register', form=form)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('hello_world')) # Or a dashboard route
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=form.remember.data)
            # Store additional info in session if needed, though current_user handles most
            session['username'] = user.username
            if user.role:
                session['role'] = user.role.name
            else:
                session['role'] = 'N/A' # Should not happen if role is assigned at registration
            
            flash('Login successful!', 'success')
            # Redirect to a dashboard or home page
            # For now, let's redirect to the main page.
            # A better target would be a user-specific dashboard.
            next_page = request.args.get('next')
            return redirect(next_page or url_for('hello_world'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('login.html', title='Login', form=form)
>>>>>>> 1eca9da5ea75796c688eecc7b35bab563ae145b2

@auth_bp.route('/logout')
@login_required
def logout():
<<<<<<< HEAD
    """Handle user logout with session cleanup."""
    try:
        # Get username before logging out
        username = current_user.username
        
        # Log the user out and clear the session
        logout_user()
        session.clear()  # Clear all session data
        
        # Clear remember me cookie if it exists
        response = redirect(url_for('auth.login'))
        response.delete_cookie('remember_token', path='/', domain=None)
        
        # Log the successful logout
        current_app.logger.info(f'User {username} logged out successfully')
        flash('Has cerrado sesión correctamente. ¡Hasta pronto!', 'info')
        
        return response
        
    except Exception as e:
        current_app.logger.error(f'Error during logout: {str(e)}')
        flash('Ocurrió un error al cerrar la sesión. Por favor, inténtalo de nuevo.', 'danger')
        return redirect(url_for('main.index'))

@auth_bp.route('/reset_password_request', methods=['GET', 'POST'])
@anonymous_required
def reset_password_request():
    """Handle password reset requests with rate limiting and security measures."""
    # Check rate limiting
    reset_attempts = session.get('reset_attempts', 0)
    last_attempt = session.get('last_reset_attempt')
    
    # Apply rate limiting
    if last_attempt and (datetime.utcnow() - last_attempt).total_seconds() < 60:  # 1 minute cooldown
        flash('Por favor espera antes de solicitar otro restablecimiento de contraseña.', 'warning')
        return redirect(url_for('auth.login'))
    
    form = ResetPasswordRequestForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        # Always return success message to prevent email enumeration
        if user and user.is_active:
            if send_password_reset_email(user):
                current_app.logger.info(f'Password reset email sent to {user.email} from IP {request.remote_addr}')
            else:
                current_app.logger.error(f'Failed to send password reset email to {user.email}')
        else:
            # Log failed attempt but don't reveal if email exists
            current_app.logger.warning(f'Password reset attempt for non-existent email: {form.email.data} from IP {request.remote_addr}')
        
        # Update rate limiting
        reset_attempts += 1
        session['reset_attempts'] = reset_attempts
        session['last_reset_attempt'] = datetime.utcnow()
        
        # Always show success message to prevent email enumeration
        flash('Si existe una cuenta con ese correo electrónico, se ha enviado un correo con instrucciones para restablecer tu contraseña. Por favor revisa tu bandeja de entrada y la carpeta de spam.', 'info')
        return redirect(url_for('auth.login'))
    
    return render_template(
        'auth/reset_password_request.html',
        title='Restablecer Contraseña',
        form=form,
        recaptcha_sitekey=current_app.config.get('RECAPTCHA_SITE_KEY', '')
    )

@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
@anonymous_required
def reset_password(token):
    """Handle password reset with token and additional security checks."""
    # Check if token is provided and has valid format
    if not token or len(token) < 32:  # Basic validation for token length
        flash('El enlace de restablecimiento es inválido.', 'danger')
        return redirect(url_for('auth.reset_password_request'))
    
    # Check rate limiting
    failed_attempts = session.get('reset_failed_attempts', 0)
    last_attempt = session.get('last_reset_attempt')
    
    # Apply rate limiting (1 hour cooldown after 5 attempts)
    if failed_attempts >= 5 and last_attempt and (datetime.utcnow() - last_attempt).total_seconds() < 3600:
        flash('Demasiados intentos fallidos. Por favor inténtalo de nuevo más tarde.', 'danger')
        return redirect(url_for('auth.reset_password_request'))
    
    # Verify token
    reset_token = PasswordResetToken.query.filter_by(token=token).first()
    
    # Log the attempt
    current_app.logger.info(
        f'Password reset attempt with token from IP {request.remote_addr} - '
        f'Token exists: {reset_token is not None}, Expired: {reset_token.is_expired() if reset_token else "N/A"}'
    )
    
    if not reset_token or reset_token.is_expired():
        # Update failed attempts counter
        session['reset_failed_attempts'] = failed_attempts + 1
        session['last_reset_attempt'] = datetime.utcnow()
        
        flash('El enlace de restablecimiento es inválido o ha expirado. Por favor solicita uno nuevo.', 'danger')
        return redirect(url_for('auth.reset_password_request'))
    
    user = User.query.get(reset_token.user_id)
    if not user or not user.is_active:
        flash('Usuario no encontrado o cuenta inactiva.', 'danger')
        return redirect(url_for('auth.reset_password_request'))
    
    form = ResetPasswordForm()
    if form.validate_on_submit():
        # Check if the new password is different from the current one
        if user.check_password(form.password.data):
            flash('La nueva contraseña no puede ser igual a la actual.', 'danger')
            return render_template('auth/reset_password.html', form=form, token=token)
        
        try:
            # Update password
            user.set_password(form.password.data)
            
            # Invalidate all sessions except current one
            user.last_password_change = datetime.utcnow()
            
            # Delete all reset tokens for this user
            PasswordResetToken.query.filter_by(user_id=user.id).delete()
            
            # Log the password change
            current_app.logger.info(f'Password reset successful for user {user.id} from IP {request.remote_addr}')
            
            # Send confirmation email
            send_password_changed_notification(user, request)
            
            db.session.commit()
            
            # Clear rate limiting
            if 'reset_failed_attempts' in session:
                session.pop('reset_failed_attempts')
            if 'last_reset_attempt' in session:
                session.pop('last_reset_attempt')
            
            flash('Tu contraseña ha sido actualizada correctamente. Por favor inicia sesión.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error resetting password: {str(e)}')
            flash('Ocurrió un error al actualizar tu contraseña. Por favor inténtalo de nuevo.', 'danger')
        # Update password
        user.set_password(form.password.data)
        
        # Delete the used token
        db.session.delete(reset_token)
        db.session.commit()
        
        flash('Tu contraseña ha sido restablecida exitosamente. Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html', title='Restablecer Contraseña', form=form, token=token)

@auth_bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Allow users to change their password when logged in."""
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.check_password(form.current_password.data):
            current_user.set_password(form.new_password.data)
            db.session.commit()
            
            # Send confirmation email
            try:
                subject = 'Contraseña actualizada - PsicoLE'
                text_body = render_template('auth/email/password_changed.txt', user=current_user)
                html_body = render_template('auth/email/password_changed.html', user=current_user)
                
                send_email(
                    subject=subject,
                    sender=current_app.config['MAIL_DEFAULT_SENDER'],
                    recipients=[current_user.email],
                    text_body=text_body,
                    html_body=html_body
                )
            except Exception as e:
                current_app.logger.error(f'Error sending password change email: {str(e)}')
            
            flash('Tu contraseña ha sido actualizada exitosamente.', 'success')
            return redirect(url_for('main.profile'))
        else:
            flash('La contraseña actual es incorrecta.', 'danger')
    return render_template('auth/change_password.html', title='Cambiar Contraseña', form=form)

@auth_bp.route('/verify_email/<token>')
@anonymous_required
def verify_email(token):
    """Verify user's email with token and additional security checks."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    # Basic token validation
    if not token or len(token) < 32:
        flash('El enlace de verificación no es válido.', 'danger')
        return redirect(url_for('auth.login'))
    
    # Check rate limiting
    verify_attempts = session.get('verify_attempts', 0)
    last_attempt = session.get('last_verify_attempt')
    
    if verify_attempts >= 5 and last_attempt and (datetime.utcnow() - last_attempt).total_seconds() < 3600:
        flash('Demasiados intentos fallidos. Por favor contacta al soporte.', 'danger')
        return redirect(url_for('auth.login'))
    
    # Verify token
    verification_token = EmailVerificationToken.query.filter_by(token=token).first()
    
    # Log the attempt
    current_app.logger.info(
        f'Email verification attempt with token from IP {request.remote_addr} - '
        f'Token exists: {verification_token is not None}, Expired: {verification_token.is_expired() if verification_token else "N/A"}'
    )
    
    if not verification_token or verification_token.is_expired():
        # Update failed attempts counter
        session['verify_attempts'] = verify_attempts + 1
        session['last_verify_attempt'] = datetime.utcnow()
        
        flash('El enlace de verificación no es válido o ha expirado. Por favor solicita uno nuevo.', 'danger')
        return redirect(url_for('auth.login'))
    
    user = User.query.get(verification_token.user_id)
    if not user or not user.is_active:
        flash('Usuario no encontrado o cuenta inactiva.', 'danger')
        return redirect(url_for('auth.login'))
    
    try:
        # Check if this is an email change verification
        if verification_token.new_email:
            old_email = user.email
            new_email = verification_token.new_email
            
            # Check if the new email is already in use
            if User.query.filter(User.email == new_email, User.id != user.id).first():
                flash('La dirección de correo electrónico ya está en uso por otra cuenta.', 'danger')
                return redirect(url_for('auth.login'))
            
            user.email = new_email
            user.is_verified = True
            
            # Send notification to both old and new email
            send_email_changed_notification(user, old_email, new_email)
            
            flash('Tu dirección de correo electrónico ha sido actualizada correctamente. Por favor inicia sesión.', 'success')
        else:
            # Standard email verification
            if user.is_verified:
                flash('Tu correo electrónico ya ha sido verificado anteriormente.', 'info')
                return redirect(url_for('main.index'))
                
            user.is_verified = True
            user.verified_on = datetime.utcnow()
            flash('¡Correo electrónico verificado con éxito! Ahora puedes iniciar sesión.', 'success')
        
        # Delete the verification token
        db.session.delete(verification_token)
        db.session.commit()
        
        # Clear rate limiting on success
        if 'verify_attempts' in session:
            session.pop('verify_attempts')
        if 'last_verify_attempt' in session:
            session.pop('last_verify_attempt')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error during email verification: {str(e)}')
        flash('Ocurrió un error al verificar tu correo electrónico. Por favor inténtalo de nuevo.', 'danger')
    
    return redirect(url_for('auth.login'))

@auth_bp.route('/resend_verification')
@login_required
def resend_verification():
    """Resend email verification."""
    if current_user.is_verified:
        flash('Tu correo electrónico ya ha sido verificado.', 'info')
        return redirect(url_for('main.index'))
    
    if send_verification_email(current_user):
        flash('Se ha enviado un nuevo correo de verificación a tu dirección de correo electrónico.', 'info')
    else:
        flash('No se pudo enviar el correo de verificación. Por favor, inténtalo de nuevo más tarde.', 'danger')
    
    return redirect(url_for('main.profile'))

@auth_bp.route('/change_email_request', methods=['GET', 'POST'])
@login_required
def change_email_request():
    """Handle email change requests."""
    form = ChangeEmailRequestForm()
    
    if form.validate_on_submit():
        # Check if email is already in use
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user and existing_user.id != current_user.id:
            flash('Este correo electrónico ya está en uso. Por favor, utiliza otro.', 'danger')
            return redirect(url_for('auth.change_email_request'))
        
        # Send verification email to the new address
        if send_verification_email(current_user, form.email.data):
            flash('Se ha enviado un correo de verificación a tu nueva dirección de correo electrónico. Por favor, sigue las instrucciones para completar el cambio.', 'info')
            return redirect(url_for('main.profile'))
        else:
            flash('No se pudo enviar el correo de verificación. Por favor, inténtalo de nuevo más tarde.', 'danger')
    
    return render_template('auth/change_email_request.html', title='Cambiar Correo Electrónico', form=form)

@auth_bp.route('/unauthorized')
def unauthorized():
    """Handle unauthorized access attempts"""
    if current_user.is_authenticated:
        # Log unauthorized access attempt for authenticated users
        current_app.logger.warning(
            f'Unauthorized access attempt by user {current_user.username} to {request.referrer or "unknown page"}'
        )
        flash('No tienes permiso para acceder a esta página.', 'warning')
    else:
        # For unauthenticated users, redirect to login with next parameter
        flash('Por favor inicia sesión para acceder a esta página.', 'info')
        return redirect(url_for('auth.login', next=request.referrer or None))
    
    # If user is authenticated but not authorized, show 403 page
    return render_template('auth/403.html', title='Acceso no autorizado'), 403
=======
    logout_user()
    # Clear custom session variables if any
    session.pop('username', None) # These are also managed by flask_login.logout_user() if set by flask_login
    session.pop('role', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/unauthorized')
def unauthorized():
    # Flashed messages are handled by base.html
    return render_template('unauthorized.html', title='Unauthorized')
>>>>>>> 1eca9da5ea75796c688eecc7b35bab563ae145b2
