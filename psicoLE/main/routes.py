from flask import render_template, redirect, url_for, current_app, flash
from flask_login import login_required, current_user
from . import main_bp
from auth.decorators import roles_required

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        try:
            if current_user.has_role('admin') or current_user.has_role('staff'):
                return redirect(url_for('admin_dashboard.dashboard'))
            elif current_user.has_role('professional'):
                return redirect(url_for('profesionales.dashboard'))
            else:
                flash('No tienes un panel de control asignado. Por favor, contacta al administrador.', 'warning')
                return render_template('main/index.html')
        except Exception as e:
            current_app.logger.error(f'Error in index route: {str(e)}')
            flash('Ocurrió un error al cargar el panel de control.', 'danger')
    
    # Default view for unauthenticated users
    return render_template('main/index.html')

@main_bp.route('/dashboard')
@login_required
def dashboard_redirect():
    """Redirect users to their respective dashboards based on their role"""
    try:
        if current_user.has_role('admin') or current_user.has_role('staff'):
            return redirect(url_for('admin_dashboard.dashboard'))
        elif current_user.has_role('professional'):
            return redirect(url_for('profesionales.dashboard'))
        else:
            flash('No tienes un panel de control asignado.', 'warning')
            return redirect(url_for('main.index'))
    except Exception as e:
        current_app.logger.error(f'Error in dashboard redirect: {str(e)}')
        flash('Ocurrió un error al intentar acceder al panel de control.', 'danger')
        return redirect(url_for('main.index'))
