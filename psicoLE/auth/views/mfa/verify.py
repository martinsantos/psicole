"""MFA verification views."""
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from flask_login import login_user, current_user
from werkzeug.security import check_password_hash

from ....models import User, SecurityEvent, SecurityEventType, db
from ....security import verify_mfa_code, generate_token
from ...decorators import login_required
from ...forms import MFAVerifyForm

# Create MFA verify blueprint
mfa_verify_bp = Blueprint('mfa_verify', __name__)

@mfa_verify_bp.route('/verify', methods=['GET', 'POST'])
def verify_mfa():
    """Verify MFA code."""
    # Check if MFA is required
    if not session.get('mfa_required'):
        return redirect(url_for('auth.login.login'))
    
    # Get user from session
    user_id = session.get('mfa_user_id')
    if not user_id:
        flash('Sesión inválida. Por favor inicie sesión nuevamente.', 'danger')
        return redirect(url_for('auth.login.login'))
    
    user = User.query.get(user_id)
    if not user:
        flash('Usuario no encontrado. Por favor inicie sesión nuevamente.', 'danger')
        return redirect(url_for('auth.login.login'))
    
    form = MFAVerifyForm()
    
    if form.validate_on_submit():
        # Verify MFA code
        if not verify_mfa_code(user, form.code.data):
            flash('Código de verificación inválido o expirado.', 'danger')
            
            # Log failed MFA attempt
            security_event = SecurityEvent(
                user_id=user.id,
                event_type=SecurityEventType.MFA_FAILED,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent'),
                details={'method': 'totp'}
            )
            db.session.add(security_event)
            db.session.commit()
            
            return redirect(url_for('auth.mfa.verify_mfa'))
        
        # MFA verification successful
        login_user(user, remember=session.get('mfa_remember', False))
        
        # Reset login attempts and update last login
        user.login_attempts = 0
        user.last_login = datetime.utcnow()
        
        # Log successful MFA verification
        security_event = SecurityEvent(
            user_id=user.id,
            event_type=SecurityEventType.MFA_SUCCESS,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent'),
            details={'method': 'totp'}
        )
        
        # Clear MFA session data
        next_page = session.pop('next', None)
        session.pop('mfa_required', None)
        session.pop('mfa_user_id', None)
        session.pop('mfa_remember', None)
        session.pop('mfa_token', None)
        
        db.session.add(security_event)
        db.session.commit()
        
        flash('Verificación exitosa. ¡Bienvenido!', 'success')
        
        # Redirect to next page or dashboard
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('main.index')
            
        return redirect(next_page)
    
    return render_template('auth/mfa/verify.html', title='Verificación en dos pasos', form=form)

@mfa_verify_bp.route('/resend', methods=['POST'])
def resend_mfa():
    """Resend MFA code."""
    if not session.get('mfa_required'):
        return redirect(url_for('auth.login.login'))
    
    user_id = session.get('mfa_user_id')
    if not user_id:
        flash('Sesión inválida. Por favor inicie sesión nuevamente.', 'danger')
        return redirect(url_for('auth.login.login'))
    
    user = User.query.get(user_id)
    if not user:
        flash('Usuario no encontrado. Por favor inicie sesión nuevamente.', 'danger')
        return redirect(url_for('auth.login.login'))
    
    # Generate new MFA token
    mfa_token = generate_token()
    session['mfa_token'] = mfa_token
    
    # In a real app, you would send this token via email/SMS
    current_app.logger.info(f'New MFA Token for {user.email}: {mfa_token}')
    
    # Log MFA resend
    security_event = SecurityEvent(
        user_id=user.id,
        event_type=SecurityEventType.MFA_CODE_RESENT,
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent'),
        details={'method': 'totp'}
    )
    
    db.session.add(security_event)
    db.session.commit()
    
    flash('Se ha enviado un nuevo código de verificación.', 'info')
    return redirect(url_for('auth.mfa.verify_mfa'))

@mfa_verify_bp.route('/recovery', methods=['GET', 'POST'])
def recovery():
    """MFA recovery using backup codes."""
    if not session.get('mfa_required'):
        return redirect(url_for('auth.login.login'))
    
    user_id = session.get('mfa_user_id')
    if not user_id:
        flash('Sesión inválida. Por favor inicie sesión nuevamente.', 'danger')
        return redirect(url_for('auth.login.login'))
    
    user = User.query.get(user_id)
    if not user:
        flash('Usuario no encontrado. Por favor inicie sesión nuevamente.', 'danger')
        return redirect(url_for('auth.login.login'))
    
    form = MFARecoveryForm()
    
    if form.validate_on_submit():
        # Verify recovery code
        recovery_code = form.recovery_code.data.strip()
        
        # In a real implementation, you would verify against stored hashed recovery codes
        # This is a simplified example
        if verify_recovery_code(user, recovery_code):
            # Login successful
            login_user(user, remember=session.get('mfa_remember', False))
            
            # Reset login attempts and update last login
            user.login_attempts = 0
            user.last_login = datetime.utcnow()
            
            # Log successful recovery
            security_event = SecurityEvent(
                user_id=user.id,
                event_type=SecurityEventType.MFA_RECOVERY_USED,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent'),
                details={'method': 'recovery_code'}
            )
            
            # Clear MFA session data
            next_page = session.pop('next', None)
            session.pop('mfa_required', None)
            session.pop('mfa_user_id', None)
            session.pop('mfa_remember', None)
            session.pop('mfa_token', None)
            
            db.session.add(security_event)
            db.session.commit()
            
            flash('¡Bienvenido! Has iniciado sesión con un código de recuperación.', 'success')
            
            # Redirect to next page or dashboard
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('main.index')
                
            return redirect(next_page)
        else:
            flash('Código de recuperación inválido o ya utilizado.', 'danger')
    
    return render_template('auth/mfa/recovery.html', title='Código de recuperación', form=form)

def verify_recovery_code(user, code):
    """Verify a recovery code.
    
    In a real implementation, this would check against stored hashed recovery codes
    and mark used codes as used.
    """
    # This is a simplified example
    # In a real app, you would:
    # 1. Hash the provided code
    # 2. Look for a matching hash in the database
    # 3. Check if the code is still valid (not used, not expired)
    # 4. Mark the code as used
    return False
