from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask import Blueprint, render_template, redirect, url_for, flash, request, Response
from psicoLE.database import db
from .models import Cuota, Pago
from psicoLE.profesionales.models import Professional # Added for joining
from .forms import GenerateFeesForm, FeeFilterForm, AutomaticDebitListFilterForm # Added new form
from .services import generate_monthly_fees, update_fee_status_after_payment # Added update_fee_status
from .services import create_mercadopago_preference # Added MP preference
from psicoLE.auth.decorators import roles_required
from decimal import Decimal, InvalidOperation
from datetime import date, datetime # Added for type checking/conversion
import io # For CSV export
import csv # For CSV export

cobranzas_bp = Blueprint('cobranzas', __name__,
                         template_folder='templates/cobranzas',
                         url_prefix='/cobranzas')

@cobranzas_bp.route('/generate-fees', methods=['GET', 'POST'])
@roles_required('admin')
def generate_fees_view():
    form = GenerateFeesForm()
    if form.validate_on_submit():
        try:
            periodo = form.periodo.data
            fecha_vencimiento = form.fecha_vencimiento.data
            monto_general = form.monto_general.data # This is already a Decimal from the form

            success_count, already_exist_count, error_count = generate_monthly_fees(
                periodo_str=periodo,
                fecha_vencimiento_date=fecha_vencimiento,
                monto_general_decimal=monto_general
            )
            
            message = f"Fee generation process completed. "
            if success_count > 0:
                message += f"{success_count} fees generated successfully. "
            if already_exist_count > 0:
                message += f"{already_exist_count} fees already existed for this period. "
            if error_count > 0:
                message += f"{error_count} errors occurred. Check logs for details."
            
            if error_count > 0:
                flash(message, 'warning')
            else:
                flash(message, 'success')
                
            return redirect(url_for('cobranzas.list_fees')) # Redirect to list view after generation
        except ValueError as ve: # Catch specific ValueError from service
            flash(f"Error: {str(ve)}", 'danger')
        except InvalidOperation: # Catch issues with Decimal conversion if form didn't handle it
            flash('Invalid amount provided for fee generation.', 'danger')
        except Exception as e:
            flash(f'An unexpected error occurred during fee generation: {str(e)}', 'danger')
            # Log the error e
            
    return render_template('generate_fees.html', form=form, title='Generate Monthly Fees')

@cobranzas_bp.route('/fees', methods=['GET', 'POST']) # Allow POST for form submission if kept on same page
@roles_required('admin', 'staff')
def list_fees():
    form = FeeFilterForm(request.form if request.method == 'POST' else request.args)
    page = request.args.get('page', 1, type=int)
    
    query = Cuota.query.join(Cuota.professional).order_by(Cuota.periodo.desc(), Professional.last_name) # Assuming Professional model is imported

    if form.validate_on_submit() or request.method == 'GET': # Process filters on GET or valid POST
        if form.professional_id.data:
            query = query.filter(Cuota.professional_id == form.professional_id.data.id)
        if form.periodo.data:
            query = query.filter(Cuota.periodo == form.periodo.data)
        if form.estado.data:
            query = query.filter(Cuota.estado == form.estado.data)

    from psicoLE.configuraciones.utils import get_config_value # Import here to avoid circular dependency at top level
    try:
        items_per_page = int(get_config_value('items_per_page', '10'))
    except ValueError:
        items_per_page = 10 # Fallback if config value is not a valid integer
    
    fees_list = query.paginate(page=page, per_page=items_per_page)
    
    # If form is submitted via POST and not valid, errors will be in form.errors
    # If GET, form.errors will be empty.
    return render_template('list_fees.html', fees=fees_list, form=form, title='List of Fees')


@cobranzas_bp.route('/fees/<int:cuota_id>')
@roles_required('admin', 'staff')
def detail_fee(cuota_id):
    cuota = Cuota.query.get_or_404(cuota_id)
    # Pagos associated with this cuota, ordered by date
    pagos = cuota.pagos.order_by(Pago.fecha_pago.desc()).all()
    
    return render_template('detail_fee.html', cuota=cuota, pagos=pagos, title='Fee Details')

@cobranzas_bp.route('/fees/<int:cuota_id>/record-payment', methods=['GET', 'POST'])
@roles_required('admin', 'staff')
def record_payment_for_cuota(cuota_id):
    cuota = Cuota.query.get_or_404(cuota_id)
    form = ManualPaymentForm(cuota=cuota) # Pass cuota to pre-fill form

    # Disable professional_id field as it's determined by the cuota
    # form.professional_id.render_kw = {'disabled': True} # This prevents data submission
    # Instead, we will rely on the fact that it's pre-selected and not change it.
    # Or, remove it from the form if it's purely display. For now, it's pre-selected.

    if form.validate_on_submit():
        try:
            nuevo_pago = Pago(
                professional_id=cuota.professional_id, # Get from cuota
                cuota_id=cuota.id,
                monto=form.monto_pagado.data,
                fecha_pago=form.fecha_pago.data, # Form provides date, Pago model expects DateTime for field
                metodo_pago=form.metodo_pago.data,
                referencia_pago=form.referencia_pago.data,
                confirmado=form.confirmado.data
            )
            # Convert date to datetime for 'fecha_pago' if model expects datetime
            # If your Pago.fecha_pago is DateTime, and form.fecha_pago.data is date:
            # nuevo_pago.fecha_pago = datetime.combine(form.fecha_pago.data, datetime.min.time())
            # However, the Pago model has default=datetime.utcnow for fecha_pago.
            # Let's assume the model handles date/datetime conversion or default if form provides date.
            # For clarity, let's ensure it's a datetime object if the model field is DateTime
            if isinstance(form.fecha_pago.data, date) and not isinstance(form.fecha_pago.data, datetime):
                 nuevo_pago.fecha_pago = datetime.combine(form.fecha_pago.data, datetime.min.time())


            db.session.add(nuevo_pago)
            db.session.commit() # Commit the payment first

            if nuevo_pago.confirmado:
                if update_fee_status_after_payment(cuota.id):
                    flash('Payment recorded and fee status updated successfully!', 'success')
                else:
                    flash('Payment recorded, but failed to update fee status. Please check logs.', 'warning')
            else:
                flash('Payment recorded but is pending confirmation. Fee status not updated yet.', 'info')
            
            return redirect(url_for('cobranzas.detail_fee', cuota_id=cuota.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error recording payment: {str(e)}', 'danger')
            # Log error e
    
    # For GET request, ensure professional_id is correctly set for display in template if needed
    # The form constructor already handles setting professional_id.data
    
    return render_template('record_payment.html', form=form, cuota=cuota, title='Record Payment')

@cobranzas_bp.route('/fees/<int:cuota_id>/pay-online', methods=['GET'])
@roles_required('professional') # Assuming 'professional' role users pay their own fees
def initiate_online_payment(cuota_id):
    cuota = Cuota.query.get_or_404(cuota_id)

    # Security Check: Ensure the current user (professional) is linked to this cuota's professional
    if not current_user.professional or current_user.professional.id != cuota.professional_id:
        flash('You are not authorized to pay this fee.', 'danger')
        # Redirect to a relevant page, e.g., their dashboard or fees list
        return redirect(url_for('cobranzas.list_fees')) # Or a user-specific dashboard

    if cuota.estado == 'paid' or (cuota.monto_esperado - cuota.monto_pagado <= Decimal('0.00')):
        flash('This fee is already paid or has no pending amount.', 'info')
        return redirect(url_for('cobranzas.detail_fee', cuota_id=cuota.id))

    try:
        # Construct callback and notification URLs
        # Ensure these are absolute URLs if MP requires it (use url_for with _external=True)
        base_url = request.url_root.rstrip('/') # Get base URL like http://localhost:5001
        
        success_url = url_for('cobranzas.mercadopago_callback', _external=True, status='success', cuota_id=cuota.id, session_id="{CHECKOUT_SESSION_ID}")
        failure_url = url_for('cobranzas.mercadopago_callback', _external=True, status='failure', cuota_id=cuota.id, session_id="{CHECKOUT_SESSION_ID}")
        pending_url = url_for('cobranzas.mercadopago_callback', _external=True, status='pending', cuota_id=cuota.id, session_id="{CHECKOUT_SESSION_ID}")
        notification_url = url_for('cobranzas.mercadopago_webhook', _external=True) # MP will POST here

        preference = create_mercadopago_preference(
            cuota=cuota,
            success_url=success_url,
            failure_url=failure_url,
            pending_url=pending_url,
            notification_url=notification_url
        )
        
        # Store preference_id if needed for reconciliation before webhook, e.g., in session or temp table
        # session[f'mp_preference_cuota_{cuota.id}'] = preference['id']
        
        # Redirect user to Mercado Pago checkout
        return redirect(preference['init_point'])

    except ValueError as ve: # From remaining_balance check in create_mercadopago_preference
        flash(str(ve), 'warning')
        return redirect(url_for('cobranzas.detail_fee', cuota_id=cuota.id))
    except Exception as e:
        flash(f'Error creating Mercado Pago preference: {str(e)}', 'danger')
        # Log error e
        return redirect(url_for('cobranzas.detail_fee', cuota_id=cuota.id))


@cobranzas_bp.route('/payment/mercadopago/callback')
# No role required here as it's a redirect from MP.
def mercadopago_callback():
    payment_status = request.args.get('status')
    cuota_id = request.args.get('external_reference') # MP often sends external_reference back
    
    if not cuota_id: # Fallback if external_reference is not in main query params
        cuota_id = request.args.get('cuota_id') 

    # Other params from MP: collection_id, payment_id, merchant_order_id, preference_id
    # For now, just display a generic message based on 'status'
    
    status_message = "Payment processing..."
    alert_type = "info"

    if payment_status == 'success' or payment_status == 'approved':
        status_message = "Your payment was successful! We are processing it."
        alert_type = "success"
    elif payment_status == 'failure' or payment_status == 'rejected':
        status_message = "Your payment failed. Please try again or contact support."
        alert_type = "danger"
    elif payment_status == 'pending':
        status_message = "Your payment is pending approval. We will notify you once it's processed."
        alert_type = "warning"
    
    flash(status_message, alert_type)
    
    # Redirect to fee detail page or a generic payment status page
    if cuota_id:
        try:
            # Validate cuota_id if needed
            int(cuota_id)
            return redirect(url_for('cobranzas.detail_fee', cuota_id=cuota_id))
        except ValueError:
            # Log: Invalid cuota_id received in callback
            pass # Fall through to generic redirect
            
    return redirect(url_for('cobranzas.list_fees')) # Or a user dashboard

@cobranzas_bp.route('/payment/mercadopago/webhook', methods=['POST'])
# @csrf.exempt # If using Flask-WTF CSRF globally, this is important
def mercadopago_webhook():
    data = request.json
    if not data:
        # Log: No data received or not JSON
        return "No data received", 400

    print(f"Webhook received: {data}") # For debugging, remove in production

    webhook_type = data.get('type')
    action = data.get('action') # Some newer webhooks use 'action' (e.g., payment.created, payment.updated)
    
    # Prioritize 'action' if available, otherwise fall back to 'type'
    if action and 'payment' in action: # e.g. action == 'payment.updated' or 'payment.created'
        mercadopago_payment_id = data.get('data', {}).get('id')
        event_topic = 'payment' # Generic payment event
    elif webhook_type == 'payment':
        mercadopago_payment_id = data.get('data', {}).get('id')
        event_topic = 'payment'
    elif webhook_type == 'application.authorized': # For app authorization, not payment
        # Handle app authorization if needed
        print(f"Received application authorization event: {data}")
        return "OK", 200
    else:
        # Log: Unknown webhook type or action
        print(f"Unknown webhook type/action: Type='{webhook_type}', Action='{action}'")
        return "Unknown event type/action", 200 # Return 200 to MP to stop retries for this event

    if not mercadopago_payment_id:
        # Log: No payment ID in webhook data
        return "No payment ID found in data", 400

    from psicoLE.main import get_mp_sdk
    sdk = get_mp_sdk()
    if not sdk:
        # Log: SDK not initialized
        return "SDK not initialized", 500

    try:
        payment_info_response = sdk.payment().get(mercadopago_payment_id)
        if payment_info_response["status"] != 200:
            # Log: Error fetching payment from MP
            print(f"Error fetching payment {mercadopago_payment_id} from MP: {payment_info_response}")
            return "Error fetching payment", 500
        
        payment_info = payment_info_response["response"]
        
        cuota_id_str = payment_info.get('external_reference')
        payment_status = payment_info.get('status')
        total_paid_amount = Decimal(str(payment_info.get('transaction_amount', '0.00'))) # Ensure Decimal
        
        if not cuota_id_str:
            # Log: No external_reference (cuota_id) in payment_info
            print(f"No external_reference in payment_info for MP payment ID {mercadopago_payment_id}")
            return "No external_reference found", 200 # Return 200 so MP doesn't retry for this non-actionable event

        try:
            cuota_id = int(cuota_id_str)
        except ValueError:
            print(f"Invalid cuota_id (external_reference) '{cuota_id_str}' in payment_info for MP payment ID {mercadopago_payment_id}")
            return "Invalid external_reference format", 200


        cuota = Cuota.query.get(cuota_id)
        if not cuota:
            # Log: Cuota not found for cuota_id
            print(f"Cuota with ID {cuota_id} not found for MP payment ID {mercadopago_payment_id}")
            return "Cuota not found", 200 # 200 so MP doesn't retry

        if payment_status == 'approved':
            # Check for existing Pago to prevent duplicates
            existing_pago = Pago.query.filter_by(referencia_pago=str(mercadopago_payment_id)).first()
            if existing_pago:
                # Log: Payment already processed
                print(f"Payment {mercadopago_payment_id} already processed for cuota {cuota_id}.")
                # Optionally, re-update fee status just in case, or simply acknowledge
                if existing_pago.confirmado:
                     update_fee_status_after_payment(cuota.id)
                return "OK, payment already processed", 200

            nuevo_pago = Pago(
                professional_id=cuota.professional_id,
                cuota_id=cuota.id,
                monto=total_paid_amount,
                fecha_pago=datetime.utcnow(), # Or use payment_info.get('date_approved') or 'date_created'
                metodo_pago=payment_info.get('payment_type_id', 'online_mp'), # e.g. 'credit_card', 'account_money'
                referencia_pago=str(mercadopago_payment_id),
                confirmado=True 
            )
            db.session.add(nuevo_pago)
            db.session.commit()
            
            if update_fee_status_after_payment(cuota.id):
                # Log: Payment processed and fee updated
                print(f"Payment {mercadopago_payment_id} processed for cuota {cuota_id}, fee status updated.")
            else:
                # Log: Payment processed but fee update failed
                print(f"Payment {mercadopago_payment_id} processed for cuota {cuota_id}, BUT fee status update FAILED.")
        
        elif payment_status in ['rejected', 'cancelled', 'failed']:
            # Log: Payment failed/rejected
            print(f"Payment {mercadopago_payment_id} for cuota {cuota_id} failed with status: {payment_status}")
            # Optionally, update cuota status if needed (e.g., back to 'pending' or 'overdue' if it was 'processing_mp')
            # For now, we only act on 'approved'.

        else: # Other statuses like 'pending', 'in_process'
            # Log: Payment in other state
            print(f"Payment {mercadopago_payment_id} for cuota {cuota_id} has status: {payment_status}")
            # You might want to set cuota.estado to something like 'processing_mp' here
            # and handle it in update_fee_status_after_payment or elsewhere.

        return "OK", 200

    except Exception as e:
        # Log unexpected error
        # Important to catch all exceptions to prevent MP from getting non-200 responses for valid reasons
        print(f"Unexpected error in MP webhook: {str(e)}")
        # Potentially rollback db.session if any operations were attempted and failed mid-way
        # db.session.rollback() # Be careful with rollback if some operations should persist even on error
        return "Internal Server Error", 500 # Or 200 if you want MP to stop retrying for this event


@cobranzas_bp.route('/reports/automatic-debit-candidates', methods=['GET', 'POST'])
@roles_required('admin', 'staff')
def list_automatic_debit_candidates():
    form = AutomaticDebitListFilterForm()
    candidates = []
    periodo_seleccionado = None

    if form.validate_on_submit():
        periodo_seleccionado = form.periodo.data
        try:
            candidates = db.session.query(
                Cuota, Professional
            ).join(Professional, Professional.id == Cuota.professional_id).filter(
                Cuota.periodo == periodo_seleccionado,
                Cuota.metodo_pago_preferido == 'debito_automatico',
                Cuota.estado.in_(['pending', 'overdue', 'partially_paid']) # Include partially_paid
            ).order_by(Professional.last_name, Professional.first_name).all()
            
            if not candidates:
                flash('No se encontraron candidatos para débito automático para el período seleccionado.', 'info')
            else:
                flash(f'{len(candidates)} candidatos encontrados para el período {periodo_seleccionado}.', 'success')
                
        except Exception as e:
            flash(f'Error al buscar candidatos: {str(e)}', 'danger')
            # Log error e

    return render_template('list_automatic_debit_candidates.html', 
                           form=form, 
                           candidates=candidates, 
                           periodo_seleccionado=periodo_seleccionado,
                           title='Candidatos para Débito Automático')


@cobranzas_bp.route('/reports/automatic-debit-candidates/export-csv')
@roles_required('admin', 'staff')
def export_automatic_debit_candidates_csv():
    periodo = request.args.get('periodo', None)
    if not periodo:
        flash('Por favor, especifique un período para exportar.', 'warning')
        return redirect(url_for('cobranzas.list_automatic_debit_candidates'))

    try:
        candidates_data = db.session.query(
            Professional.first_name,
            Professional.last_name,
            Professional.matricula,
            Professional.cbu,
            Professional.email,
            Cuota.periodo,
            (Cuota.monto_esperado - Cuota.monto_pagado).label('monto_adeudado') # Calculate amount due
        ).join(Professional, Professional.id == Cuota.professional_id).filter(
            Cuota.periodo == periodo,
            Cuota.metodo_pago_preferido == 'debito_automatico',
            Cuota.estado.in_(['pending', 'overdue', 'partially_paid'])
        ).order_by(Professional.last_name, Professional.first_name).all()

        if not candidates_data:
            flash(f'No hay candidatos para exportar para el período {periodo}.', 'info')
            return redirect(url_for('cobranzas.list_automatic_debit_candidates', periodo=periodo))

        # CSV Generation
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(["Nombre Profesional", "Apellido Profesional", "Matricula", "CBU", "Email Profesional", "Periodo Cuota", "Monto Adeudado"])
        
        for row in candidates_data:
            writer.writerow([
                row.first_name,
                row.last_name,
                row.matricula,
                row.cbu,
                row.email,
                row.periodo,
                str(row.monto_adeudado.quantize(Decimal('0.01'))) # Format Decimal to string
            ])
        
        output.seek(0)
        
        return Response(
            output,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment;filename=debitos_automaticos_{periodo.replace('-', '_')}.csv"}
        )

    except Exception as e:
        flash(f'Error al exportar CSV: {str(e)}', 'danger')
        # Log error e
        return redirect(url_for('cobranzas.list_automatic_debit_candidates', periodo=periodo))
