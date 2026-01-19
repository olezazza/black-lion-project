from flask import Flask, render_template, url_for, flash, redirect, request, abort
from flask_login import LoginManager, login_user, current_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, News, Player, Comment
from forms import RegistrationForm, LoginForm, NewsForm, PlayerForm, CommentForm

app = Flask(__name__)
app.config['SECRET_KEY'] = 'blacklion_secret_key'

# --- DATABASE CONFIGURATION (POSTGRESQL SWITCH) ---
# 1. Go to Render Dashboard -> Dashboard -> New -> PostgreSQL
# 2. Copy the "Internal Database URL"
# 3. Paste it inside the quotes below:
DB_URL = "postgresql://black_lion_db_user:V23G6Dp3Fy580TaMH3CtxfvtZJl1Q3RJ@dpg-d5mtftsmrvns73fcrmb0-a/black_lion_db"

# Fix for Render's URL format (Render uses 'postgres://' but SQLAlchemy needs 'postgresql://')
if DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DB_URL
# --------------------------------------------------

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- CRITICAL FIX FOR RENDER DEPLOYMENT ---
# This forces the database tables to be created as soon as the app starts.
with app.app_context():
    db.create_all()
# ------------------------------------------

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- MAIN ROUTES ---
@app.route("/")
@app.route("/home")
def home():
    return render_template('home.html')

@app.route("/news")
def news():
    news = News.query.order_by(News.date_posted.desc()).all()
    return render_template('news.html', news=news)

@app.route("/news/<int:news_id>", methods=['GET', 'POST'])
def news_detail(news_id):
    post = News.query.get_or_404(news_id)
    form = CommentForm()
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        comment = Comment(text=form.text.data, author=current_user, article=post)
        db.session.add(comment)
        db.session.commit()
        return redirect(url_for('news_detail', news_id=post.id))
    return render_template('news_detail.html', post=post, form=form)

@app.route("/players")
def players():
    players = Player.query.all()
    return render_template('players.html', players=players)

# --- AUTH ROUTES ---
@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated: return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_pw = generate_password_hash(form.password.data)
        # AUTO-ADMIN LOGIC: If this is the first user ever, make them Admin
        is_first_user = (User.query.count() == 0)
        user = User(username=form.username.data, email=form.email.data, 
                    password=hashed_pw, is_admin=is_first_user)
        db.session.add(user)
        db.session.commit()
        flash('Account created! Login now.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Login Failed. Check details.', 'danger')
    return render_template('login.html', form=form)

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))

# --- ADMIN ACTIONS (Create, Update, Delete) ---
@app.route("/news/new", methods=['GET', 'POST'])
@login_required
def create_news():
    if not current_user.is_admin: abort(403)
    form = NewsForm()
    if form.validate_on_submit():
        post = News(title=form.title.data, content=form.content.data, image_url=form.image_url.data)
        db.session.add(post)
        db.session.commit()
        return redirect(url_for('news'))
    return render_template('create_content.html', form=form, legend='New Article')

@app.route("/news/<int:news_id>/update", methods=['GET', 'POST'])
@login_required
def update_news(news_id):
    post = News.query.get_or_404(news_id)
    if not current_user.is_admin: abort(403)
    form = NewsForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        post.image_url = form.image_url.data
        db.session.commit()
        return redirect(url_for('news_detail', news_id=post.id))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
        form.image_url.data = post.image_url
    return render_template('create_content.html', form=form, legend='Update Article')

@app.route("/players/new", methods=['GET', 'POST'])
@login_required
def create_player():
    if not current_user.is_admin: abort(403)
    form = PlayerForm()
    if form.validate_on_submit():
        player = Player(name=form.name.data, position=form.position.data, age=form.age.data, 
                        height=form.height.data, weight=form.weight.data, image_url=form.image_url.data)
        db.session.add(player)
        db.session.commit()
        return redirect(url_for('players'))
    return render_template('create_content.html', form=form, legend='Add Player')

@app.route("/players/<int:player_id>/update", methods=['GET', 'POST'])
@login_required
def update_player(player_id):
    player = Player.query.get_or_404(player_id)
    if not current_user.is_admin: abort(403)
    form = PlayerForm()
    if form.validate_on_submit():
        player.name = form.name.data
        player.position = form.position.data
        player.age = form.age.data
        player.height = form.height.data
        player.weight = form.weight.data
        player.image_url = form.image_url.data
        db.session.commit()
        return redirect(url_for('players'))
    elif request.method == 'GET':
        form.name.data = player.name
        form.position.data = player.position
        form.age.data = player.age
        form.height.data = player.height
        form.weight.data = player.weight
        form.image_url.data = player.image_url
    return render_template('create_content.html', form=form, legend='Update Player')

@app.route("/delete/news/<int:id>", methods=['POST'])
@login_required
def delete_news(id):
    if not current_user.is_admin: abort(403)
    post = News.query.get_or_404(
