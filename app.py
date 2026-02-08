from flask import Flask, render_template, url_for, flash, redirect, request, abort
from flask_login import LoginManager, login_user, current_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from models import db, User, News, Player, Comment, Match, Standing
from forms import RegistrationForm, LoginForm, NewsForm, PlayerForm, CommentForm, MatchForm, StandingForm

app = Flask(__name__)
app.config['SECRET_KEY'] = 'blacklion_secret_key'

# --- DATABASE CONFIGURATION (RENDER POSTGRESQL) ---
# 1. Go to Render Dashboard -> Select your Database -> Copy Internal Database URL
# 2. Paste it inside the quotes below:
DB_URL = "postgresql://black_lion_db_ei2o_user:rlRmxZmEpUG0b26YZA447IuppHTRfIEd@dpg-d5mttml6ubrc73afjs6g-a/black_lion_db_ei2o"

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


# --- MAIN PUBLIC ROUTES ---

@app.route("/")
@app.route("/home")
def home():
    # 1. Upcoming Matches: Not played yet, Sorted by Date (Ascending - Soonest first)
    try:
        upcoming_matches = Match.query.filter_by(is_played=False).order_by(Match.date.asc()).limit(3).all()
        # 2. Next Match: The very first one in the list
        next_match = upcoming_matches[0] if upcoming_matches else None
    except:
        upcoming_matches = []
        next_match = None

    return render_template('home.html', matches=upcoming_matches, next_match=next_match)


@app.route("/matches")
def matches():
    # 1. Upcoming: Future games (Ascending Date)
    upcoming_matches = Match.query.filter_by(is_played=False).order_by(Match.date.asc()).all()

    # 2. Results: Past games (Descending Date - Newest first)
    played_matches = Match.query.filter_by(is_played=True).order_by(Match.date.desc()).all()

    # 3. Standings: Sorted by Position (1, 2, 3...)
    standings = Standing.query.order_by(Standing.position.asc()).all()

    return render_template('matches.html', upcoming=upcoming_matches, played=played_matches, table=standings)


@app.route("/news")
def news():
    news = News.query.order_by(News.date_posted.desc()).all()
    return render_template('news.html', news=news)


@app.route("/players")
def players():
    players = Player.query.all()
    return render_template('players.html', players=players)


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


# --- AUTH ROUTES ---

@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated: return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_pw = generate_password_hash(form.password.data)
        
        # HYBRID ADMIN LOGIC: First user OR Special Email prefix
        is_first_user = (User.query.count() == 0)
        is_special_email = form.email.data.startswith('admin.')

        user = User(username=form.username.data, email=form.email.data, 
                    password=hashed_pw, is_admin=(is_first_user or is_special_email))
        
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


# --- ADMIN ROUTES ---

# 1. NEWS MANAGEMENT
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


@app.route("/delete/news/<int:id>", methods=['POST'])
@login_required
def delete_news(id):
    if not current_user.is_admin: abort(403)
    post = News.query.get_or_404(id)
    db.session.delete(post)
    db.session.commit()
    return redirect(url_for('news'))


# 2. PLAYER MANAGEMENT
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


@app.route("/delete/player/<int:id>", methods=['POST'])
@login_required
def delete_player(id):
    if not current_user.is_admin: abort(403)
    player = Player.query.get_or_404(id)
    db.session.delete(player)
    db.session.commit()
    return redirect(url_for('players'))


# 3. MATCH MANAGEMENT (Full Control)
@app.route("/match/new", methods=['GET', 'POST'])
@login_required
def create_match():
    if not current_user.is_admin: abort(403)
    form = MatchForm()
    if form.validate_on_submit():
        match = Match(
            home_team=form.home_team.data,
            away_team=form.away_team.data,
            date=form.date.data,
            venue=form.venue.data,
            ticket_link=form.ticket_link.data,
            is_played=form.is_played.data,
            home_score=form.home_score.data,
            away_score=form.away_score.data,
            outcome=form.outcome.data
        )
        db.session.add(match)
        db.session.commit()
        return redirect(url_for('matches'))
    return render_template('create_content.html', form=form, legend='Add Match')


@app.route("/match/<int:match_id>/update", methods=['GET', 'POST'])
@login_required
def update_match(match_id):
    match = Match.query.get_or_404(match_id)
    if not current_user.is_admin: abort(403)
    form = MatchForm()
    if form.validate_on_submit():
        match.home_team = form.home_team.data
        match.away_team = form.away_team.data
        match.date = form.date.data
        match.venue = form.venue.data
        match.ticket_link = form.ticket_link.data
        match.is_played = form.is_played.data
        match.home_score = form.home_score.data
        match.away_score = form.away_score.data
        match.outcome = form.outcome.data
        db.session.commit()
        return redirect(url_for('matches'))
    elif request.method == 'GET':
        form.home_team.data = match.home_team
        form.away_team.data = match.away_team
        form.date.data = match.date
        form.venue.data = match.venue
        form.ticket_link.data = match.ticket_link
        form.is_played.data = match.is_played
        form.home_score.data = match.home_score
        form.away_score.data = match.away_score
        form.outcome.data = match.outcome
    return render_template('create_content.html', form=form, legend='Update Match')


@app.route("/match/<int:match_id>/delete", methods=['POST'])
@login_required
def delete_match(match_id):
    if not current_user.is_admin: abort(403)
    match = Match.query.get_or_404(match_id)
    db.session.delete(match)
    db.session.commit()
    return redirect(url_for('matches'))


# 4. STANDINGS MANAGEMENT (Add, Edit, Delete)
@app.route("/standing/new", methods=['GET', 'POST'])
@login_required
def create_standing():
    if not current_user.is_admin: abort(403)
    form = StandingForm()
    if form.validate_on_submit():
        team = Standing(
            position=form.position.data,
            team_name=form.team_name.data,
            played=form.played.data,
            points=form.points.data
        )
        db.session.add(team)
        db.session.commit()
        return redirect(url_for('matches'))
    return render_template('create_content.html', form=form, legend='Add Team to Table')


@app.route("/standing/<int:standing_id>/update", methods=['GET', 'POST'])
@login_required
def update_standing(standing_id):
    team = Standing.query.get_or_404(standing_id)
    if not current_user.is_admin: abort(403)
    form = StandingForm()
    if form.validate_on_submit():
        team.position = form.position.data
        team.team_name = form.team_name.data
        team.played = form.played.data
        team.points = form.points.data
        db.session.commit()
        return redirect(url_for('matches'))
    elif request.method == 'GET':
        form.position.data = team.position
        form.team_name.data = team.team_name
        form.played.data = team.played
        form.points.data = team.points
    return render_template('create_content.html', form=form, legend='Update Table')


@app.route("/standing/<int:standing_id>/delete", methods=['POST'])
@login_required
def delete_standing(standing_id):
    if not current_user.is_admin: abort(403)
    team = Standing.query.get_or_404(standing_id)
    db.session.delete(team)
    db.session.commit()
    return redirect(url_for('matches'))


if __name__ == '__main__':
    app.run(debug=True)
