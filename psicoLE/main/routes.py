from flask import render_template, redirect, url_for
from flask_login import login_required, current_user
from . import main_bp

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role and current_user.role.name == 'admin':
            return redirect(url_for('admin_dashboard.index'))
        elif current_user.role and current_user.role.name == 'professional':
            return redirect(url_for('profesionales.dashboard'))
    return render_template('main/index.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    # This will be handled by the respective role-based dashboards
    return redirect(url_for('main.index'))
