from flask import Flask, request
import sqlite3
from datetime import datetime, timedelta
import csv
import os

app = Flask(__name__)

# ---------------- LOCATIONS ----------------
LOCATIONS = [
    "Government Hospital", "Private Hospital", "Primary Health Centre",
    "Ration Shop", "Supermarket", "Shopping Complex", "Shopping Mall",
    "Restaurant", "Hotel", "Bus Stand", "Railway Station", "Metro Station",
    "Airport", "Post Office", "Bank", "ATM", "Police Station",
    "Municipal Office", "Village Office", "Taluk Office",
    "Fuel Station", "Temple", "Mosque", "Church",
    "Public Library", "Examination Centre"
]

AVG_SERVICE_TIME = 2
SERVICE_COUNTERS = 3

# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect("data.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location TEXT,
            time TIMESTAMP
        )
    """)
    conn.close()

def clear_old_entries():
    cutoff = datetime.now() - timedelta(hours=4)
    conn = sqlite3.connect("data.db")
    conn.execute("DELETE FROM queue WHERE time < ?", (cutoff,))
    conn.commit()
    conn.close()

init_db()

# ---------------- BASELINE DATA ----------------
def load_baseline():
    with open("baseline_crowd.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

baseline_data = load_baseline()

# ---------------- CORE LOGIC ----------------
def expected_crowd(location):
    now = datetime.now()
    today = now.strftime("%A")
    hour = now.hour

    today_rows = [
        r for r in baseline_data
        if r["location"] == location and r["day"] == today
    ]

    baseline = 0
    if today_rows:
        hours = sorted(int(r["hour"]) for r in today_rows)
        chosen = max([h for h in hours if h <= hour], default=min(hours))
        baseline = next(
            int(r["baseline_crowd"])
            for r in today_rows
            if int(r["hour"]) == chosen
        )

    conn = sqlite3.connect("data.db")
    registered = conn.execute(
        "SELECT COUNT(*) FROM queue WHERE location=?", (location,)
    ).fetchone()[0]
    conn.close()

    return baseline + registered

def wait_time(crowd):
    return int((crowd / SERVICE_COUNTERS) * AVG_SERVICE_TIME) if crowd else 0

def crowd_level(crowd):
    if crowd <= 50:
        return ("Low", "green")
    elif crowd <= 120:
        return ("Moderate", "orange")
    return ("High", "red")

def best_time(location):
    hours = {}
    for r in baseline_data:
        if r["location"] == location:
            h = int(r["hour"])
            c = int(r["baseline_crowd"])
            hours[h] = min(hours.get(h, c), c)
    if not hours:
        return "N/A"
    h = min(hours, key=hours.get)
    return f"{h}:00 – {h+1}:00"

# ---------------- DASHBOARD DATA ----------------
def dashboard_data():
    data = []
    for loc in LOCATIONS:
        crowd = expected_crowd(loc)
        level, color = crowd_level(crowd)
        data.append({
            "location": loc,
            "crowd": crowd,
            "level": level,
            "color": color,
            "wait": wait_time(crowd),
            "best": best_time(loc)
        })
    return data

# ---------------- UI STYLE ----------------
STYLE = """
<style>
body {
    margin:0;
    font-family:'Segoe UI', sans-serif;
    background:#f4f6fb;
}
.navbar {
    background:#1c2333;
    padding:18px 40px;
    display:flex;
    justify-content:space-between;
    align-items:center;
}
.brand {
    display:flex;
    align-items:center;
    gap:12px;
}
.brand img { height:34px; }
.brand h1 { color:white; font-size:20px; margin:0; }
.brand span { color:#8ea0ff; }

.menu {
    position:relative;
    display:inline-block;
    margin-left:30px;
    color:#cfd6f3;
    cursor:pointer;
}
.menu-content {
    display:none;
    position:absolute;
    background:white;
    min-width:260px;
    box-shadow:0 10px 25px rgba(0,0,0,0.15);
    border-radius:10px;
    z-index:1000;
}
.menu:hover .menu-content { display:block; }
.menu-content a {
    display:block;
    padding:14px 18px;
    color:#333;
    text-decoration:none;
}

.container {
    max-width:1200px;
    margin:60px auto;
    padding:0 20px;
}

.hero {
    background:white;
    padding:60px;
    border-radius:20px;
    display:grid;
    grid-template-columns:1.2fr 1fr;
    gap:40px;
    align-items:center;
    box-shadow:0 20px 40px rgba(0,0,0,0.08);
}

.btn {
    padding:14px 26px;
    border-radius:10px;
    background:#1f4fd8;
    color:white;
    text-decoration:none;
    font-weight:600;
}

.btn.secondary {
    background:#e4e8ff;
    color:#1f4fd8;
    margin-left:10px;
}

table {
    width:100%;
    border-collapse:collapse;
    margin-top:40px;
    background:white;
    border-radius:14px;
    overflow:hidden;
    box-shadow:0 15px 30px rgba(0,0,0,0.08);
}

th, td {
    padding:16px;
    text-align:left;
    font-size:14px;
}

th {
    background:#1c2333;
    color:white;
}

tr:nth-child(even) {
    background:#f7f9ff;
}

.badge {
    padding:6px 14px;
    border-radius:20px;
    color:white;
    font-weight:600;
}
.green { background:#28a745; }
.orange { background:#f0ad4e; }
.red { background:#d9534f; }

footer {
    margin-top:80px;
    background:#1c2333;
    color:#aaa;
    padding:40px;
    text-align:center;
}
</style>
"""

# ---------------- ROUTES ----------------
@app.route("/")
def home():
    clear_old_entries()
    rows = dashboard_data()

    table_rows = "".join(f"""
        <tr>
            <td>{r['location']}</td>
            <td>{r['crowd']}</td>
            <td><span class="badge {r['color']}">{r['level']}</span></td>
            <td>{r['wait']} min</td>
            <td>{r['best']}</td>
        </tr>
    """ for r in rows)

    return f"""
    <html><head><title>Q-SMART by UrbanX</title>{STYLE}</head><body>

    <div class="navbar">
        <div class="brand">
            <img src="/static/Urbanx logo.jpeg">
            <h1>Q-SMART <span>by UrbanX</span></h1>
        </div>
    </div>

    <div class="container">
        <div class="hero">
            <div>
                <h2>Smart Crowd Monitoring Dashboard</h2>
                <p>Real-time expected crowd overview across all locations.</p>
                <a class="btn" href="/status">Check Status</a>
                <a class="btn secondary" href="/join">Join Queue</a>
            </div>
            <img src="/static/Urbanx logo.jpeg" width="100%">
        </div>

        <table>
            <tr>
                <th>Location</th>
                <th>Expected Crowd</th>
                <th>Crowd Level</th>
                <th>Estimated Wait</th>
                <th>Best Time</th>
            </tr>
            {table_rows}
        </table>
    </div>

    <footer>© 2026 Q-SMART by UrbanX</footer>
    </body></html>
    """

# -------- KEEP YOUR /join and /status ROUTES SAME AS BEFORE --------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
