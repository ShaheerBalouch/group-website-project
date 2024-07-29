from flask_wtf import FlaskForm
from flask_wtf.file import FileRequired, FileAllowed
from flask_login import current_user
from wtforms import StringField, PasswordField, SelectField, SubmitField, TextAreaField, MultipleFileField, FileField, RadioField, IntegerField, SelectMultipleField, BooleanField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Regexp, InputRequired, Optional, NumberRange
from store.models import User, Tools, Address
import requests
from flask import request
import json
import googlemaps


class RegistrationForm(FlaskForm):
    name = StringField('Full Name', validators = [DataRequired()])
    email = StringField('Email',validators=[DataRequired(),Email(message='Must be a valid email')])
    password = PasswordField('Password',validators=[DataRequired(), Length(min=8, message='Password must be at least 8 characters long')])
    confirm_password = PasswordField('Confirm Password',validators=[DataRequired(), EqualTo('password', message='Passwords do not match')])
    age = IntegerField('Age', validators = [DataRequired(), NumberRange(min=18, message='Must be 18 or older to use this site')])   # May need to add a message to this
    postcode = StringField('Postcode', validators=[DataRequired()], id='auto_complete')
    agree_terms = BooleanField('', validators=[DataRequired()])
    submit = SubmitField('REGISTER')


    def validate_email(self,email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Email address is already associated with an account.')

    def validate_postcode(self, postcode):
        r = requests.get(f'http://api.postcodes.io/postcodes/{postcode.data}/validate?')
        if r.json()['result'] == False:
            raise ValidationError('Postcode is not valid.')

    def validate_password(self, password):
        # if name.data.lower() in password.data.lower():
        #     raise ValidationError('Password cannot contain your name.')

        if password.data.islower() or password.data.isupper():
            raise ValidationError('Password must contain both upper and lower case words.')

class LoginForm(FlaskForm):
    email = StringField('Email',validators=[DataRequired(),Email()])
    password = PasswordField('Password',validators=[DataRequired()])
    submit = SubmitField('Login')


class ReviewForm(FlaskForm):
    rating = RadioField('Choose a rating:', choices=[(1, 'One'), (2, 'Two'), (3, 'Three'), (4, 'Four'), (5, 'Five')],
                        coerce=int, validators=[DataRequired()])
    written = TextAreaField('Written Review')
    submit = SubmitField('Send')


class ToolForm(FlaskForm):
    title = StringField('Title', validators = [DataRequired()])
    tool_category = RadioField('Choose a category:', choices=[('measure', 'Measuring Tool (eg. Anglometer, Level, Calipers)'),
    ('striking', 'Striking Tool (eg. Hammer, Sledge)'),
    ('cutting', 'Cutting Tool (eg. Saw, Chainsaw, Axe)'),
    ('holding', 'Holding Tool (eg. Clamp, Pliers)'),
    ('driving', 'Driving Tool (eg. Screwdriver, Hand Drill, Wrench)'),
    ('power', 'Power Tool (Any Tool That Needs Power)'),
    ('miscellaneous', 'Miscellaneous Tool')],
                        validators=[DataRequired()])
    images = MultipleFileField('Tool Picture', validators = [DataRequired()])
    description = TextAreaField('Description', validators = [DataRequired()])
    location = StringField('Your Location', validators = [DataRequired()], id='search_input2')
    deposit = IntegerField('Deposit Amount', validators = [DataRequired()])

    def validate_location(self, location):
        user_address = Address.query.filter(Address.user_id == current_user.id).first()
        user_postcode = user_address.postcode
        postcode=''
        api_key = 'AIzaSyDyrFnIprNCQ3-sChnwRq74w8Df0K-SmXs'

        base_url = "https://maps.googleapis.com/maps/api/geocode/json"
        endpoint = f"{base_url}?address={location.data}&key={api_key}"
        r = requests.get(endpoint)

        results = r.json()['results'][0]
        lat = results['geometry']['location']['lat']
        lng = results['geometry']['location']['lng']

        endpoint2 = f"{base_url}?latlng={lat}, {lng}&key={api_key}"

        r2 = requests.get(endpoint2)
        results2 = r2.json()['results'][0]


        for i in results2['address_components']:
            if i['types'][0] == 'postal_code':
                postcode = i['long_name']
                break

        if postcode!=user_postcode:
            raise ValidationError('Your address does not match your postcode. Please enter YOUR address.')

    def validate_images(self, images):
        for pic in images.data:
            if pic.mimetype!='image/jpeg' and pic.mimetype!='image/png':
                raise ValidationError('Please upload Jpeg or Png images only.')


# Maybe add Tool category as radio buttons if we decide to have them

class RentToolForm(FlaskForm):
    card_number = StringField('Card Number', validators=[DataRequired(), Regexp('^[0-9]{16}$', message='Please enter a valid card number.')])
    expiry_month = StringField('Expiry Month', validators=[DataRequired(), Regexp('^(0?[1-9]|1[012])$', message='Please enter a valid expiry month.')])
    expiry_year = StringField('Expiry Year', validators=[DataRequired(), Regexp('^(2[2-9]|[3-9][0-9])$', message='Please enter a valid expiry year.')])
    security = StringField('Security', validators=[DataRequired(), Regexp('^[0-9]{3}$', message='Please enter a valid CVC')])
    submit = SubmitField('Pay')


class EditToolForm(FlaskForm):
    # removed the data required validator because a user may not want to alter the images.
    #Removed all the data required validators because the user may want to only alter one detail
    title = StringField('Title')
    images = MultipleFileField('Add more picture(s)')
    description = TextAreaField('Description')
    location = StringField('Location', id='search_input3')
    deposit = IntegerField('Deposit Amount', validators=[Optional()])

    def validate_location(self, location):

        if location.data!='':

            user_address = Address.query.filter(Address.user_id == current_user.id).first()
            user_postcode = user_address.postcode
            postcode=''
            api_key = 'AIzaSyDyrFnIprNCQ3-sChnwRq74w8Df0K-SmXs'

            base_url = "https://maps.googleapis.com/maps/api/geocode/json"
            endpoint = f"{base_url}?address={location.data}&key={api_key}"
            r = requests.get(endpoint)

            results = r.json()['results'][0]
            lat = results['geometry']['location']['lat']
            lng = results['geometry']['location']['lng']

            endpoint2 = f"{base_url}?latlng={lat}, {lng}&key={api_key}"

            r2 = requests.get(endpoint2)
            results2 = r2.json()['results'][0]


            for i in results2['address_components']:
                if i['types'][0] == 'postal_code':
                    postcode = i['long_name']
                    break

            if postcode!=user_postcode:
                raise ValidationError('Your address does not match your postcode. Please enter YOUR address.')


    def validate_images(self, images):
        for pic in images.data:

            if pic!='':
                if pic.mimetype!='image/jpeg' and pic.mimetype!='image/png':
                    raise ValidationError('Please upload Jpeg or Png images only.')

class ProfileForm(FlaskForm):
    image = FileField('Profile Picture')
    description = TextAreaField('Description')
    email = StringField('Email', validators = [Optional(), Email()])
    name = StringField('Full Name')
    address_line_1 = StringField('Address Line', id='search_input')
    #postcode = StringField('Postcode', id='auto_complete')
    city = StringField('City')          # Might remove city as it serves no purpose

    # password = PasswordField('Password') // better to implement changing password functionality in a separate form

    def validate_email(self,email):
        if email.data!=current_user.email:

            user = User.query.filter_by(email=email.data).first()
            if user is not None:
                raise ValidationError('Email address is already associated with an account.')

    def validate_image(self, image):

        if image.data!='':

            if image.data.mimetype!='image/jpeg' and image.data.mimetype!='image/png':
                raise ValidationError('Please upload Jpeg or Png images only.')


class MessagesForm(FlaskForm):
    message = TextAreaField('Message', validators=[DataRequired()])
    submit = SubmitField('Send')

class SearchForm(FlaskForm):
    search = StringField('', validators=[DataRequired()], id='toolSearch')
    submit = SubmitField('Search')


class FlagForm(FlaskForm):
    category = SelectMultipleField('Select all that apply:', choices=[('Sexual Content', 'Sexual Content'), ('Violent Content', 'Violent Content'),
    ('Spam or Misleading', 'Spam or Misleading')], validators=[DataRequired()])
    submit = SubmitField('Report')


class ResetPassword(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Submit')


class ChangePassword(FlaskForm):
    password = PasswordField('New password',validators=[DataRequired(), Length(min=8, message='Password must be at least 8 characters long')])
    confirm_password = PasswordField('Confirm Password',validators=[DataRequired(),EqualTo('password')])
    submit = SubmitField('Change password')

    def validate_password(self, password):
        # if name.data.lower() in password.data.lower():
        #     raise ValidationError('Password cannot contain your name.')

        if password.data.islower() or password.data.isupper():
            raise ValidationError('Password must contain both upper and lower case words.')


class ToolConditionForm(FlaskForm):
    condition = RadioField('Condition of the tool: ', choices = [('given', 'As it was when given away'),
    ('cosmetic', 'Functional but signs of cosmetic damage'),
    ('partial', 'Partly working'),
    ('broken','Not working at all')], validators=[DataRequired()])
    notes = TextAreaField('Notes: ', validators=[Optional()])
    submit = SubmitField('Submit condition')
