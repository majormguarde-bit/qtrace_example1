import threading
import time

from flask import Flask

from qtrace_app.core.emulator import RotorEmulator
from qtrace_app.core.qtrace import QTraceCore
from qtrace_app.extensions import db
from qtrace_app.models import Telemetry


class TelemetryService:
    def __init__(self):
        self.qtrace = QTraceCore()
        self.emulator = RotorEmulator()
        self._thread_lock = threading.Lock()
        self._thread = None
        self._app = None
        self.latest_prediction = {"days": 365, "status": "Healthy", "confidence": 0.95}

    def init_app(self, app: Flask):
        self._app = app
        with app.app_context():
            db.create_all()
            if db.session.query(Telemetry.id).count() == 0:
                for _ in range(12):
                    self.store_telemetry_sample()
        self.start_emulator()

    def set_mode(self, mode: str):
        self.emulator.set_mode(mode)

    def get_mode(self) -> str:
        return self.emulator.get_mode()

    def store_telemetry_sample(self):
        rpm, vibration_raw, temperature, load = self.emulator.next_values()
        vibration_filtered, is_anomaly, state_label, score, prediction = self.qtrace.analyze(vibration_raw, temperature, load)
        
        self.latest_prediction = prediction
        
        sample = Telemetry(
            rpm=round(rpm, 2),
            vibration_raw=round(vibration_raw, 3),
            vibration_filtered=round(vibration_filtered, 3),
            temperature=round(temperature, 2),
            load=round(load, 2),
            anomaly_score=score,
            is_anomaly=is_anomaly,
            state_label=state_label,
        )
        db.session.add(sample)
        db.session.commit()
        samples_count = db.session.query(Telemetry.id).count()
        if samples_count > 100:
            overflow = samples_count - 100
            old_ids = [item[0] for item in db.session.query(Telemetry.id).order_by(Telemetry.id.asc()).limit(overflow).all()]
            if old_ids:
                db.session.query(Telemetry).filter(Telemetry.id.in_(old_ids)).delete(synchronize_session=False)
                db.session.commit()

    def _telemetry_loop(self):
        with self._app.app_context():
            while True:
                self.store_telemetry_sample()
                time.sleep(1.0)

    def start_emulator(self):
        with self._thread_lock:
            if self._thread and self._thread.is_alive():
                return
            self._thread = threading.Thread(target=self._telemetry_loop, daemon=True)
            self._thread.start()


telemetry_service = TelemetryService()
