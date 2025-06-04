import json
from datetime import datetime, timedelta
from flask import render_template, url_for, flash, redirect, request, session, jsonify
from flask_login import login_user, current_user, logout_user, login_required
from sqlalchemy import or_, and_
from app import db
from models import User, Vehicle, Booking
from forms import (
    RegistrationForm, LoginForm, VehicleForm, BookingForm, 
    SearchForm, BookingStatusForm
)
from utils import calculate_booking_price, is_vehicle_available


def register_routes(app):
    # User authentication routes
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('index'))
            
        form = RegistrationForm()
        if form.validate_on_submit():
            user = User(
                username=form.username.data,
                email=form.email.data,
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                phone=form.phone.data
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash('Your account has been created! You can now log in.', 'success')
            return redirect(url_for('login'))
            
        return render_template('register.html', title='Register', form=form)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('index'))
            
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data).first()
            if user and user.check_password(form.password.data):
                login_user(user, remember=form.remember.data)
                next_page = request.args.get('next')
                flash('Login successful!', 'success')
                return redirect(next_page if next_page else url_for('index'))
            else:
                flash('Login unsuccessful. Please check email and password.', 'danger')
                
        return render_template('login.html', title='Login', form=form)

    @app.route('/logout')
    def logout():
        logout_user()
        flash('You have been logged out.', 'info')
        return redirect(url_for('index'))

    # Main routes
    @app.route('/')
    def index():
        # Get a few featured vehicles to display on the homepage
        featured_vehicles = Vehicle.query.filter_by(is_available=True).limit(3).all()
        return render_template('index.html', title='Home', vehicles=featured_vehicles)

    @app.route('/vehicles', methods=['GET', 'POST'])
    def vehicles():
        form = SearchForm()
        
        # Get all vehicles by default
        query = Vehicle.query.filter_by(is_available=True)
        
        if form.validate_on_submit() or request.method == 'GET' and request.args:
            # Handle form submission or GET parameters
            if request.method == 'POST':
                data = form.data
            else:
                data = request.args
                
            # Apply filters
            if data.get('vehicle_type'):
                query = query.filter(Vehicle.vehicle_type == data.get('vehicle_type'))
                
            if data.get('max_price'):
                query = query.filter(Vehicle.daily_rate <= float(data.get('max_price')))
                
            if data.get('capacity'):
                query = query.filter(Vehicle.capacity >= int(data.get('capacity')))
                
            # If dates are provided, check availability
            if data.get('start_date') and data.get('end_date'):
                start_date = datetime.strptime(data.get('start_date'), '%Y-%m-%d') if isinstance(data.get('start_date'), str) else data.get('start_date')
                end_date = datetime.strptime(data.get('end_date'), '%Y-%m-%d') if isinstance(data.get('end_date'), str) else data.get('end_date')
                
                # Store dates in session for booking process
                session['start_date'] = start_date.strftime('%Y-%m-%d')
                session['end_date'] = end_date.strftime('%Y-%m-%d')
                
                # Find unavailable vehicles during this period
                unavailable_bookings = Booking.query.filter(
                    and_(
                        Booking.status.in_(['pending', 'confirmed']),
                        or_(
                            and_(Booking.start_date <= start_date, Booking.end_date >= start_date),
                            and_(Booking.start_date <= end_date, Booking.end_date >= end_date),
                            and_(Booking.start_date >= start_date, Booking.end_date <= end_date)
                        )
                    )
                ).all()
                
                unavailable_vehicle_ids = [booking.vehicle_id for booking in unavailable_bookings]
                if unavailable_vehicle_ids:
                    query = query.filter(~Vehicle.id.in_(unavailable_vehicle_ids))
        
        vehicles = query.all()
        return render_template('vehicles.html', title='Available Vehicles', vehicles=vehicles, form=form)

    @app.route('/vehicle/<int:vehicle_id>')
    def vehicle_detail(vehicle_id):
        vehicle = Vehicle.query.get_or_404(vehicle_id)
        return render_template('vehicle_detail.html', title=f'{vehicle.make} {vehicle.model}', vehicle=vehicle)

    @app.route('/book/<int:vehicle_id>', methods=['GET', 'POST'])
    @login_required
    def book_vehicle(vehicle_id):
        vehicle = Vehicle.query.get_or_404(vehicle_id)
        
        if not vehicle.is_available:
            flash('This vehicle is not available for booking.', 'danger')
            return redirect(url_for('vehicles'))
        
        form = BookingForm()
        form.vehicle_id.data = vehicle.id
        
        # Pre-fill dates from session if available
        if session.get('start_date') and session.get('end_date'):
            form.start_date.data = datetime.strptime(session.get('start_date'), '%Y-%m-%d')
            form.end_date.data = datetime.strptime(session.get('end_date'), '%Y-%m-%d')
        
        if form.validate_on_submit():
            start_date = form.start_date.data
            end_date = form.end_date.data
            
            # Check if the vehicle is available for these dates
            if not is_vehicle_available(vehicle.id, start_date, end_date):
                flash('Sorry, this vehicle is not available for the selected dates.', 'danger')
                return redirect(url_for('book_vehicle', vehicle_id=vehicle.id))
            
            # Calculate the total price
            total_price = calculate_booking_price(vehicle.daily_rate, start_date, end_date)
            
            # Save payment information as JSON string
            payment_info = json.dumps({
                'card_number': f"xxxx-xxxx-xxxx-{form.card_number.data[-4:]}",  # Store only last 4 digits
                'card_holder': form.card_holder.data,
                'expiry_date': form.expiry_date.data
            })
            
            # Create new booking
            booking = Booking(
                user_id=current_user.id,
                vehicle_id=vehicle.id,
                start_date=start_date,
                end_date=end_date,
                total_price=total_price,
                status='pending',
                payment_info=payment_info,
                notes=form.notes.data
            )
            
            db.session.add(booking)
            db.session.commit()
            
            flash('Your booking has been submitted and is pending confirmation.', 'success')
            return redirect(url_for('my_bookings'))
        
        return render_template('booking.html', title='Book a Vehicle', form=form, vehicle=vehicle)

    @app.route('/my-bookings')
    @login_required
    def my_bookings():
        bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.created_at.desc()).all()
        return render_template('my_bookings.html', title='My Bookings', bookings=bookings)

    @app.route('/cancel-booking/<int:booking_id>', methods=['POST'])
    @login_required
    def cancel_booking(booking_id):
        booking = Booking.query.get_or_404(booking_id)
        
        # Ensure the booking belongs to the current user
        if booking.user_id != current_user.id:
            flash('You do not have permission to cancel this booking.', 'danger')
            return redirect(url_for('my_bookings'))
        
        # Only pending or confirmed bookings can be cancelled
        if booking.status not in ['pending', 'confirmed']:
            flash('This booking cannot be cancelled.', 'danger')
            return redirect(url_for('my_bookings'))
        
        booking.status = 'cancelled'
        db.session.commit()
        
        flash('Your booking has been cancelled.', 'success')
        return redirect(url_for('my_bookings'))

    # Admin routes
    @app.route('/admin/dashboard')
    @login_required
    def admin_dashboard():
        if not current_user.is_admin:
            flash('Access denied. You must be an administrator.', 'danger')
            return redirect(url_for('index'))
        
        # Get counts for dashboard
        vehicle_count = Vehicle.query.count()
        user_count = User.query.count()
        pending_bookings = Booking.query.filter_by(status='pending').count()
        active_bookings = Booking.query.filter_by(status='confirmed').count()
        
        # Get recent bookings
        recent_bookings = Booking.query.order_by(Booking.created_at.desc()).limit(5).all()
        
        return render_template('admin/dashboard.html', title='Admin Dashboard',
                               vehicle_count=vehicle_count, user_count=user_count,
                               pending_bookings=pending_bookings, active_bookings=active_bookings,
                               recent_bookings=recent_bookings)

    @app.route('/admin/vehicles', methods=['GET'])
    @login_required
    def admin_vehicles():
        if not current_user.is_admin:
            flash('Access denied. You must be an administrator.', 'danger')
            return redirect(url_for('index'))
        
        vehicles = Vehicle.query.all()
        return render_template('admin/manage_vehicles.html', title='Manage Vehicles', vehicles=vehicles)

    @app.route('/admin/vehicle/add', methods=['GET', 'POST'])
    @login_required
    def add_vehicle():
        if not current_user.is_admin:
            flash('Access denied. You must be an administrator.', 'danger')
            return redirect(url_for('index'))
        
        form = VehicleForm()
        if form.validate_on_submit():
            vehicle = Vehicle(
                make=form.make.data,
                model=form.model.data,
                year=form.year.data,
                license_plate=form.license_plate.data,
                vehicle_type=form.vehicle_type.data,
                capacity=form.capacity.data,
                color=form.color.data,
                daily_rate=form.daily_rate.data,
                is_available=form.is_available.data,
                description=form.description.data,
                features=form.features.data
            )
            
            db.session.add(vehicle)
            db.session.commit()
            
            flash('Vehicle has been added successfully.', 'success')
            return redirect(url_for('admin_vehicles'))
        
        return render_template('admin/manage_vehicles.html', title='Add Vehicle', form=form)

    @app.route('/admin/vehicle/<int:vehicle_id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_vehicle(vehicle_id):
        if not current_user.is_admin:
            flash('Access denied. You must be an administrator.', 'danger')
            return redirect(url_for('index'))
        
        vehicle = Vehicle.query.get_or_404(vehicle_id)
        form = VehicleForm(obj=vehicle)
        
        if form.validate_on_submit():
            form.populate_obj(vehicle)
            db.session.commit()
            
            flash('Vehicle has been updated successfully.', 'success')
            return redirect(url_for('admin_vehicles'))
        
        return render_template('admin/manage_vehicles.html', title='Edit Vehicle', form=form, vehicle=vehicle)

    @app.route('/admin/vehicle/<int:vehicle_id>/delete', methods=['POST'])
    @login_required
    def delete_vehicle(vehicle_id):
        if not current_user.is_admin:
            flash('Access denied. You must be an administrator.', 'danger')
            return redirect(url_for('index'))
        
        vehicle = Vehicle.query.get_or_404(vehicle_id)
        
        # Check if vehicle has any bookings
        if vehicle.bookings:
            flash('Cannot delete vehicle with existing bookings.', 'danger')
            return redirect(url_for('admin_vehicles'))
        
        db.session.delete(vehicle)
        db.session.commit()
        
        flash('Vehicle has been deleted successfully.', 'success')
        return redirect(url_for('admin_vehicles'))

    @app.route('/admin/bookings')
    @login_required
    def admin_bookings():
        if not current_user.is_admin:
            flash('Access denied. You must be an administrator.', 'danger')
            return redirect(url_for('index'))
        
        # Filter bookings by status if requested
        status = request.args.get('status')
        if status:
            bookings = Booking.query.filter_by(status=status).order_by(Booking.created_at.desc()).all()
        else:
            bookings = Booking.query.order_by(Booking.created_at.desc()).all()
        
        return render_template('admin/manage_bookings.html', title='Manage Bookings', bookings=bookings)

    @app.route('/admin/booking/<int:booking_id>', methods=['GET', 'POST'])
    @login_required
    def manage_booking(booking_id):
        if not current_user.is_admin:
            flash('Access denied. You must be an administrator.', 'danger')
            return redirect(url_for('index'))
        
        booking = Booking.query.get_or_404(booking_id)
        form = BookingStatusForm(obj=booking)
        
        if form.validate_on_submit():
            booking.status = form.status.data
            booking.notes = form.notes.data
            db.session.commit()
            
            flash('Booking status has been updated.', 'success')
            return redirect(url_for('admin_bookings'))
        
        return render_template('admin/manage_bookings.html', title='Manage Booking', form=form, booking=booking)

    @app.route('/admin/reports')
    @login_required
    def admin_reports():
        if not current_user.is_admin:
            flash('Access denied. You must be an administrator.', 'danger')
            return redirect(url_for('index'))
        
        # Get booking statistics
        today = datetime.today()
        month_start = datetime(today.year, today.month, 1)
        
        # Monthly bookings
        monthly_bookings = Booking.query.filter(Booking.created_at >= month_start).count()
        
        # Bookings by status
        pending_count = Booking.query.filter_by(status='pending').count()
        confirmed_count = Booking.query.filter_by(status='confirmed').count()
        completed_count = Booking.query.filter_by(status='completed').count()
        cancelled_count = Booking.query.filter_by(status='cancelled').count()
        
        # Revenue statistics
        monthly_revenue = db.session.query(db.func.sum(Booking.total_price)).filter(
            Booking.created_at >= month_start,
            Booking.status.in_(['confirmed', 'completed'])
        ).scalar() or 0
        
        # Most booked vehicles
        vehicle_bookings = db.session.query(
            Vehicle.id, Vehicle.make, Vehicle.model, db.func.count(Booking.id).label('booking_count')
        ).join(Booking).group_by(Vehicle.id).order_by(db.func.count(Booking.id).desc()).limit(5).all()
        
        return render_template('admin/reports.html', title='Booking Reports',
                               monthly_bookings=monthly_bookings,
                               pending_count=pending_count,
                               confirmed_count=confirmed_count,
                               completed_count=completed_count,
                               cancelled_count=cancelled_count,
                               monthly_revenue=monthly_revenue,
                               vehicle_bookings=vehicle_bookings)

    # Error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('500.html'), 500
