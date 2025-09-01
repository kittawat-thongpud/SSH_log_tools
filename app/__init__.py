from flask import Flask
from .db import init_db
import logging
import os
import sys


def _base_path() -> str:
    """Return base path for templates/static accommodating PyInstaller."""
    # When bundled via PyInstaller the package lives under ``_MEIPASS``. The
    # assets (templates/static) are collected into ``app`` inside that temp
    # folder, so adjust the base accordingly.
    mei = getattr(sys, "_MEIPASS", None)
    if mei and os.path.isdir(os.path.join(mei, "app")):
        return os.path.join(mei, "app")
    return os.path.dirname(os.path.abspath(__file__))


def create_app():
    base = _base_path()
    app = Flask(
        __name__,
        static_folder=os.path.join(base, "static"),
        template_folder=os.path.join(base, "templates"),
    )
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
