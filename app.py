from distutils.command.config import config
from pickle import FALSE, NONE
from flask import Flask
from flask import render_template, url_for, request, flash, redirect, session
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_required, logout_user, login_user, LoginManager
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
import requests
import re
import hasher
from Security.config import weather_secret

def get_weather_data(city):
     url = f'http://api.openweathermap.org/data/2.5/weather?q={ city }&units=imperial&appid=' + weather_secret
     r = requests.get(url).json()
     return r


app = Flask(__name__)
app.config['SECRET_KEY'] = 'xPOZI+`w}@`?NXC'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['FLASK_ADMIN_SWATCH'] = 'cerulean'
login_manager = LoginManager()
login_manager.init_app(app)
db = SQLAlchemy(app)

class UsersView(ModelView):
    column_display_pk = False
    column_hide_backref = False
    column_list = ( 'name', 'password', 'salt', 'fav_city')



#TODO doesn't display fav_city but does display city relationship
class Users(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String, nullable=False)
    salt = db.Column(db.String, nullable=False)
    fav_city = db.Column(db.String, db.ForeignKey('cities.name', ondelete='SET NULL'), nullable=True)
    city = db.relationship('Cities', backref=db.backref('users', lazy=True))

    def get_id(self):
        return str(self.id)
    def __repr__(self):
        return '<User %r, Favorite City: %r>' % (self.name, self.fav_city)

class Posts(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.DateTime, nullable=False, server_default=db.func.current_timestamp())
    title = db.Column(db.String, nullable = False)
    content = db.Column(db.String, nullable = False)

    def __repr__(self):
        return '<Title %s, Content %s>' % (self.title, self.content)

class Cities(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable =False, unique=True)

    def __repr__(self):
        return '<Name %s' % self.name


admin = Admin(app, name='microblog', template_mode='bootstrap3')
admin.add_view(UsersView(Users, db.session))
admin.add_view(ModelView(Posts, db.session))
admin.add_view(ModelView(Cities, db.session))

@login_manager.user_loader
def load_user(user_id):
    loaded_user = Users.query.filter_by(id=user_id).first()
    if loaded_user is not NONE:
        return loaded_user
    else:
        return NONE
# change get_id
@app.route("/")
def index():
    print(session)
    posts = Posts.query.all()
    return render_template('index.html', posts=posts)

@app.route("/<int:post_id>")
def post(post_id):
    post = Posts.query.filter_by(id=post_id).first()
    return render_template('post.html', post=post)

@app.route('/create', methods=('GET', 'POST'))
def create():
    if request.method == 'POST':
        title = request.form['title']
        content  = request.form['content']

        if not title:
            flash('Title is required')
        else:
            post = Posts(title=title,content=content)
            db.session.add(post)
            db.session.commit()
            return redirect(url_for('index'))

    return render_template('create.html')

@app.route('/<int:id>/edit', methods=('GET', 'POST'))
def edit(id):
    post = Posts.query.filter_by(id=id).first()
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        if not title:
            flash('Title is required')
        else:
            post.title = title
            post.content = content
            db.session.commit()
            return redirect(url_for('index'))

    return render_template('edit.html', post=post)

@app.route('/<int:id>/delete', methods=('Post',))
def delete(id):
    post = Posts.query.filter_by(id=id).first()
    db.session.delete(post)
    db.session.commit()
    flash('"{}" was successfully deleted!'.format(post.title))
    return redirect(url_for('index'))


@app.route('/weather')
def weather():
    cities = Cities.query.all()
    weather_data= []
    for row in cities:
        r = get_weather_data(row.name)
        weather = {
            'city': row.name,
            'temperature': r['main']['temp'],
            'icon': r['weather'][0]['icon'],
            'description': r['weather'][0]['description']
        }
        weather_data.append(weather)
    return render_template('weather.html',weather_data=weather_data)

@app.route('/weather', methods=('POST',))
def weather_post():
    new_city = request.form['request_city']
    if new_city:
        existing_city = Cities.query.filter_by(name=new_city).first()
        if existing_city is not NONE:
            new_city_data = get_weather_data(new_city)
            if new_city_data['cod'] == 200:
                city = Cities(name=new_city)
                db.session.add(city)
                db.session.commit()
            else:
                flash('City does not exist')
        else:
            flash('City already exists in database')
    else:
        flash('City is required')

    return redirect(url_for('weather'))

@app.route('/weather/<city>')
def weather_delete(city):
    deleted_city = Cities.query.filter_by(name=city).first()
    db.session.delete(deleted_city)
    db.session.commit()
    flash(city + " is deleted")
    return redirect(url_for('weather'))

@app.route('/signin', methods=('POST','GET'))
def signin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = Users.query.filter_by(name=username).first()
        if user:
            hashed = hasher.saltAndPepper(password,user.salt)[0]
            if hashed == user.password:
                print(session)
                test = login_user(user)
                print(session)
                flash("Logged in Successfully")
                return redirect(url_for('index'))
            else:
                flash("Incorrect Password")
        else:
            flash('User not found')
    return render_template('signin.html')

@app.route('/createAccount', methods=('POST', 'GET'))
def createAccount():
    if request.method == 'POST':
        name = request.form['username']
        password = request.form['password']
        password = hasher.saltAndPepper(password)
        existing_account = Users.query.filter_by(name=name).first()
        if existing_account:
            flash("User already exists")
            return render_template('createAccount.html')
        else:
            new_user = Users(name=name,password=password[0],salt=password[1])
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('index'))
    return render_template('createAccount.html')

@app.route('/profile', methods=('GET','POST'))
@login_required
def profile():
    if request.method == 'POST':
        new_city = request.form['request_city']
        if new_city:
            existing_city = Cities.query.filter_by(name=new_city).first()
            if existing_city is not NONE:
                new_city_data = get_weather_data(new_city)
                if new_city_data['cod'] == 200:
                    city = Cities(name=new_city)
                    db.session.add(city)
                    db.session.commit()
                else:
                    flash('City does not exist')
            else:
                flash('City already exists in database')
        else:
            flash('City is required')
            return redirect(url_for('profile'))
    p = load_user(session['_user_id'])
    print(p)
    posts = Posts.query.all() 
    cities = Cities.query.all()
    if p.fav_city is not NONE:
        data = get_weather_data(p.fav_city)
        weather = {
            'city': p.fav_city,
            'temperature': data['main']['temp'],
            'icon': data['weather'][0]['icon'],
            'description': data['weather'][0]['description']
        }
    else:
        weather={}
    return render_template('profile.html', user=p, posts=posts, cities=cities, weather=weather)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logged out successfully")
    return redirect(url_for('index'))
    
@app.route('/favorite/<string:city>', methods=('POST',))
@login_required
def favorite(city):
    user = load_user(session['_user_id'])
    city_obj = Cities.query.filter_by(name=city).first()
    user.fav_city=city_obj.name
    db.session.add(user)
    db.session.commit()
    return redirect(url_for('profile'))


@app.route("/hello/<name>")
def hello_there(name):
    now = datetime.now()
    formatted_now = now.strftime("%A, %d %B, %Y at %X")

    # Filter the name argument to letters only using regular expressions. URL arguments
    # can contain arbitrary text, so we restrict to safe characters only.
    match_object = re.match("[a-zA-Z]+", name)

    if match_object:
        clean_name = match_object.group(0)
    else:
        clean_name = "Friend"

    content = "Hello there, " + clean_name + "! It's " + formatted_now
    return content