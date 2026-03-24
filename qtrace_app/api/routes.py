from flask import Blueprint, jsonify, request

from qtrace_app.extensions import db
from qtrace_app.models import Telemetry
from qtrace_app.services.telemetry_service import telemetry_service

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/mode", methods=["POST"])
def set_mode():
    payload = request.get_json(silent=True) or {}
    requested_mode = str(payload.get("mode", "NORM")).upper()
    mapped_mode = "FAULT" if requested_mode in {"FAULT", "BEARING_FAULT"} else requested_mode
    if mapped_mode not in {"NORM", "IMBALANCE", "FAULT"}:
        return jsonify({"error": "Unsupported mode"}), 400
    telemetry_service.set_mode(mapped_mode)
    return jsonify({"mode": mapped_mode})


@api_bp.route("/data", methods=["GET"])
def get_data():
    points = (
        db.session.query(Telemetry)
        .order_by(Telemetry.timestamp.desc())
        .limit(100)
        .all()
    )
    points = list(reversed(points))
    if not points:
        telemetry_service.store_telemetry_sample()
        points = (
            db.session.query(Telemetry)
            .order_by(Telemetry.timestamp.desc())
            .limit(100)
            .all()
        )
        points = list(reversed(points))
    latest = points[-1]
    mu = float(telemetry_service.qtrace.mu)
    sigma = float(telemetry_service.qtrace.sigma)
    lower_limit = max(0.0, mu - 3 * sigma)
    upper_limit = mu + 3 * sigma
    payload = {
        "mode": telemetry_service.get_mode(),
        "prediction": telemetry_service.latest_prediction,
        "limits": {
            "mu": round(mu, 4),
            "sigma": round(sigma, 4),
            "lower": round(lower_limit, 4),
            "upper": round(upper_limit, 4),
        },
        "latest": {
            "timestamp": latest.timestamp.isoformat(),
            "rpm": latest.rpm,
            "vibration_raw": latest.vibration_raw,
            "vibration_filtered": latest.vibration_filtered,
            "temperature": latest.temperature,
            "load": latest.load,
            "anomaly_score": latest.anomaly_score,
            "is_anomaly": latest.is_anomaly,
            "state_label": latest.state_label,
        },
        "series": [
            {
                "timestamp": row.timestamp.isoformat(),
                "rpm": row.rpm,
                "vibration_raw": row.vibration_raw,
                "vibration_filtered": row.vibration_filtered,
                "temperature": row.temperature,
                "load": row.load,
                "anomaly_score": row.anomaly_score,
                "is_anomaly": row.is_anomaly,
                "state_label": row.state_label,
            }
            for row in points
        ],
    }
    return jsonify(payload)
