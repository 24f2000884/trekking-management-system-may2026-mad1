# models.py
from app import db
from datetime import datetime

class User(db.Model):
    __tablename__ = 'user'
    id= db.Column(db.Integer, primary_key=True)
    username=db.Column(db.String(80), unique=True, nullable=False)
    email=db.Column(db.String(120), unique=True, nullable=False)
    password_hash= db.Column(db.String(200), nullable=False)
    role=db.Column(db.String(20), nullable=False)  
    is_active=db.Column(db.Boolean, default=True)
    is_blacklisted=db.Column(db.Boolean, default=False)
    created_at= db.Column(db.DateTime, default=datetime.utcnow)
    
    bookings= db.relationship('Booking', backref='user', lazy=True)
    staff_profile= db.relationship('StaffProfile', backref='user', uselist=False)

class Trek(db.Model):
    __tablename__ = 'trek'
    id= db.Column(db.Integer, primary_key=True)
    name= db.Column(db.String(120), nullable=False)
    location= db.Column(db.String(120), nullable=False)
    difficulty= db.Column(db.String(20), nullable=False)
    duration_days= db.Column(db.Integer, nullable=False)
    available_slots=db.Column(db.Integer, nullable=False)
    total_slots=db.Column(db.Integer, nullable=False)
    description=db.Column(db.Text)
    status=db.Column(db.String(20), default='Pending')
    start_date=db.Column(db.Date)
    end_date=db.Column(db.Date)
    created_at=db.Column(db.DateTime, default=datetime.utcnow)

    bookings        = db.relationship('Booking', backref='trek', lazy=True)
    assignments     = db.relationship('TrekStaffAssignment', backref='trek', lazy=True)

class Booking(db.Model):
    __tablename__ = 'booking'
    id=db.Column(db.Integer, primary_key=True)
    user_id=db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    trek_id =db.Column(db.Integer, db.ForeignKey('trek.id'), nullable=False)
    booking_date=db.Column(db.DateTime, default=datetime.utcnow)
    status=db.Column(db.String(20), default='Booked')
    payment_status=db.Column(db.String(20), default='Pending')

class StaffProfile(db.Model):
    __tablename__ = 'staff_profile'
    id=db.Column(db.Integer, primary_key=True)
    user_id=db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name=db.Column(db.String(120), nullable=False)
    contact=db.Column(db.String(20))
    bio=db.Column(db.Text)
    status=db.Column(db.String(20), default='Active')

class TrekStaffAssignment(db.Model):
    __tablename__ ='trek_staff_assignment'
    id=db.Column(db.Integer, primary_key=True)
    trek_id=db.Column(db.Integer, db.ForeignKey('trek.id'), nullable=False)
    staff_id=db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
