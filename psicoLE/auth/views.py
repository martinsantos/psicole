from flask import Blueprint, render_template, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
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
        return redirect(url_for('hello_world'))
        
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            session['username'] = user.username
            session['role'] = user.role.name if user.role else 'N/A'
            
            flash('¡Inicio de sesión exitoso!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('hello_world'))
        else:
            flash('Usuario o contraseña incorrectos', 'danger')
    return render_template('auth/login.html', title='Iniciar Sesión', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
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
