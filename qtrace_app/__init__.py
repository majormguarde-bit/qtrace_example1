from flask import Flask

from qtrace_app.api.routes import api_bp
from qtrace_app.extensions import db, migrate
from qtrace_app.main.routes import main_bp
from qtrace_app.services.telemetry_service import telemetry_service


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///qtrace_monitor.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    migrate.init_app(app, db)

    from qtrace_app import models

    _ = models
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    telemetry_service.init_app(app)
    return app
