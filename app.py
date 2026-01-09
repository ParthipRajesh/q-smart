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

AVG_SERVICE_TIME = 2        # minutes per person
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
        chosen_hour = max([h for h in hours if h <= hour], default=min(hours))
        baseline = next(
            int(r["baseline_crowd"])
            for r in today_rows
            if int(r["hour"]) == chosen_hour
        )

    conn = sqlite3.connect("data.db")
    registered = conn.execute(
        "SELECT COUNT(*) FROM queue WHERE location=?", (location,)
    ).fetchone()[0]
    conn.close()

    return baseline + registered

def wait_time(crowd):
    if crowd == 0:
        return 0
    return int((crowd / SERVICE_COUNTERS) * AVG_SERVICE_TIME)

def crowd_level(crowd):
    if crowd <= 50:
        return ("Low", "green")
    elif crowd <= 120:
        return ("Moderate", "orange")
    else:
        return ("High", "red")

def best_time(location):
    hour_map = {}
    for r in baseline_data:
        if r["location"] == location:
            h = int(r["hour"])
            c = int(r["baseline_crowd"])
            hour_map[h] = min(hour_map.get(h, c), c)

    if not hour_map:
        return "Data unavailable"

    best = min(hour_map, key=hour_map.get)
    return f"{best}:00 – {best+1}:00"

# ---------------- UI STYLE ----------------
STYLE = """
<style>
:root {
    --primary:#1f4fd8;
    --dark:#1c2333;
    --bg:#f4f6fb;
    --card:#ffffff;
    --text:#333;
}
* { box-sizing:border-box; }
body {
    margin:0;
    font-family:'Segoe UI', sans-serif;
    background:var(--bg);
    color:var(--text);
}
.navbar {
    background:var(--dark);
    padding:18px 40px;
    display:flex;
    justify-content:space-between;
    align-items:center;
}
.navbar h1 {
    color:white;
    font-size:22px;
    margin:0;
}
.navbar a {
    color:#cfd6f3;
    margin-left:20px;
    text-decoration:none;
    font-weight:500;
}
.container {
    max-width:1100px;
    margin:60px auto;
    padding:0 20px;
}
.hero {
    display:grid;
    grid-template-columns:1.2fr 1fr;
    gap:40px;
    align-items:center;
}
.hero h2 {
    font-size:42px;
    margin:0;
}
.hero p {
    font-size:18px;
    color:#555;
    margin:20px 0;
}
.btn {
    display:inline-block;
    padding:14px 26px;
    border-radius:10px;
    background:var(--primary);
    color:white;
    text-decoration:none;
    font-weight:600;
    margin-right:12px;
}
.btn.secondary {
    background:#e4e8ff;
    color:var(--primary);
}
.card-grid {
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(240px,1fr));
    gap:24px;
    margin-top:70px;
}
.card {
    background:var(--card);
    padding:26px;
    border-radius:16px;
    box-shadow:0 12px 30px rgba(0,0,0,0.08);
}
.card h3 {
    margin-top:0;
}
.badge {
    padding:8px 16px;
    border-radius:20px;
    font-weight:600;
    color:white;
    display:inline-block;
}
.green { background:#28a745; }
.orange { background:#f0ad4e; }
.red { background:#d9534f; }
footer {
    margin-top:80px;
    padding:40px;
    background:#1c2333;
    color:#aaa;
    text-align:center;
}
select, input {
    width:100%;
    padding:12px;
    margin-top:10px;
    border-radius:8px;
    border:1px solid #ccc;
}
</style>
"""

# ---------------- ROUTES ----------------
@app.route("/")
def home():
    clear_old_entries()
    return f"""
    <html>
    <head><title>Q-SMART</title>{STYLE}</head>
    <body>

    <div class="navbar">
        <h1>Q-SMART</h1>
        <div>
            <a href="/">Home</a>
            <a href="/join">Join Queue</a>
            <a href="/status">Check Status</a>
        </div>
    </div>

    <div class="container">
        <div class="hero">
            <div>
                <h2>Experience Smarter Crowd Planning</h2>
                <p>
                    Predict queues, avoid peak hours, and plan visits efficiently
                    using historical trends and real-time registrations.
                </p>
                <a class="btn" href="/status">Check Crowd Status</a>
                <a class="btn secondary" href="/join">Join Queue</a>
            </div>
            <div>
                <img src="https://illustrations.popsy.co/gray/work-from-home.svg" width="100%">
            </div>
        </div>

        <div class="card-grid">
            <div class="card">
                <h3>📊 Expected Crowd</h3>
                <p>Calculated using historical patterns + registered users.</p>
            </div>
            <div class="card">
                <h3>⏱ Waiting Time</h3>
                <p>Estimated based on service counters and crowd size.</p>
            </div>
            <div class="card">
                <h3>📅 Best Time</h3>
                <p>Lowest crowd hour suggested from weekly data.</p>
            </div>
            <div class="card">
                <h3>🔒 Privacy First</h3>
                <p>No personal data. No hardware. Fully software-based.</p>
            </div>
        </div>
    </div>

    <footer>
        © 2026 Q-SMART • Smart Crowd Prediction Platform
    </footer>

    </body>
    </html>
    """

@app.route("/join")
def join():
    options = "".join(f"<option>{l}</option>" for l in LOCATIONS)
    return f"""
    <html><head>{STYLE}</head><body>
    <div class="container">
        <h2>Join Queue</h2>
        <form method="post" action="/add">
            <select name="location">{options}</select>
            <input type="submit" value="Register" class="btn">
        </form>
    </div></body></html>
    """

@app.route("/add", methods=["POST"])
def add():
    conn = sqlite3.connect("data.db")
    conn.execute(
        "INSERT INTO queue (location, time) VALUES (?, ?)",
        (request.form["location"], datetime.now())
    )
    conn.commit()
    conn.close()
    return f"""
    <html><head>{STYLE}</head><body>
    <div class="container">
        <h2>Registered Successfully ✅</h2>
        <a class="btn" href="/">Go Home</a>
    </div></body></html>
    """

@app.route("/status")
def status():
    location = request.args.get("location")
    options = "".join(f"<option>{l}</option>" for l in LOCATIONS)
    output = ""

    if location:
        crowd = expected_crowd(location)
        level, color = crowd_level(crowd)
        output = f"""
        <div class="card-grid">
            <div class="card"><h3>Expected Crowd</h3><h2>{crowd}</h2></div>
            <div class="card"><h3>Crowd Level</h3><span class="badge {color}">{level}</span></div>
            <div class="card"><h3>Waiting Time</h3><h3>{wait_time(crowd)} min</h3></div>
            <div class="card"><h3>Best Time</h3><h3>{best_time(location)}</h3></div>
        </div>
        """

    return f"""
    <html><head>{STYLE}</head><body>
    <div class="container">
        <h2>Check Queue Status</h2>
        <form method="get">
            <select name="location">{options}</select>
            <input type="submit" value="Check Status" class="btn">
        </form>
        {output}
    </div></body></html>
    """

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
