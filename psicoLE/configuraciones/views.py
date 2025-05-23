from flask import Blueprint, render_template, redirect, url_for, flash, request
from database import db
from .models import Configuration
from .forms import ConfigurationForm
from psicoLE.auth.decorators import roles_required

configuraciones_bp = Blueprint('configuraciones', __name__,
                               template_folder='templates/configuraciones',
                               url_prefix='/configuraciones')

@configuraciones_bp.route('/')
@roles_required('admin')
def list_configurations():
    page = request.args.get('page', 1, type=int)
    search_term = request.args.get('search', '')
    
    query = Configuration.query.order_by(Configuration.key)
    
    if search_term:
        query = query.filter(db.or_(
            Configuration.key.ilike(f'%{search_term}%'),
            Configuration.value.ilike(f'%{search_term}%'),
            Configuration.description.ilike(f'%{search_term}%')
        ))
        
    configs = query.paginate(page=page, per_page=10) # Use items_per_page from config later
    return render_template('list_config.html', configs=configs, title='System Configurations', search_term=search_term)

@configuraciones_bp.route('/create', methods=['GET', 'POST'])
@roles_required('admin')
def create_configuration():
    form = ConfigurationForm()
    if form.validate_on_submit():
        new_config = Configuration(
            key=form.key.data,
            value=form.value.data,
            description=form.description.data
        )
        db.session.add(new_config)
        db.session.commit()
        flash(f'Configuration "{form.key.data}" created successfully!', 'success')
        return redirect(url_for('configuraciones.list_configurations'))
    return render_template('create_edit_config.html', form=form, title='Create Configuration', legend='New Configuration')

@configuraciones_bp.route('/<int:config_id>/edit', methods=['GET', 'POST'])
@roles_required('admin')
def edit_configuration(config_id):
    config_item = Configuration.query.get_or_404(config_id)
    form = ConfigurationForm(original_key=config_item.key, obj=config_item)
    
    if form.validate_on_submit():
        # Key should not be changed, but value and description can be
        config_item.value = form.value.data
        config_item.description = form.description.data
        db.session.commit()
        flash(f'Configuration "{config_item.key}" updated successfully!', 'success')
        return redirect(url_for('configuraciones.list_configurations'))
    
    return render_template('create_edit_config.html', form=form, title='Edit Configuration', 
                           legend=f'Edit Configuration: {config_item.key}', config_id=config_id)

@configuraciones_bp.route('/<int:config_id>/delete', methods=['POST'])
@roles_required('admin')
def delete_configuration(config_id):
    config_item = Configuration.query.get_or_404(config_id)
    try:
        db.session.delete(config_item)
        db.session.commit()
        flash(f'Configuration "{config_item.key}" deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting configuration "{config_item.key}": {str(e)}', 'danger')
        # Log the error e for server-side review
    return redirect(url_for('configuraciones.list_configurations'))
