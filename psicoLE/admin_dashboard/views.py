from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_login import current_user
from psicoLE.database import db
from psicoLE.auth.decorators import roles_required
from psicoLE.autogestion.models import DataChangeRequest
from psicoLE.profesionales.models import Professional
from datetime import datetime

admin_dashboard_bp = Blueprint('admin_dashboard', __name__,
                               template_folder='templates/admin_dashboard',
                               url_prefix='/admin') # Common prefix for admin tasks

@admin_dashboard_bp.route('/data-changes/pending')
@roles_required('admin', 'staff')
def list_pending_data_changes():
    pending_requests = DataChangeRequest.query.filter_by(status='pending') \
                                            .join(DataChangeRequest.professional) \
                                            .order_by(DataChangeRequest.requested_at.asc()) \
                                            .all()
    return render_template('list_pending_data_changes.html', 
                           requests=pending_requests, 
                           title='Pending Data Change Requests')

@admin_dashboard_bp.route('/data-changes/<int:request_id>/review', methods=['GET', 'POST'])
@roles_required('admin', 'staff')
def review_data_change(request_id):
    change_request = DataChangeRequest.query.get_or_404(request_id)
    professional = change_request.professional

    if request.method == 'POST':
        action = request.form.get('action') # 'approve' or 'reject'
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
from psicoLE.autogestion.models import DocumentoProfesional # Already imported if DataChangeRequest is here, but good for clarity
from flask import send_from_directory, current_app as app, abort # For file serving
import os

@admin_dashboard_bp.route('/documents/<int:document_id>/download')
@roles_required('admin', 'staff')
def download_professional_document_admin(document_id):
    document = DocumentoProfesional.query.get_or_404(document_id)
    # No ownership check needed for admin/staff
    
    directory = os.path.join(app.config['UPLOAD_FOLDER'], str(document.professional_id))
    filename = document.archivo_filename
    
    try:
        return send_from_directory(directory, filename, as_attachment=True)
    except FileNotFoundError:
        flash('File not found. It might have been moved or deleted.', 'danger')
        print(f"Admin Download Error: File not found at path: {os.path.join(directory, filename)}")
        abort(404)
    except Exception as e:
        flash(f'Error downloading file: {str(e)}', 'danger')
        print(f"Admin Download Error for file {filename}: {e}")
        # Redirect to professional detail page or a generic error page
        return redirect(url_for('profesionales.detail_professional', professional_id=document.professional_id))

@admin_dashboard_bp.route('/dashboard')
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
