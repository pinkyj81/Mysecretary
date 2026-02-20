from db_config import db
from datetime import datetime

class Schedule(db.Model):
    __tablename__ = 'secretary_schedule'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(200), nullable=False)
    schedule_type = db.Column('type', db.String(20), nullable=False, default='schedule')
    color = db.Column(db.String(20), nullable=False, default='#5A9FD4')
    description = db.Column(db.Text, nullable=True)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=True)
    is_completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'schedule_type': self.schedule_type,
            'color': self.color,
            'description': self.description,
            'start_date': self.start_date.strftime('%Y-%m-%d %H:%M') if self.start_date else None,
            'end_date': self.end_date.strftime('%Y-%m-%d %H:%M') if self.end_date else None,
            'is_completed': self.is_completed,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        }
