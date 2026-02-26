from app import db
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSON
import json


class PDFReport(db.Model):
    __tablename__ = 'pdf_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    source_pdf = db.Column(db.String(500), nullable=False)
    extracted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    payload = db.Column(db.JSON, nullable=False)  # Stores the entire extracted JSON
    report_type = db.Column(db.String(50), nullable=True)  # 'infrastructure' or 'code_analysis'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'source_pdf': self.source_pdf,
            'extracted_at': self.extracted_at.isoformat(),
            'report_type': self.report_type,
            'payload': self.payload,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }
