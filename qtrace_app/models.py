from datetime import datetime

from qtrace_app.extensions import db


class Telemetry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    rpm = db.Column(db.Float, nullable=False)
    vibration_raw = db.Column(db.Float, nullable=False)
    vibration_filtered = db.Column(db.Float, nullable=False)
    temperature = db.Column(db.Float, nullable=False)
    load = db.Column(db.Float, nullable=False)
    anomaly_score = db.Column(db.Float, nullable=False)
    is_anomaly = db.Column(db.Boolean, nullable=False, default=False)
    state_label = db.Column(db.String(32), nullable=False, default="NORM")
