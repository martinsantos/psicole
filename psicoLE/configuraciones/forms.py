from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, ValidationError
from .models import Configuration

class ConfigurationForm(FlaskForm):
    key = StringField('Key', 
                      validators=[DataRequired(), Length(max=100)], 
                      render_kw={'readonly': False}) # Default to not readonly
    value = StringField('Value', 
                        validators=[DataRequired(), Length(max=255)])
    description = TextAreaField('Description', 
                                validators=[Length(max=500)], 
                                render_kw={"rows": 3})
    submit = SubmitField('Save Configuration')

    def __init__(self, original_key=None, *args, **kwargs):
        super(ConfigurationForm, self).__init__(*args, **kwargs)
        self.original_key = original_key
        if original_key: # If editing, make key readonly
            self.key.render_kw['readonly'] = True

    def validate_key(self, key):
        # If it's an edit and the key hasn't changed (it shouldn't, as it's readonly), it's valid.
        if self.original_key and self.original_key == key.data:
            return
        # If it's a new key or somehow the key was changed during edit (should not happen with readonly)
        config_entry = Configuration.query.filter_by(key=key.data).first()
        if config_entry:
            raise ValidationError('That configuration key already exists. Please choose a different one.')
