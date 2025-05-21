from flask import Blueprint, render_template, request
from psicoLE.database import db
from psicoLE.auth.decorators import roles_required
from .forms import DateRangeForm, PaymentReportFiltersForm, ProfessionalReportForm
from psicoLE.cobranzas.models import Cuota, Pago
from psicoLE.profesionales.models import Professional
from sqlalchemy import or_, func, and_
from datetime import date, datetime
from decimal import Decimal

reports_bp = Blueprint('reports', __name__,
                       template_folder='templates/reports',
                       url_prefix='/reports')

@reports_bp.route('/overdue-fees', methods=['GET', 'POST'])
@roles_required('admin', 'staff')
def overdue_fees_report():
    form = DateRangeForm(request.form if request.method == 'POST' else request.args)
    query = Cuota.query.join(Professional).filter(
        or_(
            Cuota.estado == 'overdue',
            and_(Cuota.estado.in_(['pending', 'partially_paid']), Cuota.fecha_vencimiento < date.today())
        )
    )

    # Apply date filters if provided
    if form.validate_on_submit() or request.method == 'GET': # Process on GET for bookmarkable URLs too
        start_date = form.start_date.data
        end_date = form.end_date.data
        
        if start_date:
            query = query.filter(Cuota.fecha_vencimiento >= start_date)
        if end_date:
            query = query.filter(Cuota.fecha_vencimiento <= end_date)
            
    overdue_fees = query.order_by(Cuota.fecha_vencimiento.asc(), Professional.last_name).all()
    
    report_data = []
    total_overdue_amount = Decimal('0.00')
    for fee in overdue_fees:
        amount_due = fee.monto_esperado - fee.monto_pagado
        if amount_due > 0: # Only include if there's an actual amount due
            report_data.append({
                'professional_name': f"{fee.professional.last_name}, {fee.professional.first_name}",
                'matricula': fee.professional.matricula,
                'periodo': fee.periodo,
                'fecha_vencimiento': fee.fecha_vencimiento,
                'amount_due': amount_due
            })
            total_overdue_amount += amount_due
            
    return render_template('overdue_fees_report.html', 
                           report_data=report_data, 
                           total_overdue_amount=total_overdue_amount,
                           form=form, 
                           title='Overdue Fees Report')

# Placeholders for other reports
@reports_bp.route('/payments-received', methods=['GET', 'POST'])
@roles_required('admin', 'staff')
def payments_received_report():
    form = PaymentReportFiltersForm(request.form if request.method == 'POST' else request.args)
    query = Pago.query.join(Professional).options(db.joinedload(Pago.cuota)) # Eager load cuota

    if form.validate_on_submit() or request.method == 'GET': # Process on GET for bookmarkable URLs too
        start_date = form.start_date.data
        end_date = form.end_date.data
        payment_method = form.payment_method.data
        
        if start_date:
            # Ensure start_date is datetime for comparison with Pago.fecha_pago (DateTime)
            query = query.filter(Pago.fecha_pago >= datetime.combine(start_date, datetime.min.time()))
        if end_date:
            # Ensure end_date is datetime for comparison
            query = query.filter(Pago.fecha_pago <= datetime.combine(end_date, datetime.max.time()))
        if payment_method:
            query = query.filter(Pago.metodo_pago == payment_method)
            
    payments = query.order_by(Pago.fecha_pago.desc(), Professional.last_name).all()
    
    total_received_amount = sum(p.monto for p in payments if p.confirmado) # Sum only confirmed payments
    
    return render_template('payments_received_report.html', 
                           payments=payments, 
                           total_received_amount=total_received_amount,
                           form=form, 
                           title='Payments Received Report')

@reports_bp.route('/professional-account-status', methods=['GET', 'POST'])
@roles_required('admin', 'staff')
def professional_account_status_report():
    form = ProfessionalReportForm(request.form) # Handles both GET (empty) and POST
    professional_data = None
    fees = []
    payments = []
    overall_balance = Decimal('0.00')

    if request.method == 'POST' and form.validate_on_submit():
        professional = form.professional_id.data
        if professional:
            professional_data = professional
            fees = Cuota.query.filter_by(professional_id=professional.id).order_by(Cuota.periodo.desc()).all()
            payments = Pago.query.filter_by(professional_id=professional.id).order_by(Pago.fecha_pago.desc()).all()
            
            total_expected_fees = sum(fee.monto_esperado for fee in fees)
            total_confirmed_payments = sum(pago.monto for pago in payments if pago.confirmado)
            overall_balance = total_expected_fees - total_confirmed_payments
    
    # For GET request, form is empty, professional_data remains None, lists are empty.
    
    return render_template('professional_account_status_report.html',
                           form=form,
                           professional_data=professional_data,
                           fees=fees,
                           payments=payments,
                           overall_balance=overall_balance,
                           title='Professional Account Status Report')
