from flask import render_template, redirect, url_for, flash, session, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from database import db
from .models import User, Role
from .forms import RegistrationForm, LoginForm
from . import auth_bp  # Import the blueprint from __init__.py

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index')) # Or a dashboard route
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
        return redirect(url_for('login.login'))
    return render_template('register.html', title='Register', form=form)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index')) # Or a dashboard route
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
            return redirect(next_page or url_for('main.index'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('login.html', title='Login', form=form)

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
