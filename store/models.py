from datetime import datetime
from store import db, login_manager
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

class Messages(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    from_user = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    to_user = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    contents = db.Column(db.String(250), nullable=False)
    datetime = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Maybe a relationship from the message to the user?

    def __repr__(self):
        return f"Messages('{self.from_user}', '{self.to_user}', '{self.contents}', '{self.datetime}')"

class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_1 = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user_2 = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    room = db.Column(db.String(50), nullable=False)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key = True)
    # username = db.Column(db.String(15), unique=True, nullable = False)  Client said we don't need username
    name = db.Column(db.String(50), nullable = False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    # password = db.Column(db.String(60), nullable=False) Not needed since we have the property decorator on the password method!
    age = db.Column(db.Integer, nullable = False)
    description = db.Column(db.Text)
    # image_id = db.Column(db.Integer, db.ForeignKey('img.id'), default=2)
    image = db.relationship('Img', uselist=False)
    tool_post = db.relationship('Tools', backref = 'user', lazy=True)
    review = db.relationship('Reviews', backref = 'user', lazy = True)
    flag = db.relationship('Flags', backref = 'user', lazy = True)
    address = db.relationship('Address', backref = 'user', lazy = True)
    confirmed = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)


    def __repr__(self):
        return f"User('{self.id}', {self.email}')"

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self,password):
        self.password_hash=generate_password_hash(password)

    def verify_password(self,password):
        return check_password_hash(self.password_hash,password)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Tools(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    title = db.Column(db.String(100), nullable=False)
    # image_id = db.Column(db.Integer, db.ForeignKey('img.id'), default=1)
    images = db.relationship('Img')
    description = db.Column(db.Text)
    deposit = db.Column(db.Integer, nullable=False)
    availibility = db.Column(db.Boolean, nullable = False, default = True)
    tool_category = db.Column(db.String(100), nullable = False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable = False)
    tool_review = db.relationship('Reviews', backref = 'post', lazy = True)
    flag = db.relationship('Flags', backref = 'post', lazy = True)


    def __repr__(self):
      return f"Post('{self.date}', '{self.title}', '{self.description}')"

class Reviews(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    date = db.Column(db.DateTime, nullable = False, default = datetime.utcnow)
    rating = db.Column(db.Integer, nullable = False)
    written_review = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable = False)
    tool_id = db.Column(db.Integer, db.ForeignKey('tools.id'), nullable = False)

    def __repr__(self):
        return f"Review('{self.date}', '{self.rating}')"

class Flags(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    date = db.Column(db.DateTime, nullable = False, default = datetime.utcnow)
    category = db.Column(db.String(100), nullable = False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable = False)
    tool_id = db.Column(db.Integer, db.ForeignKey('tools.id'), nullable = False)

    def __repr__(self):
        return f"Flag('{self.date}', '{self.category}')"

class Address(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    address_line_1 = db.Column(db.String(100))
    city = db.Column(db.String(50))
    postcode = db.Column(db.String(64))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable = False)

    def __repr__(self):
        return f"Address('{self.address_line_1}')"

class Img(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    img = db.Column(db.Text)
    name = db.Column(db.Text, nullable=False)
    mimetype = db.Column(db.Text, nullable=False)
    # tool_img = db.relationship('Tools', backref = 'img', lazy=True)
    # profile_img = db.relationship('User', backref = 'img', lazy=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    tool_id = db.Column(db.Integer, db.ForeignKey('tools.id'))

    def __repr__(self):
        return f"Img('{self.img}')"

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.Text)
    content = db.Column(db.Text)
    seen = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable = False)

    def __repr__(self):
        return f"Notification('{self.subject}', '{self.content}')"


class BorrowHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable = False)
    tool_id = db.Column(db.Integer, db.ForeignKey('tools.id'), nullable = False)
    deposit_paid = db.Column(db.Integer, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    active_status = db.Column(db.Boolean, default=True)
    tool = db.relationship('Tools')
    user = db.relationship('User', backref='borrowed_tools')
