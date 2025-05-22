from flask import render_template, flash, redirect, url_for, request, current_app
from flask_login import current_user, login_required
from datetime import datetime, timedelta
from . import admin_bp as admin_dashboard_bp
from auth.models import db, User, Role
from auth.decorators import roles_required

# Import models with error handling
try:
    from profesionales.models import Professional
except ImportError:
    Professional = None

try:
    from payments.models import Payment
except ImportError:
    Payment = None

try:
    from autogestion.models import DataChangeRequest
except ImportError:
    DataChangeRequest = None

@admin_dashboard_bp.route('/')
@login_required
@roles_required('admin', 'staff')
def dashboard():
    # Initialize stats with default values
    stats = {
        'total_users': User.query.count(),
        'admin_users': User.query.join(Role).filter(Role.name == 'admin').count(),
        'staff_users': User.query.join(Role).filter(Role.name == 'staff').count(),
        'professional_users': User.query.join(Role).filter(Role.name == 'professional').count()
    }
    
    # Add additional stats if models are available
    if Professional:
        stats['active_professionals'] = Professional.query.filter_by(is_active=True).count()
    
    if DataChangeRequest:
        stats['pending_data_changes'] = DataChangeRequest.query.filter_by(status='pending').count()
    
    if Payment:
        stats['pending_payments'] = Payment.query.filter_by(status='pending').count()
        stats['total_earnings'] = sum(p.amount for p in Payment.query.filter_by(status='completed').all())
    
    # Get recent users
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    
    return render_template('admin_dashboard/dashboard.html',
                         title='Panel de Administración',
                         stats=stats,
                         recent_users=recent_users)

@admin_dashboard_bp.route('/data-changes/pending')
@roles_required('admin', 'staff')
def list_pending_data_changes():
    pending_requests = DataChangeRequest.query.filter_by(status='pending') \
                                            .join(DataChangeRequest.professional) \
                                            .order_by(DataChangeRequest.requested_at.asc()) \
                                            .all()
    return render_template('admin_dashboard/list_pending_data_changes.html', 
                         requests=pending_requests, 
                         title='Solicitudes de Cambio de Datos Pendientes')

@admin_dashboard_bp.route('/data-changes/<int:request_id>/review', methods=['GET', 'POST'])
@roles_required('admin', 'staff')
def review_data_change(request_id):
    change_request = DataChangeRequest.query.get_or_404(request_id)
    professional = change_request.professional

    if request.method == 'POST':
        action = request.form.get('action')  # 'approve' or 'reject'
        review_comments = request.form.get('review_comments', None)

        if action == 'approve':
            try:
                # Update the professional's field
                # Make sure field_name is a valid attribute of Professional model
                if hasattr(professional, change_request.field_name):
                    setattr(professional, change_request.field_name, change_request.new_value)
                    db.session.add(professional) # Add professional to session for update
                    
                    change_request.status = 'approved'
                    flash(f'Change request for {professional.first_name} {professional.last_name} ({change_request.field_name}) approved and data updated.', 'success')
                else:
                    change_request.status = 'rejected' # Cannot apply if field is invalid
                    flash(f'Field "{change_request.field_name}" not found on professional model. Request rejected.', 'danger')
            except Exception as e:
                db.session.rollback()
                flash(f'Error approving change: {str(e)}', 'danger')
                return redirect(url_for('admin_dashboard.list_pending_data_changes'))
        
        elif action == 'reject':
            change_request.status = 'rejected'
            flash(f'Change request for {professional.first_name} {professional.last_name} ({change_request.field_name}) rejected.', 'info')
        
        else:
            flash('Invalid action.', 'danger')
            return redirect(url_for('admin_dashboard.review_data_change', request_id=request_id))

        change_request.reviewed_at = datetime.utcnow()
        change_request.reviewer_id = current_user.id
        change_request.review_comments = review_comments
        
        try:
            db.session.add(change_request) # Add change_request to session
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f'Error saving review: {str(e)}', 'danger')
            
        return redirect(url_for('admin_dashboard.list_pending_data_changes'))

    return render_template('review_data_change_form.html', 
                           change_request=change_request, 
                           professional=professional,
                           title='Review Data Change Request')

# View for Admin/Staff to download any professional's document
from flask import send_from_directory, abort
import os

@admin_dashboard_bp.route('/documents/<int:document_id>/download')
@roles_required('admin', 'staff')
def download_professional_document_admin(document_id):
    document = DocumentoProfesional.query.get_or_404(document_id)
    
    # Verify the file exists
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], document.storage_path)
    if not os.path.exists(file_path):
        abort(404, "El archivo solicitado no existe.")
    
    # Determine the download name (original filename or generate one)
    download_name = document.original_filename or f"documento_{document.id}{os.path.splitext(document.storage_path)[1]}"
    
    return send_from_directory(
        os.path.dirname(file_path),
        os.path.basename(file_path),
        as_attachment=True,
        download_name=download_name
    )

@admin_dashboard_bp.route('/admin/dashboard')
@roles_required('admin', 'staff')
def admin_dashboard_main():
    # Key Statistics
    active_professionals_count = Professional.query.filter_by(status_matricula='active').count()
    
    pending_fees_query = Cuota.query.filter(Cuota.estado.in_(['pending', 'overdue', 'partially_paid']))
    pending_fees_count = pending_fees_query.count()
    
    # Calculate total pending amount
    total_pending_amount_raw = db.session.query(db.func.sum(Cuota.monto_esperado - Cuota.monto_pagado)) \
        .filter(Cuota.estado.in_(['pending', 'overdue', 'partially_paid'])) \
        .scalar()
    total_pending_amount = total_pending_amount_raw or Decimal('0.00')


    today_date = datetime.date.today() # Use datetime.date for comparison with Date field
    payments_today_count = Pago.query.filter(
        db.func.date(Pago.fecha_pago) == today_date, 
        Pago.confirmado == True
    ).count()
    
    # This is already available via context processor, but can be queried here too for direct use
    pending_data_changes_count = DataChangeRequest.query.filter_by(status='pending').count()

    stats = {
        'active_professionals': active_professionals_count,
        'pending_fees_count': pending_fees_count,
        'total_pending_amount': total_pending_amount,
        'payments_today_count': payments_today_count,
        'pending_data_changes': pending_data_changes_count
    }

    return render_template('dashboard.html', stats=stats, title="Admin Dashboard")
