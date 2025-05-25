<<<<<<< HEAD
from flask import request, current_app
from flask_wtf import FlaskForm
from flask_babel import _, lazy_gettext as _l
from flask_login import current_user
from wtforms import (
    StringField, PasswordField, SubmitField, BooleanField, 
    TextAreaField, SelectField, HiddenField, IntegerField, RadioField
)
from wtforms.validators import (
    DataRequired, Email, EqualTo, Length, 
    ValidationError, Optional, Regexp, NumberRange
)
from .models import User, db, Role, SecurityQuestion, SecurityEvent
import pyotp
import re

class PasswordValidator:
    """Password validation helper class."""
    def __init__(self, message=None):
        if not message:
            message = _('La contraseña debe tener al menos 8 caracteres, incluyendo mayúsculas, minúsculas, números y caracteres especiales.')
        self.message = message

    def __call__(self, form, field):
        password = field.data
        if len(password) < 8:
            raise ValidationError(_('La contraseña debe tener al menos 8 caracteres.'))
        if not any(char.isdigit() for char in password):
            raise ValidationError(_('La contraseña debe contener al menos un número.'))
        if not any(char.isupper() for char in password):
            raise ValidationError(_('La contraseña debe contener al menos una letra mayúscula.'))
        if not any(char.islower() for char in password):
            raise ValidationError(_('La contraseña debe contener al menos una letra minúscula.'))
        if not any(not char.isalnum() for char in password):
            raise ValidationError(_('La contraseña debe contener al menos un carácter especial (ej. !@#$%^&*).'))

class RegistrationForm(FlaskForm):
    username = StringField(_l('Nombre de Usuario'), 
                         validators=[
                             DataRequired(_('Este campo es obligatorio')),
                             Length(min=4, max=64, message=_('El nombre de usuario debe tener entre 4 y 64 caracteres')),
                             Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0,
                                  _('El nombre de usuario solo puede contener letras, números, puntos o guiones bajos'))
                         ])
    email = StringField(_l('Correo Electrónico'),
                       validators=[
                           DataRequired(_('Este campo es obligatorio')),
                           Email(_('Ingresa un correo electrónico válido')),
                           Length(max=120)
                       ])
    password = PasswordField(_l('Contraseña'),
                           validators=[
                               DataRequired(_('La contraseña es obligatoria')),
                               Length(min=8, message=_('La contraseña debe tener al menos 8 caracteres')),
                               EqualTo('confirm_password', message=_('Las contraseñas deben coincidir')),
                               PasswordValidator()
                           ])
    confirm_password = PasswordField(_l('Confirmar Contraseña'),
                                   validators=[DataRequired(_('Confirma tu contraseña'))])
    accept_tos = BooleanField(_l('Acepto los Términos de Servicio'), 
                             validators=[DataRequired(_('Debes aceptar los términos de servicio'))])
    submit = SubmitField(_l('Registrarse'))
=======
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from .models import User

class RegistrationForm(FlaskForm):
    username = StringField('Username', 
                           validators=[DataRequired(), Length(min=4, max=25)])
    email = StringField('Email', 
                        validators=[DataRequired(), Email()])
    password = PasswordField('Password', 
                             validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', 
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')
>>>>>>> 1eca9da5ea75796c688eecc7b35bab563ae145b2

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
<<<<<<< HEAD
            raise ValidationError(_('Este nombre de usuario ya está en uso. Por favor, elige otro.'))
=======
            raise ValidationError('That username is taken. Please choose a different one.')
>>>>>>> 1eca9da5ea75796c688eecc7b35bab563ae145b2

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
<<<<<<< HEAD
            raise ValidationError(_('Este correo electrónico ya está registrado. Por favor, utiliza otro o inicia sesión.'))

class LoginForm(FlaskForm):
    username = StringField(_l('Usuario o Correo Electrónico'), 
                         validators=[
                             DataRequired(_('Este campo es obligatorio')), 
                             Length(min=4, max=120, message=_('El usuario debe tener entre 4 y 120 caracteres'))
                         ],
                         render_kw={"placeholder": _l("Usuario o correo electrónico")})
    password = PasswordField(_l('Contraseña'), 
                           validators=[
                               DataRequired(_('La contraseña es obligatoria')),
                               Length(min=1, max=128)
                           ],
                           render_kw={"placeholder": _l("Contraseña")})
    remember_me = BooleanField(_l('Recuérdame'), default=False)
    submit = SubmitField(_l('Iniciar Sesión'))
    
    def __init__(self, *args, **kwargs):
        super(LoginForm, self).__init__(*args, **kwargs)
        self.user = None
        
    def validate(self, extra_validators=None):
        initial_validation = super(LoginForm, self).validate(extra_validators)
        if not initial_validation:
            return False
            
        # Check if user exists
        self.user = User.query.filter(
            (User.username == self.username.data) | 
            (User.email == self.username.data)
        ).first()
        
        if not self.user:
            self.username.errors.append(_('Usuario o correo electrónico no encontrado.'))
            return False
            
        # Check if user is active
        if not self.user.is_active:
            self.username.errors.append(_('Esta cuenta ha sido desactivada. Contacta al administrador.'))
            return False
            
        # Check password
        if not self.user.check_password(self.password.data):
            self.password.errors.append(_('Contraseña incorrecta. Inténtalo de nuevo.'))
            return False
            
        return True


class ResetPasswordRequestForm(FlaskForm):
    email = StringField(_l('Correo Electrónico'), 
                       validators=[
                           DataRequired(_('Este campo es obligatorio')), 
                           Email(_('Ingresa un correo electrónico válido')),
                           Length(max=120)
                       ],
                       render_kw={"placeholder": _l("tucorreo@ejemplo.com")})
    submit = SubmitField(_l('Solicitar Restablecimiento de Contraseña'))
    
    def __init__(self, *args, **kwargs):
        super(ResetPasswordRequestForm, self).__init__(*args, **kwargs)
        self.user = None
    
    def validate_email(self, email):
        self.user = User.query.filter_by(email=email.data).first()
        if self.user is None:
            raise ValidationError(_('No existe ninguna cuenta con este correo electrónico.'))
        if not self.user.is_active:
            raise ValidationError(_('Esta cuenta ha sido desactivada. Contacta al administrador.'))


class ResetPasswordForm(FlaskForm):
    password = PasswordField(_l('Nueva Contraseña'), 
                           validators=[
                               DataRequired(_('La contraseña es obligatoria')),
                               Length(min=8, max=128, message=_('La contraseña debe tener entre 8 y 128 caracteres')),
                               EqualTo('confirm_password', message=_('Las contraseñas deben coincidir')),
                               PasswordValidator()
                           ],
                           render_kw={
                               "placeholder": _l("Nueva contraseña"),
                               "autocomplete": "new-password"
                           })
    confirm_password = PasswordField(_l('Confirmar Contraseña'),
                                   validators=[DataRequired(_('Confirma tu contraseña'))],
                                   render_kw={
                                       "placeholder": _l("Confirma tu nueva contraseña"),
                                       "autocomplete": "new-password"
                                   })
    submit = SubmitField(_l('Restablecer Contraseña'))


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField(_l('Contraseña Actual'),
                                   validators=[
                                       DataRequired(_('Ingresa tu contraseña actual')),
                                       Length(min=1, max=128)
                                   ],
                                   render_kw={
                                       "placeholder": _l("Contraseña actual"),
                                       "autocomplete": "current-password"
                                   })
    new_password = PasswordField(_l('Nueva Contraseña'),
                               validators=[
                                   DataRequired(_('La nueva contraseña es obligatoria')),
                                   Length(min=8, max=128, message=_('La contraseña debe tener entre 8 y 128 caracteres')),
                                   EqualTo('confirm_password', message=_('Las contraseñas deben coincidir')),
                                   PasswordValidator()
                               ],
                               render_kw={
                                   "placeholder": _l("Nueva contraseña"),
                                   "autocomplete": "new-password"
                               })
    confirm_password = PasswordField(_l('Confirmar Nueva Contraseña'),
                                   validators=[DataRequired(_('Confirma tu nueva contraseña'))],
                                   render_kw={
                                       "placeholder": _l("Confirma tu nueva contraseña"),
                                       "autocomplete": "new-password"
                                   })
    submit = SubmitField(_l('Cambiar Contraseña'))
    
    def __init__(self, user, *args, **kwargs):
        super(ChangePasswordForm, self).__init__(*args, **kwargs)
        self.user = user
    
    def validate_current_password(self, field):
        if not self.user.check_password(field.data):
            raise ValidationError(_('La contraseña actual es incorrecta.'))
    
    def validate_new_password(self, field):
        if field.data == self.current_password.data:
            raise ValidationError(_('La nueva contraseña debe ser diferente a la actual.'))


class ChangeEmailRequestForm(FlaskForm):
    email = StringField(_l('Nuevo Correo Electrónico'),
                       validators=[
                           DataRequired(_('El correo electrónico es obligatorio')),
                           Email(_('Ingresa un correo electrónico válido')),
                           Length(max=120, message=_('El correo electrónico no puede tener más de 120 caracteres'))
                       ],
                       render_kw={
                           "placeholder": _l("nuevo@ejemplo.com"),
                           "autocomplete": "email"
                       })
    password = PasswordField(_l('Contraseña Actual'),
                           validators=[
                               DataRequired(_('Ingresa tu contraseña actual para confirmar')),
                               Length(min=1, max=128)
                           ],
                           render_kw={
                               "placeholder": _l("Tu contraseña actual"),
                               "autocomplete": "current-password"
                           })
    submit = SubmitField(_l('Solicitar Cambio de Correo'))
    
    def __init__(self, user, *args, **kwargs):
        super(ChangeEmailRequestForm, self).__init__(*args, **kwargs)
        self.user = user
    
    def validate_email(self, email):
        if email.data == self.user.email:
            raise ValidationError(_('Este ya es tu correo electrónico actual.'))
            
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError(_('Este correo electrónico ya está en uso. Por favor, utiliza otro.'))
    
    def validate_password(self, field):
        if not self.user.check_password(field.data):
            raise ValidationError(_('La contraseña es incorrecta.'))


class ProfileForm(FlaskForm):
    """Form for editing user profile information."""
    first_name = StringField(_l('Nombre'),
                           validators=[
                               Optional(),
                               Length(max=50, message=_('El nombre no puede tener más de 50 caracteres'))
                           ],
                           render_kw={"placeholder": _l("Tu nombre")})
    last_name = StringField(_l('Apellido'),
                          validators=[
                              Optional(),
                              Length(max=50, message=_('El apellido no puede tener más de 50 caracteres'))
                          ],
                          render_kw={"placeholder": _l("Tu apellido")})
    bio = TextAreaField(_l('Biografía'),
                       validators=[
                           Optional(),
                           Length(max=500, message=_('La biografía no puede tener más de 500 caracteres'))
                       ],
                       render_kw={
                           "placeholder": _l("Cuéntanos algo sobre ti..."),
                           "rows": 4
                       })
    location = StringField(_l('Ubicación'),
                         validators=[
                             Optional(),
                             Length(max=100, message=_('La ubicación no puede tener más de 100 caracteres'))
                         ],
                         render_kw={"placeholder": _l("Ciudad, País")})
    website = StringField(_l('Sitio Web'),
                        validators=[
                            Optional(),
                            Length(max=200, message=_('La URL no puede tener más de 200 caracteres')),
                            Regexp('^https?://.+', message=_('Ingresa una URL válida (debe comenzar con http:// o https://)'))
                        ],
                        render_kw={
                            "placeholder": _l("https://tusitio.com"),
                            "autocomplete": "url"
                        })
    submit = SubmitField(_l('Actualizar Perfil'))
    
    def __init__(self, user, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)
        self.user = user
    
    def validate_website(self, field):
        if field.data and not field.data.startswith(('http://', 'https://')):
            field.data = 'http://' + field.data


class MFAVerifyForm(FlaskForm):
    """Form for verifying MFA codes."""
    code = StringField(_l('Código de verificación'),
                      validators=[
                          DataRequired(_('El código de verificación es obligatorio')),
                          Length(min=6, max=6, message=_('El código debe tener 6 dígitos')),
                          Regexp('^\d{6}$', message=_('El código debe contener solo números'))
                      ],
                      render_kw={
                          'placeholder': _('123456'),
                          'autocomplete': 'one-time-code',
                          'inputmode': 'numeric',
                          'pattern': '\d{6}'
                      })
    submit = SubmitField(_l('Verificar'))


class MFASetupForm(FlaskForm):
    """Form for setting up MFA."""
    code = StringField(_l('Código de verificación'),
                      validators=[
                          DataRequired(_('El código de verificación es obligatorio')),
                          Length(min=6, max=6, message=_('El código debe tener 6 dígitos')),
                          Regexp('^\d{6}$', message=_('El código debe contener solo números'))
                      ],
                      render_kw={
                          'placeholder': _('Ingresa el código de tu aplicación de autenticación'),
                          'autocomplete': 'one-time-code',
                          'inputmode': 'numeric',
                          'pattern': '\d{6}'
                      })
    submit = SubmitField(_l('Activar autenticación en dos pasos'))


class MFARecoveryForm(FlaskForm):
    """Form for MFA recovery using backup codes."""
    recovery_code = StringField(_l('Código de recuperación'),
                               validators=[
                                   DataRequired(_('El código de recuperación es obligatorio')),
                                   Length(min=12, max=16, message=_('Código de recuperación inválido'))
                               ],
                               render_kw={
                                   'placeholder': _('Ej: abcd-efgh-ijkl'),
                                   'autocomplete': 'off',
                                   'autocapitalize': 'off',
                                   'autocorrect': 'off',
                                   'spellcheck': 'false'
                               })
    submit = SubmitField(_l('Usar código de recuperación'))


class SecurityQuestionsForm(FlaskForm):
    """Form for setting up security questions."""
    question1 = SelectField(_l('Pregunta de seguridad 1'),
                           validators=[DataRequired(_('Selecciona una pregunta de seguridad'))],
                           coerce=int)
    answer1 = StringField(_l('Respuesta 1'),
                         validators=[
                             DataRequired(_('La respuesta es obligatoria')),
                             Length(min=2, max=100, message=_('La respuesta debe tener entre 2 y 100 caracteres'))
                         ],
                         render_kw={
                             'autocomplete': 'off',
                             'autocapitalize': 'off',
                             'autocorrect': 'off',
                             'spellcheck': 'false'
                         })
    question2 = SelectField(_l('Pregunta de seguridad 2'),
                           validators=[DataRequired(_('Selecciona una pregunta de seguridad'))],
                           coerce=int)
    answer2 = StringField(_l('Respuesta 2'),
                         validators=[
                             DataRequired(_('La respuesta es obligatoria')),
                             Length(min=2, max=100, message=_('La respuesta debe tener entre 2 y 100 caracteres'))
                         ],
                         render_kw={
                             'autocomplete': 'off',
                             'autocapitalize': 'off',
                             'autocorrect': 'off',
                             'spellcheck': 'false'
                         })
    submit = SubmitField(_l('Guardar preguntas de seguridad'))

    def __init__(self, *args, **kwargs):
        super(SecurityQuestionsForm, self).__init__(*args, **kwargs)
        # Populate question choices from database
        questions = SecurityQuestion.query.order_by('question').all()
        choices = [(q.id, q.question) for q in questions]
        self.question1.choices = choices
        self.question2.choices = choices

    def validate(self, extra_validators=None):
        if not super().validate():
            return False
        
        if self.question1.data == self.question2.data:
            self.question2.errors.append(_('Debes seleccionar dos preguntas diferentes'))
            return False
            
        return True


class VerifySecurityQuestionsForm(FlaskForm):
    """Form for verifying security questions."""
    answer1 = StringField(_l('Respuesta 1'),
                         validators=[
                             DataRequired(_('La respuesta es obligatoria')),
                             Length(min=2, max=100)
                         ],
                         render_kw={
                             'autocomplete': 'off',
                             'autocapitalize': 'off',
                             'autocorrect': 'off',
                             'spellcheck': 'false'
                         })
    answer2 = StringField(_l('Respuesta 2'),
                         validators=[
                             DataRequired(_('La respuesta es obligatoria')),
                             Length(min=2, max=100)
                         ],
                         render_kw={
                             'autocomplete': 'off',
                             'autocapitalize': 'off',
                             'autocorrect': 'off',
                             'spellcheck': 'false'
                         })
    submit = SubmitField(_l('Verificar respuestas'))


class SessionManagementForm(FlaskForm):
    """Form for managing user sessions."""
    session_id = HiddenField(validators=[DataRequired()])
    submit = SubmitField(_l('Cerrar sesión'))


class DeviceAuthorizationForm(FlaskForm):
    """Form for authorizing new devices."""
    device_name = StringField(_l('Nombre del dispositivo'),
                             validators=[
                                 DataRequired(_('El nombre del dispositivo es obligatorio')),
                                 Length(max=100, message=_('El nombre no puede tener más de 100 caracteres'))
                             ],
                             render_kw={
                                 'placeholder': _('Ej: Mi teléfono personal')
                             })
    remember_device = BooleanField(_l('Recordar este dispositivo'), default=False)
    submit = SubmitField(_l('Autorizar dispositivo'))
=======
            raise ValidationError('That email is already registered. Please choose a different one.')

class LoginForm(FlaskForm):
    username = StringField('Username', 
                           validators=[DataRequired(), Length(min=4, max=25)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')
>>>>>>> 1eca9da5ea75796c688eecc7b35bab563ae145b2
