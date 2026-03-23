from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SubmitField, SelectField, 
    TextAreaField, IntegerField, DateField, TimeField, URLField, BooleanField
)
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional, NumberRange

class RegisterForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(max=100)])
    email = StringField('Email Address', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        'Confirm Password', 
        validators=[DataRequired(), EqualTo('password', message='Passwords must match')]
    )
   
    # REQUIREMENT: POPIA Consent
    popia_consent = BooleanField('I agree to the POPI Act terms', validators=[DataRequired()])
    submit = SubmitField('Create Account')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class WorkshopForm(FlaskForm):
    # 1. Basic Info
    title = StringField('Workshop Title', validators=[
        DataRequired(message="Please enter a title."), 
        Length(max=100)
    ])
    description = TextAreaField('Detailed Description', validators=[
        DataRequired(message="Please provide a description of what students will learn.")
    ])
    
    # 2. Faculty Association
    faculty = SelectField('Target Faculty', choices=[
        ('Management Sciences', 'Management Sciences'),
        ('Engineering & Built Environment', 'Engineering & Built Environments'),
        ('Health Sciences', 'Health Sciences'),
        ('Arts and Design', 'Arts and Design'),
        ('Accounting and Informatics', 'Accounting and Informatics'),
        ('Applied Science', 'Applied Science')
    ], validators=[DataRequired()])

    # 3. Delivery Mode (FIXED: This was missing and caused the error)
    workshop_type = SelectField('Workshop Type', choices=[
        ('In-Person', 'In-Person (On Campus)'), 
        ('Online', 'Online (Virtual)')
    ])
    
    # These fields are required depending on the type selected
    venue = StringField('Physical Venue', validators=[Optional(), Length(max=100)])
    online_link = URLField('Online Link', validators=[Optional()])

    # 4. Discipline/Category
    category = SelectField('Discipline/Field', choices=[
        ('Information Technology', 'Information Technology'),
        ('Computer Science', 'Computer Science'),
        ('Engineering', 'Engineering'),
        ('Business & Finance', 'Business & Finance'),
        ('Soft Skills', 'Soft Skills')
    ], validators=[DataRequired()])
    
    # 5. Experience Levels
    level = SelectField('Target Level', choices=[
        ('Entry-level', 'Entry-level'),
        ('Intermediate', 'Intermediate'),
        ('Advanced', 'Advanced')
    ], validators=[DataRequired()])

    # 6. Timing
    date = DateField('Date', format='%Y-%m-%d', validators=[DataRequired()])
    start_time = TimeField('Start Time', validators=[DataRequired()])
    end_time = TimeField('End Time', validators=[DataRequired()])
    
    # 7. Capacity
    capacity = IntegerField('Capacity', validators=[
        DataRequired(), 
        NumberRange(min=1, message="Capacity must be at least 1.")
    ])
    
    # 8. Facilitator (Populated in app.py)
    facilitator_id = SelectField('Facilitator', coerce=int, validators=[DataRequired()])
    
    submit = SubmitField('Save Workshop Details')

class FacilitatorForm(FlaskForm):
    full_name = StringField("Facilitator Name", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    submit = SubmitField("Create Facilitator")

class FeedbackForm(FlaskForm):
    rating = SelectField('Rating', coerce=int, choices=[
        (5, '5 - Excellent'), (4, '4 - Good'), (3, '3 - Average'), (2, '2 - Poor'), (1, '1 - Very Poor')
    ], validators=[DataRequired()])
    comment = TextAreaField('Comments', validators=[DataRequired(), Length(min=5)])
    submit = SubmitField('Submit Feedback')