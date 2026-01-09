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
    margin:0;
    font-family:'Segoe UI', sans-serif;
    background:#f4f6fa;
}

.navbar {
    display:flex;
    justify-content:space-between;
    align-items:center;
    padding:16px 40px;
    background:#1e293b;
    color:white;
}

.brand {
    display:flex;
    align-items:center;
    gap:12px;
    font-size:20px;
    font-weight:600;
}

.brand img {
    height:40px;
}

.nav-right {
    display:flex;
    align-items:center;
    gap:30px;
}

.nav-right a, .dropbtn {
    color:white;
    text-decoration:none;
    background:none;
    border:none;
    font-size:16px;
    cursor:pointer;
}

.dropdown {
    position:relative;
}

.dropdown-content {
    display:none;
    position:absolute;
    top:40px;
    background:white;
    min-width:220px;
    box-shadow:0 10px 25px rgba(0,0,0,0.15);
    border-radius:8px;
    z-index:100;
}

.dropdown-content a {
    display:block;
    padding:10px 14px;
    color:#333;
    text-decoration:none;
}

.dropdown-content a:hover {
    background:#f1f5f9;
}

.dropdown:hover .dropdown-content {
    display:block;
}

.solutions-scroll {
    max-height:300px;
    overflow-y:auto;
}

.container {
    max-width:1000px;
    margin:60px auto;
    background:white;
    padding:50px;
    border-radius:16px;
    box-shadow:0 20px 50px rgba(0,0,0,0.08);
}

h1, h2 {
    margin-top:0;
}

.btn {
    background:#2563eb;
    color:white;
    border:none;
    padding:14px 22px;
    border-radius:10px;
    font-size:16px;
    font-weight:600;
    cursor:pointer;
}

select {
    width:100%;
    padding:14px;
    font-size:16px;
    border-radius:10px;
    border:1px solid #ccc;
    margin-bottom:20px;
}

.card-grid {
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(200px,1fr));
    gap:20px;
    margin-top:30px;
}

.card {
    background:#f9fafc;
    padding:20px;
    border-radius:14px;
    text-align:center;
}

.badge {
    display:inline-block;
    margin-top:10px;
    padding:8px 16px;
    border-radius:20px;
    color:white;
    font-weight:600;
}

.green {background:#22c55e;}
.orange {background:#f59e0b;}
.red {background:#ef4444;}
</style>
"""

# ---------------- NAVBAR ----------------
solutions_menu = "".join(
    f'<a href="/status?location={l}">{l}</a>' for l in LOCATIONS
)

NAVBAR = f"""
<div class="navbar">
  <div class="brand">
    <img src="/static/Urbanx logo.jpeg">
    Q-SMART by UrbanX
  </div>

  <div class="nav-right">
    <div class="dropdown">
      <button class="dropbtn">Company ▾</button>
      <div class="dropdown-content">
        <a href="/company">About UrbanX</a>
      </div>
    </div>

    <div class="dropdown">
      <button class="dropbtn">Solutions ▾</button>
      <div class="dropdown-content solutions-scroll">
        {solutions_menu}
      </div>
    </div>
  </div>
</div>
"""

# ---------------- ROUTES ----------------
@app.route("/")
def home():
    clear_old_entries()
    return f"""
    <html><head><title>Q-SMART</title>{STYLE}</head><body>
    {NAVBAR}
    <div class="container">
        <h1>Experience Smarter Crowd Planning</h1>
        <p>Predict queues, avoid peak hours, and plan visits efficiently.</p>
        <a class="btn" href="/status">Check Crowd Status</a>
        <a class="btn" style="background:#e5e7eb;color:#000;margin-left:10px" href="/join">Join Queue</a>
    </div>
    </body></html>
    """

@app.route("/company")
def company():
    return f"""
    <html><head><title>Company</title>{STYLE}</head><body>
    {NAVBAR}
    <div class="container" style="text-align:center">
        <img src="/static/Urbanx logo.jpeg" style="height:120px">
        <h1>UrbanX</h1>
        <p>Smart urban analytics for better public experiences.</p>
    </div>
    </body></html>
    """

@app.route("/join")
def join():
    options = "".join(f"<option>{l}</option>" for l in LOCATIONS)
    return f"""
    <html><head><title>Join Queue</title>{STYLE}</head><body>
    {NAVBAR}
    <div class="container">
        <h2>Join Queue</h2>
        <form method="post" action="/add">
            <select name="location">{options}</select>
            <button class="btn">Register</button>
        </form>
    </div>
    </body></html>
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
    {NAVBAR}
    <div class="container" style="text-align:center">
        <h2>Registered Successfully ✅</h2>
        <a class="btn" href="/status">Check Status</a>
    </div>
    </body></html>
    """

@app.route("/status")
def status():
    selected = request.args.get("location")
    options = "".join(
        f'<option {"selected" if l==selected else ""}>{l}</option>'
        for l in LOCATIONS
    )

    output = ""
    if selected:
        crowd = expected_crowd(selected)
        level, color = crowd_level(crowd)
        output = f"""
        <div class="card-grid">
            <div class="card"><b>Expected Crowd</b><h2>{crowd}</h2></div>
            <div class="card"><b>Crowd Level</b><br><span class="badge {color}">{level}</span></div>
            <div class="card"><b>Waiting Time</b><h2>{wait_time(crowd)} min</h2></div>
            <div class="card"><b>Best Time</b><h2>{best_time(selected)}</h2></div>
        </div>
        """

    return f"""
    <html><head><title>Status</title>{STYLE}</head><body>
    {NAVBAR}
    <div class="container">
        <h2>Check Queue Status</h2>
        <form method="get">
            <select name="location">{options}</select>
            <button class="btn">Check Status</button>
        </form>
        {output}
    </div>
    </body></html>
    """

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
