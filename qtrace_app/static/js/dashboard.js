const chartCtx = document.getElementById("vibrationChart");
const vibrationChart = new Chart(chartCtx, {
    type: "line",
    data: {
        labels: [],
        datasets: [
            {
                label: "Нижняя граница 3σ",
                data: [],
                borderColor: "rgba(113, 221, 161, 0.9)",
                backgroundColor: "rgba(113, 221, 161, 0.00)",
                borderWidth: 1.3,
                borderDash: [6, 6],
                pointRadius: 0,
                tension: 0,
                order: 1
            },
            {
                label: "Допустимый коридор 3σ",
                data: [],
                borderColor: "rgba(113, 221, 161, 0.9)",
                backgroundColor: "rgba(113, 221, 161, 0.16)",
                borderWidth: 1.3,
                borderDash: [6, 6],
                pointRadius: 0,
                fill: "-1",
                tension: 0,
                order: 1
            },
            {
                label: "Raw",
                data: [],
                borderColor: "#b7cbec",
                backgroundColor: "transparent",
                tension: 0.2,
                borderWidth: 1.8,
                pointRadius: 0,
                order: 2
            },
            {
                label: "Kalman",
                data: [],
                borderColor: "#ffd166",
                backgroundColor: "transparent",
                tension: 0.28,
                borderWidth: 2.4,
                pointRadius: 0,
                order: 3
            }
        ]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { labels: { color: "#f2f7ff" } }
        },
        scales: {
            x: { ticks: { color: "#d8e6fa" }, grid: { color: "#3e4f69" } },
            y: { ticks: { color: "#d8e6fa" }, grid: { color: "#3e4f69" } }
        }
    }
});

function modeLabel(mode) {
    if (mode === "FAULT") return "Дефект подшипника";
    if (mode === "IMBALANCE") return "Дисбаланс";
    return "Норма";
}

function stateClass(stateLabel) {
    if (stateLabel === "BEARING_FAULT") return "state-BEARING_FAULT";
    if (stateLabel === "IMBALANCE") return "state-IMBALANCE";
    return "state-NORM";
}

async function setMode(mode) {
    await fetch("/api/mode", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode })
    });
    refresh();
}

function updateEvents(rows) {
    const body = document.getElementById("eventsBody");
    body.innerHTML = "";
    rows.slice(-10).reverse().forEach((row) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${row.timestamp.slice(11, 19)}</td>
            <td>${row.state_label}</td>
            <td>${row.anomaly_score.toFixed(2)}</td>
        `;
        body.appendChild(tr);
    });
}

function computeCorridor(rows) {
    const values = rows.map((row) => row.vibration_filtered);
    if (values.length === 0) {
        return { lower: 0, upper: 0 };
    }
    const mean = values.reduce((acc, value) => acc + value, 0) / values.length;
    const variance = values.reduce((acc, value) => acc + (value - mean) ** 2, 0) / values.length;
    const std = Math.sqrt(variance);
    const lower = Math.max(0, mean - 3 * std);
    const upper = mean + 3 * std;
    return { lower, upper };
}

async function refresh() {
    const response = await fetch("/api/data");
    const payload = await response.json();
    const rows = payload.series;
    const latest = payload.latest;
    const corridor = payload.limits ?? computeCorridor(rows);
    const lowerLimit = corridor.lower;
    const upperLimit = corridor.upper;

    // Обновление метрик
    document.getElementById("modeValue").textContent = modeLabel(payload.mode);
    document.getElementById("vibrationValue").textContent = `${latest.vibration_filtered.toFixed(3)} (raw ${latest.vibration_raw.toFixed(3)})`;
    document.getElementById("temperatureValue").textContent = latest.temperature.toFixed(2);
    document.getElementById("rpmValue").textContent = latest.rpm.toFixed(0);
    document.getElementById("scoreValue").textContent = latest.anomaly_score.toFixed(2);
    document.getElementById("anomalyFlag").textContent = latest.is_anomaly ? "Да" : "Нет";

    // Обновление прогноза (RUL)
    const prediction = payload.prediction;
    const rulValueEl = document.getElementById("rulValue");
    const rulStatusEl = document.getElementById("rulStatus");

    if (prediction && rulValueEl && rulStatusEl) {
        rulValueEl.textContent = `${prediction.days} дн.`;
        rulStatusEl.textContent = `${prediction.status} (${Math.round(prediction.confidence * 100)}%)`;

        if (prediction.days < 7) {
            rulValueEl.className = "metric text-danger";
            rulStatusEl.className = "small-note mt-1 text-danger";
        } else if (prediction.days < 30) {
            rulValueEl.className = "metric text-warning";
            rulStatusEl.className = "small-note mt-1 text-warning";
        } else {
            rulValueEl.className = "metric text-success";
            rulStatusEl.className = "small-note mt-1 text-success";
        }
    }

    // Статус и аномалия
    const stateChip = document.getElementById("stateChip");
    stateChip.textContent = latest.state_label;
    stateChip.className = `state-chip ${stateClass(latest.state_label)}`;

    const anomalyCard = document.getElementById("anomalyFlag").closest(".card");
    if (latest.is_anomaly) {
        anomalyCard.classList.add("state-ANOMALY");
    } else {
        anomalyCard.classList.remove("state-ANOMALY");
    }

    vibrationChart.data.labels = rows.map((row) => row.timestamp.slice(11, 19));
    vibrationChart.data.datasets[0].data = rows.map(() => lowerLimit);
    vibrationChart.data.datasets[1].data = rows.map(() => upperLimit);
    vibrationChart.data.datasets[2].data = rows.map((row) => row.vibration_raw);
    vibrationChart.data.datasets[3].data = rows.map((row) => row.vibration_filtered);
    vibrationChart.update();
    updateEvents(rows);
}

refresh();
setInterval(refresh, 2000);
