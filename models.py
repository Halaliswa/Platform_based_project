from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='student') # student, facilitator, admin
    is_suspended = db.Column(db.Boolean, default=False)
     --- POPIA COMPLIANCE FIELDS ---
    popia_consent = db.Column(db.Boolean, default=False, nullable=False)
    consent_date = db.Column(db.DateTime, nullable=True)

    # Relationships
    user_registrations = db.relationship('Registration', backref='student', lazy=True)
    user_feedbacks = db.relationship('Feedback', backref='student', lazy=True)
    user_notifications = db.relationship('Notification', backref='recipient', lazy=True)

class Workshop(db.Model):
    __tablename__ = 'workshop'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    
    # --- UPDATED: Faculty Requirement ---
    # This matches the filter_by(faculty=...) in your app.py
    faculty = db.Column(db.String(100), nullable=False) 
    
    workshop_type = db.Column(db.String(20), default="In-Person") 
    venue = db.Column(db.String(100)) 
    online_link = db.Column(db.String(255), nullable=True)
    category = db.Column(db.String(50)) 
    level = db.Column(db.String(20)) 
    
    # Timing
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    
    # Capacity
    capacity = db.Column(db.Integer, nullable=False)
    
    # Ownership
    facilitator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    facilitator = db.relationship('User', backref='hosted_workshops')
    registrations = db.relationship('Registration', backref='workshop_ref', lazy=True)
    attendance_records = db.relationship('Attendance', backref='workshop_ref', lazy=True)
    feedbacks = db.relationship('Feedback', backref='workshop_ref', lazy=True)

    def is_over(self):
        """Logic to enable the feedback button only after the workshop ends."""
        combined_end = datetime.combine(self.date, self.end_time)
        return datetime.now() > combined_end

    def current_enrollment(self):
        return len(self.registrations)

class Registration(db.Model):
    __tablename__ = 'registration'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    workshop_id = db.Column(db.Integer, db.ForeignKey('workshop.id'), nullable=False)
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Registered') 
    
    # Access links
    user = db.relationship('User', backref='registration_entries')
    workshop = db.relationship('Workshop', backref='registration_entries')

class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    workshop_id = db.Column(db.Integer, db.ForeignKey('workshop.id'), nullable=False)
    marked_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Present')

    user = db.relationship('User', backref='attendance_history')

class Feedback(db.Model):
    __tablename__ = 'feedback'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    workshop_id = db.Column(db.Integer, db.ForeignKey('workshop.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False) 
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# --- NEW: Notification Model for Email/Broadcast tracking ---
class Notification(db.Model):
    __tablename__ = 'notification'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    workshop_id = db.Column(db.Integer, db.ForeignKey('workshop.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    workshop = db.relationship('Workshop', backref='notifications')
