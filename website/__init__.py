from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import exc
from os import path
import os
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_mail import Mail

db = SQLAlchemy()
mail = Mail()

def create_app():
    # instance_relative_config=True so app.instance_path points to /instance
    app = Flask(__name__, instance_relative_config=True)
    app.config['SECRET_KEY'] = 'hjshjhdjah kjshkjdhjs'

    # Ensure instance folder exists
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass

    # Database Configuration – use SQLite file in /instance/local.db
    db_path = os.path.join(app.instance_path, 'local.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Email Configuration
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 465
    app.config['MAIL_USE_SSL'] = True
    app.config['MAIL_USERNAME'] = 'toleranttogether@gmail.com'
    app.config['MAIL_PASSWORD'] = 'kretqfdywchpgbuo'

    mail.init_app(app)
    db.init_app(app)
    migrate = Migrate(app, db)

    from .views import views
    from .auth import auth
    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')

    from .models import User

    # Only create tables if the DB file does NOT exist yet
    if not path.exists(db_path):
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
            db.session.execute("SELECT 1")
        except exc.SQLAlchemyError:
            db.session.rollback()
            db.session.remove()
            db.engine.dispose()
            # Do NOT recreate tables here, just recover the session

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
    # Helper, aligned with instance/local.db usage
    db_path = path.join(app.instance_path, 'local.db')
    if not path.exists(db_path):
        with app.app_context():
            db.create_all()
            print('Created Database!')
