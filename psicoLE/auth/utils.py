"""Utility functions for authentication module."""
from flask import render_template, current_app
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from werkzeug.exceptions import BadRequest
from datetime import datetime, timedelta
import logging
from user_agents import parse

def generate_token(email, salt=None, expires_in=3600):
    """Generate a secure token for email verification or password reset.
    
    Args:
        email (str): User's email address
        salt (str, optional): Salt for the token. Defaults to None.
        expires_in (int, optional): Token expiration time in seconds. Defaults to 3600 (1 hour).
    
    Returns:
        str: Generated token
    """
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(email, salt=salt or current_app.config['SECURITY_PASSWORD_SALT'])

def verify_token(token, salt=None, max_age=3600):
    """Verify a token and return the associated email if valid.
    
    Args:
        token (str): Token to verify
        salt (str, optional): Salt used to generate the token. Defaults to None.
        max_age (int, optional): Maximum age of the token in seconds. Defaults to 3600 (1 hour).
    
    Returns:
        str: Email address associated with the token if valid, None otherwise
    """
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = serializer.loads(
            token,
            salt=salt or current_app.config['SECURITY_PASSWORD_SALT'],
            max_age=max_age
        )
        return email
    except (SignatureExpired, BadSignature) as e:
        current_app.logger.warning(f'Invalid token: {str(e)}')
        return None

def send_email(subject, recipients, template, **context):
    """Send an email using the provided template and context.
    
    Args:
        subject (str): Email subject
        recipients (list): List of recipient email addresses
        template (str): Template name (without .html extension)
        **context: Additional context variables for the template
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    if not current_app.config.get('MAIL_SERVER'):
        current_app.logger.warning('Email sending is not configured. Check your MAIL_* settings.')
        return False
    
    try:
        # Add common template variables
        context.setdefault('app_name', current_app.config.get('APP_NAME', 'PsicoLE'))
        context.setdefault('year', datetime.utcnow().year)
        context.setdefault('config', current_app.config)
        
        # Render both HTML and plain text versions
        html_body = render_template(f'emails/{template}.html', **context)
        text_body = render_template(f'emails/{template}.txt', **context) \
            if template_exists(f'emails/{template}.txt') else None
        
        # Create and send the email
        msg = Message(
            subject=subject,
            sender=current_app.config['MAIL_DEFAULT_SENDER'],
            recipients=recipients,
            html=html_body,
            body=text_body
        )
        
        mail = current_app.extensions.get('mail')
        if not mail:
            from flask_mail import Mail
            mail = Mail(current_app)
        
        mail.send(msg)
        current_app.logger.info(f'Email sent to {recipients} with subject: {subject}')
        return True
        
    except Exception as e:
        current_app.logger.error(f'Failed to send email to {recipients}: {str(e)}', exc_info=True)
        return False

def send_verification_email(user):
    """Send an email verification link to the user.
    
    Args:
        user (User): User instance to send verification email to
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    token = generate_token(user.email, salt='email-verification-salt')
    verification_url = f"{current_app.config['FRONTEND_URL']}/verify-email?token={token}"
    
    return send_email(
        subject='Verifica tu correo electrónico',
        recipients=[user.email],
        template='auth/verify_email',
        user=user,
        verification_url=verification_url,
        token=token
    )

def send_password_reset_email(user):
    """Send a password reset link to the user.
    
    Args:
        user (User): User instance to send reset password email to
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    token = generate_token(user.email, salt='password-reset-salt', expires_in=3600)  # 1 hour expiration
    reset_url = f"{current_app.config['FRONTEND_URL']}/reset-password?token={token}"
    
    return send_email(
        subject='Restablece tu contraseña',
        recipients=[user.email],
        template='auth/reset_password',
        user=user,
        reset_url=reset_url,
        token=token
    )

def send_email_change_notification(user, old_email, new_email, request):
    """Send a notification email when a user changes their email address.
    
    Args:
        user (User): User instance
        old_email (str): Previous email address
        new_email (str): New email address
        request: The Flask request object to extract IP and user agent
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    user_agent = parse(request.headers.get('User-Agent', ''))
    
    return send_email(
        subject='Confirmación de cambio de correo electrónico',
        recipients=[old_email, new_email],
        template='auth/email_change_notification',
        user=user,
        old_email=old_email,
        new_email=new_email,
        timestamp=datetime.utcnow(),
        ip_address=request.remote_addr,
        user_agent={
            'platform': user_agent.get_os(),
            'browser': user_agent.get_browser(),
            'device': user_agent.get_device()
        }
    )

def send_password_changed_notification(user, request):
    """Send a notification email when a user changes their password.
    
    Args:
        user (User): User instance
        request: The Flask request object to extract IP and user agent
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    user_agent = parse(request.headers.get('User-Agent', ''))
    
    return send_email(
        subject='Tu contraseña ha sido cambiada',
        recipients=[user.email],
        template='auth/password_changed',
        user=user,
        timestamp=datetime.utcnow(),
        ip_address=request.remote_addr,
        user_agent={
            'platform': user_agent.get_os(),
            'browser': user_agent.get_browser(),
            'device': user_agent.get_device()
        }
    )

def template_exists(template_name):
    """Check if a template exists.
    
    Args:
        template_name (str): Name of the template to check
        
    Returns:
        bool: True if the template exists, False otherwise
    """
    return template_name in current_app.jinja_env.list_templates()

def is_safe_url(target):
    """Check if a URL is safe for redirection.
    
    Args:
        target (str): URL to check
        
    Returns:
        bool: True if the URL is safe, False otherwise
    """
    from urllib.parse import urlparse, urljoin
    from flask import request
    
    if not target:
        return False
        
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc
