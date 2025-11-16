from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import exc, text
import os
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_mail import Mail
from dotenv import load_dotenv

# Load environment variables from .env (DATABASE_URL)
load_dotenv()

db = SQLAlchemy()
mail = Mail()

def create_app():
    # instance_relative_config=True so app.instance_path points to /instance
    app = Flask(__name__, instance_relative_config=True)
    app.config['SECRET_KEY'] = 'hjshjhdjah kjshkjdhjs'

    # Ensure instance folder exists (still ok to have, even if DB is remote)
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass

    # 🔴 Database Configuration – use shared PostgreSQL from .env
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL not set in .env")

    # Make sure driver is correct for SQLAlchemy
    if db_url.startswith("postgresql://") and "+psycopg2" not in db_url:
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    print("📌 USING DATABASE:", app.config['SQLALCHEMY_DATABASE_URI'])

    # Email Configuration
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 465
    app.config['MAIL_USE_SSL'] = True
    app.config['MAIL_USERNAME'] = 'togethertolerant@gmail.com'
    app.config['MAIL_PASSWORD'] = 'asdqweyxc123'

    mail.init_app(app)
    db.init_app(app)
    migrate = Migrate(app, db)

    from .views import views
    from .auth import auth
    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')

    from .models import User

    # Optional: create tables if they don't exist
    with app.app_context():
        db.create_all()
        db.session.commit()

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    @app.before_request
    def before_request():
        # Check if the database connection is valid
        try:
            db.session.execute(text("SELECT 1"))
        except exc.SQLAlchemyError:
            db.session.rollback()
            db.session.remove()
            db.engine.dispose()

    @app.teardown_request
    def teardown_request(exception=None):
        # Ensure that the session is properly closed at the end of the request
        db.session.remove()

    @app.errorhandler(500)
    def handle_internal_server_error(e):
        # Log the error or take appropriate action
        return "Internal Server Error", 500

    return app


def create_database(app):
    # Generic helper: create all tables on the current DB
    with app.app_context():
        db.create_all()
        print('Created Database!')
