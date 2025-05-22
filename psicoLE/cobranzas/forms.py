from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, DecimalField, DateField, SelectField, HiddenField, BooleanField
from wtforms.validators import DataRequired, Optional, Regexp, ValidationError, NumberRange
from wtforms_sqlalchemy.fields import QuerySelectField
from psicoLE.profesionales.models import Professional
from psicoLE.configuraciones.utils import get_config_value
from datetime import date, datetime
from decimal import Decimal
import re

def get_active_professionals():
    # This function will be used by QuerySelectField to get choices.
    # It should return a query object.
    return Professional.query.filter_by(status_matricula='active').order_by(Professional.last_name, Professional.first_name)

class GenerateFeesForm(FlaskForm):
    periodo = StringField('Periodo (YYYY-MM)', 
                          validators=[DataRequired(), Regexp(r'^\d{4}-\d{2}$', message="Periodo must be in YYYY-MM format.")])
    fecha_vencimiento = DateField('Fecha de Vencimiento', 
                                  validators=[DataRequired()], 
                                  default=date.today) # Sensible default
    monto_general = DecimalField('Monto General de Cuota', 
                                 validators=[DataRequired()], 
                                 places=2)
    submit = SubmitField('Generate Monthly Fees')

    def __init__(self, *args, **kwargs):
        super(GenerateFeesForm, self).__init__(*args, **kwargs)
        if not self.monto_general.data: # Set default from config if not provided
            default_fee_str = get_config_value('default_monthly_fee_amount', '100.00')
            try:
                self.monto_general.data = DecimalField().process_formdata([default_fee_str])[0] # Process to Decimal
            except (ValueError, TypeError):
                self.monto_general.data = DecimalField().process_formdata(['100.00'])[0]


    def validate_periodo(self, periodo_field):
        if not re.match(r'^\d{4}-\d{2}$', periodo_field.data):
            raise ValidationError("Periodo must be in YYYY-MM format.")
        year, month = map(int, periodo_field.data.split('-'))
        if not (1 <= month <= 12):
            raise ValidationError("Month must be between 01 and 12.")
        if not (2020 <= year <= 2100): # Reasonable year range
            raise ValidationError("Year must be between 2020 and 2100.")


class FeeFilterForm(FlaskForm):
    professional_id = QuerySelectField('Professional', 
                                     query_factory=get_active_professionals,
                                     get_label=lambda p: f"{p.last_name}, {p.first_name} ({p.matricula})",
                                     allow_blank=True, 
                                     blank_text='-- All Professionals --',
                                     validators=[Optional()])
    periodo = StringField('Periodo (YYYY-MM)', 
                          validators=[Optional(), Regexp(r'^\d{4}-\d{2}$', message="Periodo must be in YYYY-MM format if provided.")])
    estado = SelectField('Estado', 
                         choices=[
                             ('', '-- All Statuses --'),
                             ('pending', 'Pending'),
                             ('paid', 'Paid'),
                             ('partially_paid', 'Partially Paid'),
                             ('overdue', 'Overdue'),
                             ('cancelled', 'Cancelled')
                         ], 
                         validators=[Optional()])
    submit = SubmitField('Filter Fees')

    def validate_periodo(self, periodo_field):
        if periodo_field.data: # Only validate if data is present
            if not re.match(r'^\d{4}-\d{2}$', periodo_field.data):
                raise ValidationError("Periodo must be in YYYY-MM format.")
            year, month = map(int, periodo_field.data.split('-'))
            if not (1 <= month <= 12):
                raise ValidationError("Month must be between 01 and 12.")
            if not (2020 <= year <= 2100): # Reasonable year range
                raise ValidationError("Year must be between 2020 and 2100.")

class ManualPaymentForm(FlaskForm):
    cuota_id = HiddenField('Cuota ID', validators=[Optional()]) # Optional for now, but usually linked
    professional_id = QuerySelectField('Professional',
                                        query_factory=get_active_professionals,
                                        get_label=lambda p: f"{p.last_name}, {p.first_name} ({p.matricula})",
                                        allow_blank=False, # Must select a professional if cuota_id is not set
                                        validators=[DataRequired()])
    monto_pagado = DecimalField('Monto Pagado', 
                                validators=[DataRequired(), NumberRange(min=0.01)], 
                                places=2)
    fecha_pago = DateField('Fecha de Pago', 
                           validators=[DataRequired()], 
                           default=date.today)
    metodo_pago = SelectField('Método de Pago', 
                              validators=[DataRequired()], 
                              choices=[
                                  ('cash', 'Cash (Efectivo)'),
                                  ('transfer', 'Transferencia Bancaria'),
                                  ('cheque', 'Cheque'),
                                  ('card_debit', 'Tarjeta de Débito'),
                                  ('card_credit', 'Tarjeta de Crédito'),
                                  ('gateway_mercadopago', 'MercadoPago (Gateway)'),
                                  ('other_manual', 'Otro Manual')
                              ])
    referencia_pago = StringField('Referencia de Pago (e.g., Transaction ID, Check No.)', 
                                  validators=[Optional(), Length(max=100)])
    confirmado = BooleanField('Pago Confirmado', default=True) # Usually true for manual entries
    submit = SubmitField('Record Payment')

    def __init__(self, cuota=None, *args, **kwargs):
        super(ManualPaymentForm, self).__init__(*args, **kwargs)
        if cuota:
            self.cuota_id.data = cuota.id
            self.professional_id.data = cuota.professional # Pre-select professional
            # Make professional_id field read-only or disabled if cuota is provided
            # self.professional_id.render_kw = {'disabled': True} # This makes it not submit data
            # A better way is to display it as text or ensure it's not changed by user.
            # For now, QuerySelectField will show it as selected.
            
            if not self.monto_pagado.data: # If form is fresh for this cuota
                remaining_balance = cuota.monto_esperado - cuota.monto_pagado
                if remaining_balance > Decimal('0.00'):
                    self.monto_pagado.data = remaining_balance
                else: # If already paid or overpaid, default to a small amount or full amount
                    self.monto_pagado.data = cuota.monto_esperado 
        
        # If professional_id is pre-selected (e.g. from cuota), filter QuerySelectField choices to only that one
        # This is tricky with QuerySelectField as it expects a query_factory.
        # A simpler approach for display: show professional name as text if cuota is set.
        # Or, if QuerySelectField must be used, ensure its data is correctly set and validated.
        # Current setup: it will be pre-selected if cuota.professional is in the list of active professionals.


class AutomaticDebitListFilterForm(FlaskForm):
    periodo = StringField(
        'Periodo (YYYY-MM)', 
        validators=[
            DataRequired(message="El campo Periodo es obligatorio."), 
            Regexp(r'^\d{4}-\d{2}$', message="El Periodo debe tener el formato YYYY-MM.")
        ],
        render_kw={"placeholder": "YYYY-MM"}
    )
    submit = SubmitField('Ver Candidatos para Débito Automático')
