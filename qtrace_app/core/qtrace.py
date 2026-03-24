from collections import deque


class QTraceCore:
    def __init__(self):
        self.process_noise = 0.02
        self.measurement_noise = 0.35
        self.estimate_error = 1.0
        self.estimate = 1.5
        self.window = deque(maxlen=80)
        self.mu = 1.6
        self.sigma = 0.25
        self.som_vectors = {
            "NORM": (1.5, 65.0, 62.0),
            "IMBALANCE": (2.6, 74.0, 70.0),
            "BEARING_FAULT": (3.8, 88.0, 78.0),
        }
        self.rul_window = deque(maxlen=30)  # Окно для оценки тренда

    def predict_rul(self, score: float) -> dict:
        """
        Прогноз RUL (Remaining Useful Life) на основе динамики Anomaly Score.
        """
        self.rul_window.append(score)
        
        # Если данных мало или скор низкий - считаем узел здоровым
        if len(self.rul_window) < 10 or score < 0.2:
            return {"days": 365, "status": "Healthy", "confidence": 0.95}

        # Линейная аппроксимация тренда
        n = len(self.rul_window)
        x = list(range(n))
        y = list(self.rul_window)
        
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi * xi for xi in x)
        
        denominator = (n * sum_x2 - sum_x * sum_x)
        if abs(denominator) < 1e-7:
            slope = 0
        else:
            slope = (n * sum_xy - sum_x * sum_y) / denominator

        # Порог отказа = 1.0
        if slope <= 0:
            # Тренд стабилен или падает
            if score > 0.7:
                return {"days": 7, "status": "Critical", "confidence": 0.6}
            return {"days": 180, "status": "Stable", "confidence": 0.8}

        # Экстраполяция: сколько шагов до score = 1.0
        # 1 шаг = 1 секунда (в эмуляторе), но для "реалистичности" считаем в днях
        steps_to_failure = (1.0 - score) / slope
        
        # Масштабируем секунды в "условные дни" для демонстрации
        days = int(steps_to_failure * 2) 
        
        if days < 3:
            status = "Immediate Action"
        elif days < 14:
            status = "Maintenance Required"
        else:
            status = "Degrading"
            
        return {
            "days": max(1, days),
            "status": status,
            "confidence": round(max(0.4, 1.0 - (score * 0.5)), 2)
        }

    def kalman_filter(self, measurement: float) -> float:
        prediction_error = self.estimate_error + self.process_noise
        gain = prediction_error / (prediction_error + self.measurement_noise)
        self.estimate = self.estimate + gain * (measurement - self.estimate)
        self.estimate_error = (1 - gain) * prediction_error
        return self.estimate

    def update_shewhart(self, filtered_value: float) -> bool:
        self.window.append(filtered_value)
        if len(self.window) > 15:
            mean = sum(self.window) / len(self.window)
            variance = sum((x - mean) ** 2 for x in self.window) / len(self.window)
            std = variance ** 0.5
            if std > 0.0001:
                self.mu = mean
                self.sigma = std
        upper = self.mu + 3 * self.sigma
        return filtered_value > upper

    def classify(self, filtered_vibration: float, temperature: float, load: float) -> str:
        distances = {}
        for state, vector in self.som_vectors.items():
            dv = filtered_vibration - vector[0]
            dt = temperature - vector[1]
            dl = load - vector[2]
            distances[state] = (dv * dv + dt * dt + dl * dl) ** 0.5
        return min(distances, key=distances.get)

    def anomaly_score(self, filtered_vibration: float, temperature: float) -> float:
        vib_component = max(0.0, (filtered_vibration - self.mu) / max(self.sigma, 0.05))
        temp_component = max(0.0, (temperature - 70.0) / 18.0)
        return round(min(1.0, 0.15 * vib_component + 0.5 * temp_component), 3)

    def analyze(self, raw_vibration: float, temperature: float, load: float):
        filtered = self.kalman_filter(raw_vibration)
        shewhart_anomaly = self.update_shewhart(filtered)
        state_label = self.classify(filtered, temperature, load)
        score = self.anomaly_score(filtered, temperature)
        is_anomaly = shewhart_anomaly or score > 0.67 or state_label == "BEARING_FAULT"
        
        # Добавляем расчет прогноза RUL
        prediction = self.predict_rul(score)
        
        return filtered, is_anomaly, state_label, score, prediction
