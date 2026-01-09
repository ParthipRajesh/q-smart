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

    today_rows = [r for r in baseline_data if r["location"] == location and r["day"] == today]
    baseline = 0

    if today_rows:
        hours = sorted(int(r["hour"]) for r in today_rows)
        chosen = max([h for h in hours if h <= hour], default=min(hours))
        baseline = next(int(r["baseline_crowd"]) for r in today_rows if int(r["hour"]) == chosen)

    conn = sqlite3.connect("data.db")
    registered = conn.execute(
        "SELECT COUNT(*) FROM queue WHERE location=?", (location,)
    ).fetchone()[0]
    conn.close()

    return baseline + registered

def wait_time(crowd):
    return int((crowd / SERVICE_COUNTERS) * AVG_SERVICE_TIME) if crowd > 0 else 0

def crowd_level(crowd):
    if crowd <= 50:
        return ("Low", "green")
    elif crowd <= 120:
        return ("Moderate", "orange")
    else:
        return ("High", "red")

def best_time(location):
    hours = {}
    for r in baseline_data:
        if r["location"] == location:
            h = int(r["hour"])
            c = int(r["baseline_crowd"])
            hours[h] = min(hours.get(h, c), c)
    if not hours:
        return "Data unavailable"
    h = min(hours, key=hours.get)
    return f"{h}:00 – {h+1}:00"

# ---------------- UI STYLE ----------------
STYLE = """
<style>
body {
    font-family: 'Segoe UI', sans-serif;
    background:#f2f4f8;
    margin:0;
}
.container {
    max-width:900px;
    margin:60px auto;
    background:white;
    padding:40px;
    border-radius:14px;
    box-shadow:0 15px 40px rgba(0,0,0,0.08);
}
h1 {
    color:#1f4fd8;
    font-size:36px;
}
h2 {
    margin-top:0;
}
.nav a {
    margin-right:20px;
    text-decoration:none;
    font-weight:600;
    color:#1f4fd8;
}
.hero {
    display:flex;
    justify-content:space-between;
    align-items:center;
}
.hero-text {
    max-width:500px;
}
.hero p {
    color:#555;
    font-size:18px;
}
.btn {
    display:inline-block;
    margin-top:20px;
    padding:12px 22px;
    background:#1f4fd8;
    color:white;
    text-decoration:none;
    border-radius:8px;
    font-weight:600;
}
.card-grid {
    display:grid;
    grid-template-columns:repeat(auto-fit, minmax(220px,1fr));
    gap:20px;
    margin-top:30px;
}
.card {
    background:#f9fafc;
    padding:20px;
    border-radius:12px;
}
.badge {
    padding:6px 14px;
    border-radius:20px;
    font-weight:600;
    color:white;
    display:inline-block;
}
.green { background:#28a745; }
.orange { background:#f0ad4e; }
.red { background:#d9534f; }
select, input {
    padding:10px;
    margin-top:10px;
    width:100%;
}
</style>
"""

# ---------------- ROUTES ----------------
@app.route("/")
def home():
    clear_old_entries()
    return f"""
    <html><head><title>Q-SMART</title>{STYLE}</head><body>
    <div class="container">
        <div class="hero">
            <div class="hero-text">
                <h1>Q-SMART</h1>
                <p>Smart Crowd Prediction & Queue Management System</p>
                <a class="btn" href="/join">Join Queue</a>
                <a class="btn" style="background:#555" href="/status">Check Status</a>
            </div>
        </div>
    </div></body></html>
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
            <div class="card"><b>Expected Crowd</b><br><h2>{crowd}</h2></div>
            <div class="card"><b>Crowd Level</b><br><span class="badge {color}">{level}</span></div>
            <div class="card"><b>Estimated Waiting Time</b><br><h3>{wait_time(crowd)} min</h3></div>
            <div class="card"><b>Best Time to Visit</b><br><h3>{best_time(location)}</h3></div>
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
