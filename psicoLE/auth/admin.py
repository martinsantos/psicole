"""Admin interface configuration."""
from datetime import datetime, timedelta
from flask import url_for, redirect, request, abort, current_app, flash
from flask_login import current_user
from flask_admin import Admin, AdminIndexView, expose, BaseView
from flask_admin.contrib.sqla import ModelView
from flask_admin.menu import MenuLink
from werkzeug.security import generate_password_hash
from sqlalchemy import func, and_

# Import db from the auth package to avoid circular imports
from . import db

# Import models after db is defined to avoid circular imports
from .models import User, Role, SecurityEvent, UserSession, SecurityQuestion, SecurityEventType

# Custom formatters
def _format_datetime(view, context, model, name):
    """Format datetime for admin views."""
    value = getattr(model, name, None)
    if value is None:
        return ''
    return value.strftime('%Y-%m-%d %H:%M:%S')

def _format_user(view, context, model, name):
    """Format user for admin views."""
    user = getattr(model, 'user', None)
    if user:
        return f"{user.email} ({user.id})"
    return ''

class CustomAdminIndexView(AdminIndexView):
    @expose('/')
    def index(self):
        if not current_user.is_authenticated or not current_user.is_administrator():
            return redirect(url_for('auth.login', next=request.url))
            
        # Get user statistics
        user_count = User.query.count()
        active_sessions = UserSession.query.filter_by(is_active=True).count()
        
        # Get security events from the last 7 days
        week_ago = datetime.utcnow() - timedelta(days=7)
        security_events_7d = SecurityEvent.query.filter(
            SecurityEvent.created_at >= week_ago
        ).count()
        
        # Get new users from the last 7 days
        new_users_7d = User.query.filter(
            User.created_at >= week_ago
        ).count()
        
        # Get recent security events with user information
        recent_activity = db.session.query(
            SecurityEvent,
            User.email
        ).outerjoin(
            User, SecurityEvent.user_id == User.id
        ).order_by(
            SecurityEvent.created_at.desc()
        ).limit(10).all()
        
        # Format recent activity for template
        formatted_activity = []
        for event, email in recent_activity:
            formatted_activity.append({
                'event_type': event.event_type,
                'user_email': email,
                'ip_address': event.ip_address,
                'user_agent': event.user_agent,
                'created_at': event.created_at,
                'details': event.details
            })
        
        # Get user distribution by role
        user_roles = db.session.query(
            Role.name,
            func.count(User.id).label('count'),
            Role.color
        ).outerjoin(
            User, User.role_id == Role.id
        ).group_by(Role.id).all()
        
        # Convert to list of dicts with colors
        roles_with_colors = []
        colors = ['#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', '#e74a3b', '#858796']
        for i, (name, count, color) in enumerate(user_roles):
            roles_with_colors.append({
                'name': name,
                'count': count,
                'color': color or colors[i % len(colors)]
            })
        
        # Get system status (placeholder values - replace with actual system metrics)
        system_status = {
            'cpu_usage': 45,
            'memory_usage': 65,
            'disk_usage': 30,
            'uptime': '5d 12h 30m'
        }
        
        return self.render('admin/index.html',
                         user_count=user_count,
                         active_sessions=active_sessions,
                         security_events_7d=security_events_7d,
                         new_users_7d=new_users_7d,
                         recent_activity=formatted_activity,
                         user_roles=roles_with_colors,
                         system_status=system_status)

class SecureModelView(ModelView):
    """Base model view with security checks and common configurations."""
    
    # Set the number of items to display per page
    page_size = 20
    
    # Enable CSRF protection
    form_base_class = None  # You can set this to use CSRF protected forms
    
    # Enable model creation/editing/deletion
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    
    # Export options
    can_export = True
    export_types = ['csv', 'xlsx']
    
    def is_accessible(self):
        """Check if the current user has access to the admin interface."""
        if not current_user.is_authenticated:
            return False
        # Only allow users with admin role to access the admin interface
        return current_user.is_administrator()
    
    def inaccessible_callback(self, name, **kwargs):
        """Handle unauthorized access attempts."""
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login', next=request.url))
        flash('No tienes permiso para acceder a esta sección.', 'error')
        return redirect(url_for('admin.index'))
    
    def after_model_change(self, form, model, is_created):
        """Log changes to the model."""
        if is_created:
            action = 'created'
        else:
            action = 'updated'
            
        # Log the action to security events
        try:
            event = SecurityEvent(
                user_id=current_user.id,
                event_type=f'model_{model.__tablename__}_{action}',
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string,
                details={
                    'model': model.__tablename__,
                    'action': action,
                    'id': getattr(model, 'id', None)
                }
            )
            db.session.add(event)
            db.session.commit()
        except Exception as e:
            current_app.logger.error(f'Error logging admin action: {str(e)}')
            db.session.rollback()
    
    def after_model_delete(self, model):
        """Log model deletion."""
        try:
            event = SecurityEvent(
                user_id=current_user.id,
                event_type=f'model_{model.__tablename__}_deleted',
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string,
                details={
                    'model': model.__tablename__,
                    'id': getattr(model, 'id', None)
                }
            )
            db.session.add(event)
            db.session.commit()
        except Exception as e:
            current_app.logger.error(f'Error logging admin delete action: {str(e)}')
            db.session.rollback()
    
    # Common column formatters
    column_formatters = {
        'created_at': _format_datetime,
        'updated_at': _format_datetime,
        'last_login': _format_datetime,
        'user': _format_user
    }


class SecureIndexView(AdminIndexView):
    """Custom admin index view with security checks."""
    
    @expose('/')
    def index(self):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login', next=request.url))
        if not current_user.is_administrator():
            abort(403, description="No tienes permiso para acceder al panel de administración.")
        return super().index()


def init_admin(app, db_instance):
    """Initialize the admin interface."""
    # Create admin interface with custom index view
    admin = Admin(
        app,
        name='Psicole Admin',
        template_mode='bootstrap4',
        index_view=CustomAdminIndexView(
            name='Inicio',
            template='admin/index.html',
            url='/admin',
            endpoint='admin'
        )
    )
    
    # Import models here to avoid circular imports
    from .models import User, Role, SecurityEvent, SecurityQuestion, UserSession
    
    # Add model views
    admin.add_view(UserModelView(User, db.session, name='Usuarios', category='Usuarios y Roles'))
    admin.add_view(RoleModelView(Role, db.session, name='Roles', category='Usuarios y Roles'))
    admin.add_view(SecurityEventModelView(SecurityEvent, db.session, name='Eventos de Seguridad', category='Seguridad'))
    admin.add_view(SecurityQuestionModelView(SecurityQuestion, db.session, name='Preguntas de Seguridad', category='Seguridad'))
    admin.add_view(UserSessionModelView(UserSession, db.session, name='Sesiones de Usuario', category='Seguridad'))
    
    # Add custom links
    admin.add_link(MenuLink(name='Volver al Sitio', url='/'))
    admin.add_link(MenuLink(name='Cerrar Sesión', url='/auth/logout'))
    
    return admin


# Custom Model Views
class UserModelView(SecureModelView):
    """Custom view for User model."""
    # List view configuration
    column_list = [
        'email', 'first_name', 'last_name', 'role', 
        'is_active', 'email_verified', 'last_login', 'created_at'
    ]
    column_searchable_list = ['email', 'first_name', 'last_name']
    column_filters = [
        'is_active', 'email_verified', 'role.name', 'created_at', 'last_login'
    ]
    column_default_sort = ('created_at', True)
    
    # Form configuration
    form_columns = [
        'email', 'first_name', 'last_name', 'role', 
        'is_active', 'email_verified', 'password'
    ]
    form_edit_rules = {
        'email', 'first_name', 'last_name', 'role', 
        'is_active', 'email_verified', 'password'
    }
    form_create_rules = form_edit_rules
    
    # Override password field to use password input
    form_overrides = {}
    form_args = {
        'password': {
            'label': 'Contraseña',
            'description': 'Dejar en blanco para mantener la contraseña actual',
            'validators': []  # Remove default required validator
        }
    }
    
    def on_model_change(self, form, model, is_created):
        """Handle model changes."""
        # Only set password if it was provided in the form
        if form.password.data:
            model.set_password(form.password.data)
        
        # Log the action
        action = 'creado' if is_created else 'actualizado'
        current_app.logger.info(f'Usuario {model.email} {action} por {current_user.email}')
        
        # Call parent method
        return super().on_model_change(form, model, is_created)


class RoleModelView(SecureModelView):
    """Custom view for Role model."""
    # List view configuration
    column_list = ['name', 'description', 'permissions', 'users_count']
    column_searchable_list = ['name', 'description']
    column_filters = ['name']
    column_default_sort = ('name', True)
    
    # Form configuration
    form_columns = ['name', 'description', 'permissions', 'users']
    form_edit_rules = form_columns
    form_create_rules = form_columns
    
    # Custom column for user count
    def users_count(self, context, model, name):
        return len(model.users)
    
    # Set column labels
    column_labels = {
        'name': 'Nombre',
        'description': 'Descripción',
        'permissions': 'Permisos',
        'users_count': 'Usuarios',
        'users': 'Usuarios Asociados'
    }
    
    def on_model_change(self, form, model, is_created):
        """Handle model changes."""
        # Log the action
        action = 'creado' if is_created else 'actualizado'
        current_app.logger.info(f'Rol {model.name} {action} por {current_user.email}')
        return super().on_model_change(form, model, is_created)


class SecurityEventModelView(SecureModelView):
    """Custom view for SecurityEvent model."""
    # List view configuration
    column_list = ['event_type', 'user', 'ip_address', 'user_agent', 'created_at']
    column_searchable_list = ['event_type', 'ip_address', 'user_agent']
    column_filters = ['event_type', 'created_at', 'ip_address']
    column_default_sort = ('-created_at', True)
    can_create = False
    can_edit = False
    can_delete = True
    
    # Set column labels
    column_labels = {
        'event_type': 'Tipo de Evento',
        'user': 'Usuario',
        'ip_address': 'Dirección IP',
        'user_agent': 'Navegador',
        'created_at': 'Fecha y Hora',
        'details': 'Detalles'
    }
    
    # Custom column formatters
    column_formatters = {
        'created_at': _format_datetime,
        'user': _format_user,
        'details': lambda v, c, m, n: str(m.details)[:100] + '...' if m.details else ''
    }
    
    # Export configuration
    column_export_list = ['event_type', 'user', 'ip_address', 'created_at']
    column_formatters_export = {
        'created_at': _format_datetime,
        'user': _format_user
    }


class SecurityQuestionModelView(SecureModelView):
    """Custom view for SecurityQuestion model."""
    # List view configuration
    column_list = ['question', 'is_active', 'created_at', 'updated_at']
    column_searchable_list = ['question']
    column_filters = ['is_active', 'created_at']
    column_default_sort = ('question', True)
    
    # Form configuration
    form_columns = ['question', 'is_active']
    form_edit_rules = form_columns
    form_create_rules = form_columns
    
    # Set column labels
    column_labels = {
        'question': 'Pregunta',
        'is_active': 'Activa',
        'created_at': 'Creada',
        'updated_at': 'Actualizada'
    }
    
    # Custom column formatters
    column_formatters = {
        'created_at': _format_datetime,
        'updated_at': _format_datetime
    }
    
    def on_model_change(self, form, model, is_created):
        """Handle model changes."""
        # Log the action
        action = 'creada' if is_created else 'actualizada'
        current_app.logger.info(f'Pregunta de seguridad {model.id} {action} por {current_user.email}')
        return super().on_model_change(form, model, is_created)


class UserSessionModelView(SecureModelView):
    """Custom view for UserSession model."""
    # List view configuration
    column_list = ['user', 'ip_address', 'user_agent', 'last_activity', 'is_active', 'created_at']
    column_searchable_list = ['ip_address', 'user_agent']
    column_filters = ['is_active', 'last_activity', 'created_at', 'ip_address']
    column_default_sort = ('-last_activity', True)
    can_edit = False
    can_create = False
    
    # Set column labels
    column_labels = {
        'user': 'Usuario',
        'ip_address': 'Dirección IP',
        'user_agent': 'Navegador',
        'last_activity': 'Última Actividad',
        'is_active': 'Activa',
        'created_at': 'Creada'
    }
    
    # Custom column formatters
    column_formatters = {
        'user': _format_user,
        'last_activity': _format_datetime,
        'created_at': _format_datetime
    }
    
    # Export configuration
    column_export_list = ['user', 'ip_address', 'last_activity', 'is_active']
    column_formatters_export = {
        'user': _format_user,
        'last_activity': _format_datetime
    }
