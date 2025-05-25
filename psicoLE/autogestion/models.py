from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from database import db
from datetime import datetime

class DataChangeRequest(db.Model):
    __tablename__ = 'data_change_requests'
    id = Column(Integer, primary_key=True)
    professional_id = Column(Integer, ForeignKey('professionals.id'), nullable=False)
    field_name = Column(String(100), nullable=False) # e.g., 'email', 'phone_number', 'address'
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default='pending') # pending, approved, rejected
    requested_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)
    reviewer_id = Column(Integer, ForeignKey('users.id'), nullable=True) # admin/staff who reviewed
    review_comments = Column(Text, nullable=True)

    # Relationships will be set up in the application factory
    # to avoid circular imports

    def __init__(self, professional_id, field_name, new_value, old_value=None, status='pending', review_comments=None):
        self.professional_id = professional_id
        self.field_name = field_name
        self.old_value = old_value
        self.new_value = new_value
        self.status = status
        self.review_comments = review_comments
        # requested_at, reviewed_at, reviewer_id are set programmatically

    def __repr__(self):
        return f'<DataChangeRequest {self.id} for Prof {self.professional_id} - Field: {self.field_name} - Status: {self.status}>'

class DocumentoProfesional(db.Model):
    __tablename__ = 'documentos_profesionales'
    id = Column(Integer, primary_key=True)
    professional_id = Column(Integer, ForeignKey('professionals.id'), nullable=False)
    nombre_documento = Column(String(255), nullable=False)
    tipo_documento = Column(String(100), nullable=True) # e.g., 'CV', 'Título', 'Certificado Curso', 'Otro'
    fecha_carga = Column(DateTime, nullable=False, default=datetime.utcnow)
    archivo_filename = Column(String(255), nullable=False) # Secure filename
    archivo_path = Column(String(512), nullable=False) # Relative path like '<professional_id>/<secure_filename>'
    mimetype = Column(String(100), nullable=True)

    # Relationships
    professional = relationship('Professional', back_populates='documentos')

    def __init__(self, professional_id, nombre_documento, archivo_filename, archivo_path, tipo_documento=None, mimetype=None):
        self.professional_id = professional_id
        self.nombre_documento = nombre_documento
        self.tipo_documento = tipo_documento
        self.archivo_filename = archivo_filename
        self.archivo_path = archivo_path
        self.mimetype = mimetype
        # fecha_carga is default

    def __repr__(self):
        return f'<DocumentoProfesional {self.id} - Prof {self.professional_id} - {self.nombre_documento}>'
