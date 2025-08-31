from flask import Flask
from .db import init_db
import logging


def create_app():
    app = Flask(__name__, static_folder="static", template_folder="templates")
    # Initialize local SQLite database
    try:
        init_db()
    except Exception:
        pass
    logging.getLogger(__name__).info("Creating Flask app and registering blueprints")

    # Defer route registration to keep init lightweight
    from .routes import bp as api_bp
    app.register_blueprint(api_bp)

    from .views import bp as views_bp
    app.register_blueprint(views_bp)

    from .docs import bp as docs_bp
    app.register_blueprint(docs_bp)

    return app
