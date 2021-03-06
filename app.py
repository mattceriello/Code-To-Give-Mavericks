from flask import Flask, Blueprint, render_template, redirect, url_for, request, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_socketio import SocketIO, join_room, leave_room, emit
from flask_session import Session
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import os, sys

app = Flask(__name__)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'Cod3ToGiv3'
app.config['SESSION_TYPE'] = 'filesystem'

# Connects local PostgreSQL database to Flask app
#app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://postgres:pwd@db/codetogive'

# Connects Heroku PostgreSQL database to Flask app
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://tdlixfnucgirtt:f4b8e06465c23212247ad430912af82eac34db6988e6bc263ce046fa03cd466d@ec2-52-21-136-176.compute-1.amazonaws.com:5432/d3c01e59q00k31'


db = SQLAlchemy(app)

# Initialize Login Manager and connect to Flask app
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# Initialize table within database to store Users and define parameters
# (Open to be changed as project progresses along)
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    firstname = db.Column(db.String(80), unique=False, nullable=False)
    lastname = db.Column(db.String(80), unique=False, nullable=False)
    password = db.Column(db.String(300), unique=False, nullable=False)
    email = db.Column(db.String(80), unique=False, nullable=False)
    phone = db.Column(db.String(15), unique=False, nullable=False)
    age = db.Column(db.Integer, unique=False, nullable=False)

    def __init__(self, username=None, firstname=None, lastname=None, password=None, email=None, phone=None, age=None):
        self.username = username
        self.firstname = firstname
        self.lastname = lastname
        self.password = password
        self.email = email
        self.phone = phone
        self.age = age

    def serialize(self):
        return {"id": self.id,
                "username": self.username,
                "firstname": self.firstname,
                "lastname": self.lastname,
                "password": self.password,
                "email": self.email,
                "phone": self.phone,
                "age": self.age}


with app.app_context():
    db.create_all()


Session(app)
CORS(app)
socketio = SocketIO(app, manage_session=False, engineio_logger=False)

# ----------------------------------------------------------------#

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Landing Route
@app.route('/')
def index():
    return render_template('index.html')


# Landing Route
@app.route('/index')
def index1():
    return render_template('index.html')


# Load Profile
@app.route('/profile/<username>')
@login_required
def profile(username):
    return render_template('profile.html', user=current_user.serialize())


# Render Login Page
@app.route('/login')
def login():
    return render_template('login.html')


# Login Functionality
@app.route('/login', methods=['POST'])
def login_post():
    # Grab username and password from post request
    username = request.form["username"]
    password = request.form["password"]

    # Query user table
    user = User.query.filter_by(username=username).first()

    # Failed login
    if not user or not check_password_hash(user.password, password):
        flash('Login failed. Please try again')
        return redirect(url_for('login'))

    # Register login with Login Manager
    login_user(user)

    # Load profile
    return redirect(url_for('profile', username=user.username))


# Render Register Page
@app.route('/register')
def register():
    return render_template('register.html')


# Register Functionality
@app.route('/register', methods=['POST'])
def register_post():
    username = request.form['username']
    firstname = request.form['firstname']
    lastname = request.form['lastname']
    password1 = request.form['password1']
    password2 = request.form['password2']
    email = request.form['email']
    phone = request.form['phone']
    age = request.form['age']
    user = User.query.filter_by(username=username).first() # check to see if username exists
    if user:
        flash('Username already exists')
        return redirect(url_for('register'))

    if password1 == password2:
        print("sup")
        newUser = User(username=username, firstname=firstname, lastname=lastname, password=generate_password_hash(password1, method='sha256'), email=email, phone=phone, age=age)
        db.session.add(newUser)
        db.session.commit()
        user = User.query.filter_by(username=username).first()
        if user is None:
            return "err: user not created"

        return redirect(url_for('login'))

    else:
        flash('Passwords don\'t match')
        return redirect(url_for('register'))


# Logout Functionality
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))
# ----------------------------------------------------------------#

@app.route('/profile/chatportal')
@login_required
def chatportal():
    return render_template('chatportal.html')


# Render Chat Page
@app.route('/profile/chat', methods=['GET','POST'])
@login_required
def chat():
    # try:
    print("here", flush=True)
    username = request.form["username"]
    room = request.form["room"]
    session['username'] = username
    session['room'] = room
    return render_template('chat.html', username=username,room=room)


@app.route('/profile/update', methods=['POST'])
@login_required
def update():
    # try:
    user = User.query.filter_by(username=current_user.username).first()
    username = request.form['username']
    firstname = request.form['firstname']
    lastname = request.form['lastname']
    email = request.form['email']
    phone = request.form['phone']
    age = request.form['age']

    user.username = username
    user.firstname = firstname
    user.lastname = lastname
    user.email = email
    user.phone = phone
    user.age = age
    db.session.commit()
    return redirect(url_for('profile'))


# Join chat room
@socketio.on('join', namespace='/profile/chat')
def join():
    print("Joined!", flush=True)
    room = session.get('room')
    join_room(room)
    emit('status', {'msg':  session.get('username') + ' has entered the room.'}, room=room)


# Send message in chat room
@socketio.on('text', namespace='/profile/chat')
def text(message, username):
    room = session.get('room')
    emit('message', {'msg': username + ' : ' + message['msg']}, room=room)


# Leave chat room
@socketio.on('left', namespace='/profile/chat')
def left(message):
    room = session.get('room')
    username = session.get('username')
    leave_room(room)
    session.clear()
    emit('status', {'msg': username + ' has left the room.'}, room=room)




if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    socketio.run(app=app,host='0.0.0.0',port=port)
