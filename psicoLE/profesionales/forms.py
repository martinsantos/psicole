from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, DateField, TextAreaField, BooleanField
from wtforms.validators import DataRequired, Email, Optional, Length, ValidationError
from .models import Professional # Assuming Professional model is in .models

class ProfessionalForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=100)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=100)])
    matricula = StringField('Matrícula (License Number)', validators=[DataRequired(), Length(max=50)])
    status_matricula = SelectField('Status Matrícula', 
                                   choices=[
                                       ('active', 'Active'), 
                                       ('inactive', 'Inactive'), 
                                       ('pending', 'Pending Review'),
                                       ('suspended', 'Suspended')
                                   ], 
                                   validators=[DataRequired()])
    vigencia_matricula = DateField('Vigencia Matrícula (License Expiry Date)', 
                                   validators=[Optional()], format='%Y-%m-%d')
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    phone_number = StringField('Phone Number', validators=[Optional(), Length(max=20)])
    address = TextAreaField('Address', validators=[Optional(), Length(max=200)])
    title = StringField('Title (e.g., Licenciado en Psicología)', validators=[Optional(), Length(max=100)])
    specialization = StringField('Specialization (e.g., Psicología Clínica)', validators=[Optional(), Length(max=100)])
    university = StringField('University', validators=[Optional(), Length(max=100)])
    cbu = StringField('CBU (Bank Account for Payments)', validators=[Optional(), Length(max=50)])
    autoriza_debito_automatico = BooleanField('Autoriza Débito Automático en CBU informado?')
    
    submit = SubmitField('Save Professional')

    # We might need to pass the original matricula during edit to avoid self-collision
    def __init__(self, original_matricula=None, *args, **kwargs):
        super(ProfessionalForm, self).__init__(*args, **kwargs)
        self.original_matricula = original_matricula

    def validate_matricula(self, matricula):
        # If it's an edit and the matricula hasn't changed, it's valid.
        if self.original_matricula and self.original_matricula == matricula.data:
            return
        professional = Professional.query.filter_by(matricula=matricula.data).first()
        if professional:
            raise ValidationError('That matrícula is already registered. Please choose a different one.')

    def validate_email(self, email):
        # This validation assumes email should be unique across Professionals,
        # but User model also has email. If Professional.email must match User.email,
        # or if Professional can have an independent email, this needs clarification.
        # For now, assume Professional.email is unique among professionals.
        # If we are editing a professional, we need to make sure we are not conflicting with another professional's email.
        # This would require knowing the current professional's ID.
        # A simpler approach for now: if Professional is linked to a User, its email should match User.email.
        # This form doesn't handle User linking directly yet.
        # For now, basic unique check for Professional email.
        professional = Professional.query.filter(Professional.email == email.data)
        if self.original_matricula: # crude way to check if this is an edit form
            current_professional = Professional.query.filter_by(matricula=self.original_matricula).first()
            if current_professional:
                professional = professional.filter(Professional.id != current_professional.id)
        
        if professional.first():
            raise ValidationError('That email is already in use by another professional.')


class ProfessionalFilterForm(FlaskForm):
    search = StringField('Search by Name or Matrícula', validators=[Optional(), Length(max=100)])
    status_matricula = SelectField('Status Matrícula', 
                                   choices=[
                                       ('', 'All Statuses'), # Add an option for 'All'
                                       ('active', 'Active'), 
                                       ('inactive', 'Inactive'), 
                                       ('pending', 'Pending Review'),
                                       ('suspended', 'Suspended')
                                   ], 
                                   validators=[Optional()])
    specialization = StringField('Specialization', validators=[Optional(), Length(max=100)])
    university = StringField('University', validators=[Optional(), Length(max=100)])
    title = StringField('Title', validators=[Optional(), Length(max=100)])
    submit = SubmitField('Search/Filter')
    # clear = SubmitField('Clear Filters') # Optional: For a dedicated clear button - can be handled by a simple link


class SpecializationReportFilterForm(FlaskForm):
    status_matricula = SelectField('Status Matrícula', 
                                   choices=[ # Re-define choices or import if they are globally defined
                                       ('active', 'Active'), 
                                       ('inactive', 'Inactive'), 
                                       ('pending', 'Pending Review'),
                                       ('suspended', 'Suspended'),
                                       ('', 'All Statuses') # Allow selecting all
                                   ],
                                   default='active', # Default to 'active'
                                   validators=[Optional()]) # Optional, as we default
    submit = SubmitField('Generate Report')
