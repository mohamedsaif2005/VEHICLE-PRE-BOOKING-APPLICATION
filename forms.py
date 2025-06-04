from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, SelectField, FloatField, IntegerField, DateField, HiddenField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, NumberRange, Optional
from models import User


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=20)])
    email = StringField('Email Address', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=64)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=64)])
    phone = StringField('Phone Number', validators=[DataRequired(), Length(max=20)])
    submit = SubmitField('Sign Up')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username is already taken. Please choose another one.')
            
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email is already registered. Please use another one.')


class LoginForm(FlaskForm):
    email = StringField('Email Address', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')


class VehicleForm(FlaskForm):
    make = StringField('Make', validators=[DataRequired(), Length(max=64)])
    model = StringField('Model', validators=[DataRequired(), Length(max=64)])
    year = IntegerField('Year', validators=[DataRequired(), NumberRange(min=1900, max=2100)])
    license_plate = StringField('License Plate', validators=[DataRequired(), Length(max=20)])
    vehicle_type = SelectField('Vehicle Type', validators=[DataRequired()], 
                               choices=[('car', 'Car'), ('van', 'Van'), ('truck', 'Truck'), 
                                       ('suv', 'SUV'), ('motorcycle', 'Motorcycle')])
    capacity = IntegerField('Capacity (Persons)', validators=[DataRequired(), NumberRange(min=1, max=50)])
    color = StringField('Color', validators=[DataRequired(), Length(max=20)])
    daily_rate = FloatField('Daily Rate ($)', validators=[DataRequired(), NumberRange(min=0)])
    is_available = BooleanField('Available for Booking')
    description = TextAreaField('Description', validators=[Optional(), Length(max=1000)])
    features = TextAreaField('Features (comma-separated)', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Save Vehicle')


class BookingForm(FlaskForm):
    vehicle_id = HiddenField('Vehicle ID', validators=[DataRequired()])
    start_date = DateField('Start Date', validators=[DataRequired()], format='%Y-%m-%d')
    end_date = DateField('End Date', validators=[DataRequired()], format='%Y-%m-%d')
    card_number = StringField('Card Number', validators=[DataRequired(), Length(min=13, max=19)])
    card_holder = StringField('Card Holder Name', validators=[DataRequired(), Length(max=100)])
    expiry_date = StringField('Expiry Date (MM/YY)', validators=[DataRequired(), Length(min=5, max=5)])
    cvv = StringField('CVV', validators=[DataRequired(), Length(min=3, max=4)])
    notes = TextAreaField('Special Requests', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Confirm Booking')

    def validate_end_date(self, end_date):
        if self.start_date.data and end_date.data:
            if end_date.data < self.start_date.data:
                raise ValidationError('End date must be after start date.')


class SearchForm(FlaskForm):
    vehicle_type = SelectField('Vehicle Type', choices=[('', 'All Types'), ('car', 'Car'), ('van', 'Van'), 
                                                        ('truck', 'Truck'), ('suv', 'SUV'), ('motorcycle', 'Motorcycle')])
    start_date = DateField('Start Date', validators=[Optional()], format='%Y-%m-%d')
    end_date = DateField('End Date', validators=[Optional()], format='%Y-%m-%d')
    max_price = FloatField('Max Daily Rate ($)', validators=[Optional(), NumberRange(min=0)])
    capacity = IntegerField('Min Capacity', validators=[Optional(), NumberRange(min=1)])
    submit = SubmitField('Search')


class BookingStatusForm(FlaskForm):
    status = SelectField('Status', validators=[DataRequired()], 
                         choices=[('pending', 'Pending'), ('confirmed', 'Confirmed'), 
                                  ('completed', 'Completed'), ('cancelled', 'Cancelled')])
    notes = TextAreaField('Admin Notes', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Update Status')
