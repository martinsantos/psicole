from functools import wraps
from flask import flash, redirect, url_for, request # Added request
from flask_login import current_user

def roles_required(*role_names):
    """
    Ensures the current user is logged in and has at least one of the specified roles.
    Redirects to login if not authenticated, or to an unauthorized page if role not matched.
    Usage: @roles_required('admin', 'staff')
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
