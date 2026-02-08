from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, IntegerField, DateTimeLocalField, \
    BooleanField, SelectField
from wtforms.validators import DataRequired, Length, Email, ValidationError, Optional
from models import User


# (Keep RegistrationForm, LoginForm, NewsForm, PlayerForm, CommentForm unchanged)
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        if User.query.filter_by(username=username.data).first():
            raise ValidationError('Username taken.')

    def validate_email(self, email):
        if User.query.filter_by(email=email.data).first():
            raise ValidationError('Email taken.')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class NewsForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    image_url = StringField('Image Link (URL)', validators=[DataRequired()])
    content = TextAreaField('Content', validators=[DataRequired()])
    submit = SubmitField('Post News')


class PlayerForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    position = StringField('Position', validators=[DataRequired()])
    age = IntegerField('Age', validators=[DataRequired()])
    height = IntegerField('Height (cm)', validators=[DataRequired()])
    weight = IntegerField('Weight (kg)', validators=[DataRequired()])
    image_url = StringField('Player Photo Link (URL)', validators=[DataRequired()])
    submit = SubmitField('Add Player')


class CommentForm(FlaskForm):
    text = TextAreaField('Comment', validators=[DataRequired()])
    submit = SubmitField('Post')


# --- UPDATED MATCH FORM ---
class MatchForm(FlaskForm):
    home_team = StringField('Home Team', validators=[DataRequired()], default="Black Lion")
    away_team = StringField('Away Team', validators=[DataRequired()])
    date = DateTimeLocalField('Date & Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    venue = StringField('Venue', validators=[DataRequired()])
    ticket_link = StringField('Ticket Link (Optional)', validators=[Optional()])

    # Results Section
    is_played = BooleanField('Match Finished?')
    home_score = IntegerField('Home Score', validators=[Optional()])
    away_score = IntegerField('Away Score', validators=[Optional()])
    outcome = SelectField('Result Color',
                          choices=[('win', 'Win (Green)'), ('loss', 'Loss (Red)'), ('draw', 'Draw (Grey)')],
                          validators=[Optional()])

    submit = SubmitField('Save Match')


class StandingForm(FlaskForm):
    position = IntegerField('Position', validators=[DataRequired()])
    team_name = StringField('Team Name', validators=[DataRequired()])
    played = IntegerField('Games Played', validators=[DataRequired()])
    points = IntegerField('Points', validators=[DataRequired()])
    submit = SubmitField('Update Team')
