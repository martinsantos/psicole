from functools import wraps
from flask import flash, redirect, url_for, request
from flask_login import current_user, login_required


def anonymous_required(f):
    """
    Redirects user to the home page if they are already logged in.
    Use this decorator for views that should only be accessible to anonymous users.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated:
            flash('You are already logged in.', 'info')
            return redirect(url_for('main.index'))  # Adjust the endpoint as needed
        return f(*args, **kwargs)
    return decorated_function

def roles_required(*role_names):
    """
    Ensures the current user is logged in and has at least one of the specified roles.
    Redirects to login if not authenticated, or to an unauthorized page if role not matched.
    
    Args:
        *role_names: One or more role names that are allowed to access the decorated view.
        
    Returns:
        function: Decorated function with role-based access control.
        
    Example:
        @roles_required('admin', 'staff')
        def admin_dashboard():
            return render_template('admin/dashboard.html')
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
