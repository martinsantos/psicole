"""MFA setup and management views."""
import base64
import pyotp
import qrcode
import qrcode.image.svg
from io import BytesIO
from flask import (
    Blueprint, render_template, redirect, url_for, 
    flash, current_app, session, request, jsonify
)
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash

from ....models import db, User, SecurityEvent, SecurityEventType
from ....security import generate_secure_token, is_mfa_required
from ...decorators import password_required
from ...forms import MFASetupForm, MFARecoveryForm

# Create MFA setup blueprint
mfa_setup_bp = Blueprint('mfa_setup', __name__)

@mfa_setup_bp.route('/setup', methods=['GET', 'POST'])
@login_required
@password_required
@password_required
@password_required
def setup_mfa():
    """Set up multi-factor authentication for the current user."""
    # If MFA is already set up, redirect to account settings
    if current_user.mfa_enabled:
        flash('La autenticación en dos pasos ya está configurada.', 'info')
        return redirect(url_for('account.settings'))
    
    form = MFASetupForm()
    
    # Generate a new secret if not already in session
    if 'mfa_secret' not in session:
        session['mfa_secret'] = pyotp.random_base32()
    
    # Generate provisioning URI for QR code
    totp = pyotp.TOTP(session['mfa_secret'])
    provisioning_uri = totp.provisioning_uri(
        name=current_user.email,
        issuer_name=current_app.config.get('APP_NAME', 'Psicole')
    )
    
    # Generate QR code as SVG
    img = qrcode.make(provisioning_uri, image_factory=qrcode.image.svg.SvgImage)
    stream = BytesIO()
    img.save(stream)
    qr_code_svg = stream.getvalue().decode('utf-8')
    
    if form.validate_on_submit():
        # Verify the code
        totp = pyotp.TOTP(session['mfa_secret'])
        if totp.verify(form.code.data, valid_window=1):
            # Save the MFA secret to the user
            current_user.mfa_secret = session['mfa_secret']
            current_user.mfa_enabled = True
            
            # Generate recovery codes
            recovery_codes = [generate_secure_token(10) for _ in range(10)]
            current_user.mfa_recovery_codes = [
                generate_password_hash(code) for code in recovery_codes
            ]
            
            # Log the security event
            security_event = SecurityEvent(
                user_id=current_user.id,
                event_type=SecurityEventType.MFA_ENABLED,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )
            
            try:
                db.session.add(security_event)
                db.session.commit()
                
                # Clear the session
                session.pop('mfa_secret', None)
                
                # Show recovery codes to the user (only once!)
                session['recovery_codes'] = recovery_codes
                
                flash('Autenticación en dos pasos configurada correctamente.', 'success')
                return redirect(url_for('auth.mfa_setup.show_recovery_codes'))
                
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f'Error enabling MFA: {str(e)}')
                flash('Error al guardar la configuración. Por favor, inténtalo de nuevo.', 'danger')
        else:
            flash('Código de verificación inválido. Por favor, inténtalo de nuevo.', 'danger')
    
    return render_template(
        'auth/mfa/setup.html',
        title='Configurar autenticación en dos pasos',
        form=form,
        qr_code_svg=qr_code_svg,
        secret=session['mfa_secret']
    )

@mfa_setup_bp.route('/recovery-codes', methods=['GET'])
@login_required
def show_recovery_codes():
    """Display recovery codes to the user (one-time view)."""
    if 'recovery_codes' not in session:
        if not current_user.mfa_enabled:
            flash('Primero debes configurar la autenticación en dos pasos.', 'warning')
            return redirect(url_for('auth.mfa_setup.setup_mfa'))
        return redirect(url_for('account.settings'))
    
    recovery_codes = session.pop('recovery_codes')
    
    return render_template(
        'auth/mfa/recovery_codes.html',
        title='Códigos de recuperación',
        recovery_codes=recovery_codes
    )

@mfa_setup_bp.route('/disable', methods=['POST'])
@login_required
@password_required
def disable_mfa():
    """Disable multi-factor authentication for the current user."""
    if not current_user.mfa_enabled:
        flash('La autenticación en dos pasos no está habilitada.', 'warning')
        return redirect(url_for('account.settings'))
    
    # Log the security event
    security_event = SecurityEvent(
        user_id=current_user.id,
        event_type=SecurityEventType.MFA_DISABLED,
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )
    
    # Disable MFA
    current_user.mfa_enabled = False
    current_user.mfa_secret = None
    current_user.mfa_recovery_codes = None
    
    try:
        db.session.add(security_event)
        db.session.commit()
        flash('Autenticación en dos pasos deshabilitada correctamente.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error disabling MFA: {str(e)}')
        flash('Error al deshabilitar la autenticación en dos pasos. Por favor, inténtalo de nuevo.', 'danger')
    
    return redirect(url_for('account.settings'))

@mfa_setup_bp.route('/recovery/setup', methods=['GET', 'POST'])
@login_required
def setup_recovery_codes():
    """Generate new recovery codes for the current user."""
    if not current_user.mfa_enabled:
        flash('Primero debes configurar la autenticación en dos pasos.', 'warning')
        return redirect(url_for('auth.mfa_setup.setup_mfa'))
    
    form = MFARecoveryForm()
    
    if form.validate_on_submit():
        # Verify the code
        totp = pyotp.TOTP(current_user.mfa_secret)
        if totp.verify(form.code.data, valid_window=1):
            # Generate new recovery codes
            recovery_codes = [generate_secure_token(10) for _ in range(10)]
            current_user.mfa_recovery_codes = [
                generate_password_hash(code) for code in recovery_codes
            ]
            
            # Log the security event
            security_event = SecurityEvent(
                user_id=current_user.id,
                event_type=SecurityEventType.MFA_RECOVERY_CODES_REGENERATED,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )
            
            try:
                db.session.add(security_event)
                db.session.commit()
                
                # Show recovery codes to the user (only once!)
                session['recovery_codes'] = recovery_codes
                
                flash('Nuevos códigos de recuperación generados.', 'success')
                return redirect(url_for('auth.mfa_setup.show_recovery_codes'))
                
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f'Error generating recovery codes: {str(e)}')
                flash('Error al generar los códigos de recuperación. Por favor, inténtalo de nuevo.', 'danger')
        else:
            flash('Código de verificación inválido. Por favor, inténtalo de nuevo.', 'danger')
    
    return render_template(
        'auth/mfa/verify_code.html',
        title='Generar códigos de recuperación',
        form=form,
        action=url_for('auth.mfa_setup.setup_recovery_codes')
    )
