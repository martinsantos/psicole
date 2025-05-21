from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import current_user
from psicoLE.auth.decorators import roles_required
from psicoLE.profesionales.models import Professional
from psicoLE.cobranzas.models import Cuota, Pago
from psicoLE.facturacion.models import Factura
from psicoLE.database import db # For potential direct queries if needed, though relationships are preferred

autogestion_bp = Blueprint('autogestion', __name__,
                           template_folder='templates/autogestion',
                           url_prefix='/autogestion')

@autogestion_bp.route('/financials')
@roles_required('professional')
def financial_dashboard():
    if not current_user.professional:
        flash('No professional profile linked to your user account. Please contact support.', 'warning')
        return redirect(url_for('hello_world')) # Or a more appropriate redirect

    professional = current_user.professional
    
    # Fetch fees, payments, and invoices for the logged-in professional
    # Using relationships defined in Professional model
    
    fees = professional.cuotas.order_by(Cuota.periodo.desc()).all()
    # Alternative if relationship is not ordered or for complex ordering:
    # fees = Cuota.query.filter_by(professional_id=professional.id).order_by(Cuota.periodo.desc()).all()
    
    payments = professional.pagos.order_by(Pago.fecha_pago.desc()).all()
    # payments = Pago.query.filter_by(professional_id=professional.id).order_by(Pago.fecha_pago.desc()).all()

    invoices = professional.facturas.order_by(Factura.fecha_emision.desc()).all()
    # invoices = Factura.query.filter_by(professional_id=professional.id).order_by(Factura.fecha_emision.desc()).all()

    return render_template('autogestion_financials.html', 
                           professional=professional,
                           fees=fees,
                           payments=payments,
                           invoices=invoices,
                           title='My Financial Dashboard')

@autogestion_bp.route('/profile')
@roles_required('professional')
def view_my_profile():
    if not current_user.professional:
        flash('No professional profile linked to your user account. Please contact support.', 'warning')
        return redirect(url_for('hello_world'))

    professional = current_user.professional
    # Fetch pending and recent (last 5-10) change requests for this professional
    pending_requests = DataChangeRequest.query.filter_by(
        professional_id=professional.id, 
        status='pending'
    ).order_by(DataChangeRequest.requested_at.desc()).all()
    
    recent_reviewed_requests = DataChangeRequest.query.filter(
        DataChangeRequest.professional_id == professional.id,
        DataChangeRequest.status.in_(['approved', 'rejected'])
    ).order_by(DataChangeRequest.reviewed_at.desc()).limit(5).all()

    return render_template('view_my_profile.html', 
                           professional=professional,
                           pending_requests=pending_requests,
                           recent_reviewed_requests=recent_reviewed_requests,
                           title='My Profile')

@autogestion_bp.route('/profile/request-change', methods=['GET', 'POST'])
@roles_required('professional')
def request_profile_change():
    if not current_user.professional:
        flash('No professional profile linked to your user account.', 'danger')
        return redirect(url_for('hello_world'))

    professional = current_user.professional
    # Pass professional_data to pre-fill the form
    form = ProfileEditRequestForm(professional_data=professional)

    if form.validate_on_submit():
        changes_requested_count = 0
        for field_name in EDITABLE_PROFESSIONAL_FIELDS.keys():
            current_value = getattr(professional, field_name, None)
            form_value = form[field_name].data
            
            # Normalize empty strings to None for comparison, especially for TextAreaField
            if isinstance(current_value, str) and not current_value.strip():
                current_value_comp = None
            else:
                current_value_comp = current_value

            if isinstance(form_value, str) and not form_value.strip():
                form_value_comp = None
            else:
                form_value_comp = form_value

            # Only create a request if the value has actually changed
            if form_value_comp != current_value_comp:
                # Check if a pending request for this field already exists
                existing_pending_request = DataChangeRequest.query.filter_by(
                    professional_id=professional.id,
                    field_name=field_name,
                    status='pending'
                ).first()

                if existing_pending_request:
                    # Update existing pending request's new_value and requested_at
                    existing_pending_request.old_value = str(current_value) if current_value is not None else None
                    existing_pending_request.new_value = str(form_value) if form_value is not None else None
                    existing_pending_request.requested_at = datetime.utcnow()
                    flash(f'Updated pending request for {EDITABLE_PROFESSIONAL_FIELDS[field_name]["label"]}.', 'info')
                else:
                    # Create new request
                    change_request = DataChangeRequest(
                        professional_id=professional.id,
                        field_name=field_name,
                        old_value=str(current_value) if current_value is not None else None,
                        new_value=str(form_value) if form_value is not None else None,
                        status='pending'
                    )
                    db.session.add(change_request)
                
                changes_requested_count += 1
        
        if changes_requested_count > 0:
            db.session.commit()
            flash('Your change requests have been submitted for review.', 'success')
        else:
            flash('No changes detected in the form.', 'info')
            
        return redirect(url_for('autogestion.view_my_profile'))

    return render_template('request_profile_change_form.html', 
                           form=form, 
                           professional=professional,
                           title='Request Profile Changes')

@autogestion_bp.route('/documents', methods=['GET', 'POST'])
@roles_required('professional')
def manage_my_documents():
    if not current_user.professional:
        flash('No professional profile linked to your user account.', 'danger')
        return redirect(url_for('hello_world'))

    professional = current_user.professional
    form = DocumentUploadForm()

    if form.validate_on_submit():
        file = form.document_file.data
        if file and allowed_file(file.filename): # allowed_file from main.py context processor
            try:
                filename = secure_filename(file.filename)
                # Path relative to UPLOAD_FOLDER. Store professional-specific files in subdirectories.
                professional_upload_dir_rel = str(professional.id) 
                professional_upload_dir_abs = os.path.join(app.config['UPLOAD_FOLDER'], professional_upload_dir_rel)
                
                os.makedirs(professional_upload_dir_abs, exist_ok=True)
                
                file_path_abs = os.path.join(professional_upload_dir_abs, filename)
                file.save(file_path_abs)
                
                # Store relative path for DB
                archivo_path_rel = os.path.join(professional_upload_dir_rel, filename)

                new_document = DocumentoProfesional(
                    professional_id=professional.id,
                    nombre_documento=form.nombre_documento.data,
                    tipo_documento=form.tipo_documento.data or None, # Handle empty string from select
                    archivo_filename=filename,
                    archivo_path=archivo_path_rel,
                    mimetype=file.mimetype
                )
                db.session.add(new_document)
                db.session.commit()
                flash('Document uploaded successfully!', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error uploading document: {str(e)}', 'danger')
                # Consider logging the error
            return redirect(url_for('autogestion.manage_my_documents'))
        elif file: # File was provided but not allowed
             flash('File type not allowed. Allowed types: ' + ", ".join(app.config['ALLOWED_EXTENSIONS']), 'danger')


    uploaded_documents = DocumentoProfesional.query.filter_by(professional_id=professional.id) \
                                               .order_by(DocumentoProfesional.fecha_carga.desc()).all()
    
    return render_template('manage_my_documents.html', 
                           form=form, 
                           documents=uploaded_documents,
                           title='Manage My Documents')

@autogestion_bp.route('/dashboard')
@roles_required('professional')
def autogestion_main_dashboard():
    if not current_user.professional:
        flash('No professional profile linked to your user account. Please contact support.', 'warning')
        return redirect(url_for('hello_world'))

    professional = current_user.professional
    
    # Outstanding Fees
    outstanding_fees_query = Cuota.query.filter(
        Cuota.professional_id == professional.id,
        Cuota.estado.in_(['pending', 'overdue', 'partially_paid'])
    )
    outstanding_fees_count = outstanding_fees_query.count()
    
    total_outstanding_amount_raw = db.session.query(db.func.sum(Cuota.monto_esperado - Cuota.monto_pagado)).filter(
        Cuota.professional_id == professional.id,
        Cuota.estado.in_(['pending', 'overdue', 'partially_paid'])
    ).scalar()
    total_outstanding_amount = total_outstanding_amount_raw or Decimal('0.00')
    
    # Filter out amounts that are zero or less after subtraction
    if total_outstanding_amount < Decimal('0.00'): # Should not happen if data is clean
        total_outstanding_amount = Decimal('0.00')


    # Count pending data change requests for this professional
    pending_profile_changes_count = DataChangeRequest.query.filter_by(
        professional_id=professional.id,
        status='pending'
    ).count()

    summary_info = {
        'status_matricula': professional.status_matricula,
        'vigencia_matricula': professional.vigencia_matricula.strftime('%d/%m/%Y') if professional.vigencia_matricula else 'N/A',
        'outstanding_fees_count': outstanding_fees_count,
        'total_outstanding_amount': total_outstanding_amount,
        'pending_profile_changes_count': pending_profile_changes_count,
    }

    return render_template('dashboard.html', 
                           professional=professional,
                           summary_info=summary_info,
                           title='My Dashboard')

@autogestion_bp.route('/documents/<int:document_id>/download')
@roles_required('professional')
def download_my_document(document_id):
    document = DocumentoProfesional.query.get_or_404(document_id)
    if not current_user.professional or document.professional_id != current_user.professional.id:
        flash('You are not authorized to download this document.', 'danger')
        return redirect(url_for('autogestion.manage_my_documents'))
    
    # Construct the absolute path to the file
    # UPLOAD_FOLDER is 'instance/uploads/professional_documents'
    # archivo_path is '<professional_id>/<filename>'
    # So, we need to serve from 'instance/uploads/professional_documents/<professional_id>' directory
    
    directory = os.path.join(app.config['UPLOAD_FOLDER'], str(document.professional_id))
    filename = document.archivo_filename
    
    try:
        return send_from_directory(directory, filename, as_attachment=True)
    except FileNotFoundError:
        flash('File not found. It might have been moved or deleted by an administrator.', 'danger')
        # Log this error server-side
        print(f"Error: File not found at path: {os.path.join(directory, filename)}")
        abort(404) # Or redirect
    except Exception as e:
        flash(f'Error downloading file: {str(e)}', 'danger')
        print(f"Error downloading file {filename}: {e}")
        return redirect(url_for('autogestion.manage_my_documents'))

@autogestion_bp.route('/documents/<int:document_id>/delete', methods=['POST'])
@roles_required('professional')
def delete_my_document(document_id):
    document = DocumentoProfesional.query.get_or_404(document_id)
    if not current_user.professional or document.professional_id != current_user.professional.id:
        flash('You are not authorized to delete this document.', 'danger')
        return redirect(url_for('autogestion.manage_my_documents'))

    try:
        # Construct the absolute path to the file
        file_path_abs = os.path.join(app.config['UPLOAD_FOLDER'], document.archivo_path)
        
        # Delete file from filesystem
        if os.path.exists(file_path_abs):
            os.remove(file_path_abs)
            # Consider removing the professional's subdirectory if it becomes empty
            # professional_dir = os.path.dirname(file_path_abs)
            # if not os.listdir(professional_dir):
            #     os.rmdir(professional_dir)
        else:
            flash('File not found on server, but deleting record.', 'warning')
            # Log this inconsistency

        # Delete record from database
        db.session.delete(document)
        db.session.commit()
        flash(f'Document "{document.nombre_documento}" deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting document: {str(e)}', 'danger')
        # Log error e
        
    return redirect(url_for('autogestion.manage_my_documents'))
