import math
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from sqlalchemy import or_, and_
from app import db

def calculate_booking_price(daily_rate, start_date, end_date):
    """Calculate the total price for a booking"""
    # Calculate number of days
    days = (end_date - start_date).days + 1
    
    # Calculate total price
    total_price = daily_rate * days
    
    # Apply discounts for longer bookings
    if days >= 7:
        # 10% discount for bookings of a week or more
        total_price = total_price * 0.9
    elif days >= 30:
        # 20% discount for bookings of a month or more
        total_price = total_price * 0.8
    
    # Round to 2 decimal places
    return round(total_price, 2)


def is_vehicle_available(vehicle_id, start_date, end_date):
    """Check if a vehicle is available for a given date range"""
    from models import Booking
    
    # Find any bookings that overlap with the requested period
    conflicting_bookings = Booking.query.filter(
        and_(
            Booking.vehicle_id == vehicle_id,
            Booking.status.in_(['pending', 'confirmed']),
            or_(
                and_(Booking.start_date <= start_date, Booking.end_date >= start_date),
                and_(Booking.start_date <= end_date, Booking.end_date >= end_date),
                and_(Booking.start_date >= start_date, Booking.end_date <= end_date)
            )
        )
    ).all()
    
    # If there are no conflicting bookings, the vehicle is available
    return len(conflicting_bookings) == 0


def initialize_admin():
    """Create admin user if it doesn't exist"""
    from models import User
    
    admin = User.query.filter_by(email='admin@vehiclebooking.com').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@vehiclebooking.com',
            first_name='Admin',
            last_name='User',
            phone='555-123-4567',
            is_admin=True
        )
        admin.set_password('adminpassword')
        
        db.session.add(admin)
        db.session.commit()
        print("Admin user created")
