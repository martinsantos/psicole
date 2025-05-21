from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import Optional, Email, Length
# Assuming Professional model is in psicoLE.profesionales.models
# No direct import of Professional model here if we are just defining fields by name.

# These are the fields a professional can request changes for.
# Excludes core identifiers like first_name, last_name, matricula for this iteration.
EDITABLE_PROFESSIONAL_FIELDS = {
    'email': {'label': 'Email', 'validators': [Optional(), Email(), Length(max=120)], 'type': 'StringField'},
    'phone_number': {'label': 'Phone Number', 'validators': [Optional(), Length(max=20)], 'type': 'StringField'},
    'address': {'label': 'Address', 'validators': [Optional(), Length(max=200)], 'type': 'TextAreaField'},
    # Academic fields are view-only for now, but could be added here later
    # 'title': {'label': 'Title (e.g., Licenciado en Psicología)', 'validators': [Optional(), Length(max=100)], 'type': 'StringField'},
    # 'specialization': {'label': 'Specialization (e.g., Psicología Clínica)', 'validators': [Optional(), Length(max=100)], 'type': 'StringField'},
    # 'university': {'label': 'University', 'validators': [Optional(), Length(max=100)], 'type': 'StringField'},
    'cbu': {'label': 'CBU (Bank Account for Payments)', 'validators': [Optional(), Length(max=50)], 'type': 'StringField'},
}

class ProfileEditRequestForm(FlaskForm):
    # Fields will be added dynamically in the view or a helper based on EDITABLE_PROFESSIONAL_FIELDS
    # For example:
    # email = StringField('Email', validators=[Optional(), Email(), Length(max=120)])
    # phone_number = StringField('Phone Number', validators=[Optional(), Length(max=20)])
    # address = TextAreaField('Address', validators=[Optional(), Length(max=200)], render_kw={'rows':3})
    # cbu = StringField('CBU (Bank Account for Payments)', validators=[Optional(), Length(max=50)])
    
    submit = SubmitField('Submit Change Requests')

    def __init__(self, professional_data=None, *args, **kwargs):
        super(ProfileEditRequestForm, self).__init__(*args, **kwargs)
        
        for field_name, field_attrs in EDITABLE_PROFESSIONAL_FIELDS.items():
            field_type = getattr(FlaskForm, field_attrs['type'], StringField) # Default to StringField
            
            # Dynamically create the field and add it to the form
            # WTForms fields are typically defined at class level, but can be added to `self`
            # However, for validation and rendering, they need to be part of the class definition
            # or handled specially.
            # A common way is to add them before `super().__init__` using `setattr`.
            # This approach is a bit more complex than defining them directly if they are fixed.
            
            # For simplicity in this step, I'll assume fields are defined explicitly on the class for now,
            # or the view will handle populating fields based on EDITABLE_PROFESSIONAL_FIELDS.
            # If fields were added dynamically, they'd be like:
            # field = field_type(field_attrs['label'], validators=field_attrs['validators'])
            # setattr(self, field_name, field)

        if professional_data:
            # Populate form fields with existing data from the professional object
            for field_name in EDITABLE_PROFESSIONAL_FIELDS.keys():
                if hasattr(self, field_name) and hasattr(professional_data, field_name):
                    # getattr(self, field_name) gives the BoundField object.
                    # We need to set its .data attribute.
                    form_field = getattr(self, field_name)
                    form_field.data = getattr(professional_data, field_name)

# Explicitly define fields based on EDITABLE_PROFESSIONAL_FIELDS for clarity and standard WTForms usage
# This makes the dynamic part of __init__ for field creation redundant if fields are fixed.
# If fields were truly dynamic (e.g., from DB config), a different form generation strategy might be needed.
ProfileEditRequestForm.email = StringField(
    EDITABLE_PROFESSIONAL_FIELDS['email']['label'], 
    validators=EDITABLE_PROFESSIONAL_FIELDS['email']['validators']
)
ProfileEditRequestForm.phone_number = StringField(
    EDITABLE_PROFESSIONAL_FIELDS['phone_number']['label'],
    validators=EDITABLE_PROFESSIONAL_FIELDS['phone_number']['validators']
)
ProfileEditRequestForm.address = TextAreaField(
    EDITABLE_PROFESSIONAL_FIELDS['address']['label'],
    validators=EDITABLE_PROFESSIONAL_FIELDS['address']['validators'],
    render_kw={'rows': 3}
)
ProfileEditRequestForm.cbu = StringField(
    EDITABLE_PROFESSIONAL_FIELDS['cbu']['label'],
    validators=EDITABLE_PROFESSIONAL_FIELDS['cbu']['validators']
)

# For Document Upload
from flask_wtf.file import FileField, FileAllowed, FileRequired
from psicoLE.main import app # To access app.config for ALLOWED_EXTENSIONS

class DocumentUploadForm(FlaskForm):
    nombre_documento = StringField('Nombre del Documento', validators=[DataRequired(), Length(max=255)])
    tipo_documento = SelectField('Tipo de Documento', 
                                 choices=[
                                     ('', '-- Seleccione Tipo (Opcional) --'),
                                     ('CV', 'CV'), 
                                     ('Título', 'Título Académico'), 
                                     ('Certificado Curso', 'Certificado de Curso'), 
                                     ('Seguro Mala Praxis', 'Seguro de Mala Praxis'),
                                     ('DNI', 'DNI / Identificación'),
                                     ('Otro', 'Otro')
                                 ], 
                                 validators=[Optional()])
    document_file = FileField('Archivo', 
                              validators=[
                                  FileRequired(message="Debe seleccionar un archivo."),
                                  FileAllowed(app.config['ALLOWED_EXTENSIONS'], 
                                              message="Tipo de archivo no permitido. Permitidos: " + ", ".join(app.config['ALLOWED_EXTENSIONS']))
                              ])
    submit_upload = SubmitField('Subir Documento')
