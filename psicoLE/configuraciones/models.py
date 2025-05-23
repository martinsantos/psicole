from database import db # Corrected import
from sqlalchemy import Column, Integer, String, Text

class Configuration(db.Model):
    __tablename__ = 'configurations'
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(String(255), nullable=False)
    description = Column(Text)

    def __init__(self, key, value, description=None):
        self.key = key
        self.value = value
        self.description = description

    def __repr__(self):
        return f'<Configuration {self.key}: {self.value}>'
