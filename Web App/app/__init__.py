from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config.config import Config

# Initialize extensions
db = SQLAlchemy()

def create_app():
    """Application factory pattern."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions with app
    db.init_app(app)

    # # Register blueprints
    from . import routes
    app.register_blueprint(routes.main_bp)

    return app
