import random
import threading


class RotorEmulator:
    def __init__(self):
        self.mode = "NORM"
        self._lock = threading.Lock()
        self._phase = 0.0

    def set_mode(self, mode: str):
        with self._lock:
            self.mode = mode

    def get_mode(self) -> str:
        with self._lock:
            return self.mode

    def next_values(self):
        mode = self.get_mode()
        self._phase += random.uniform(0.17, 0.42)
        if mode == "NORM":
            rpm_base = 2970
            vib_base = 1.5
            temp_base = 63
            load_base = 61
            vib_noise = random.gauss(0, 0.14)
        elif mode == "IMBALANCE":
            rpm_base = 2940
            vib_base = 2.55
            temp_base = 73
            load_base = 69
            vib_noise = random.gauss(0, 0.2)
        else:
            rpm_base = 2890
            vib_base = 3.7
            temp_base = 86
            load_base = 77
            vib_noise = random.gauss(0, 0.28)
        harmonic = 0.16 * random.random() * random.choice([-1, 1]) + 0.18 * (1 + random.random()) * abs(random.gauss(0, 0.2))
        raw_vibration = max(0.2, vib_base + vib_noise + harmonic)
        rpm = max(2500.0, rpm_base + random.gauss(0, 20))
        temperature = temp_base + random.gauss(0, 1.3) + raw_vibration * 0.9
        load = load_base + random.gauss(0, 2.0) + (3000 - rpm) / 25
        return rpm, raw_vibration, temperature, load
