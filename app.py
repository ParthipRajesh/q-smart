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
        return "Data unavailable"
    h = min(hours, key=hours.get)
    return f"{h}:00 – {h+1}:00"

# ---------------- UI STYLE ----------------
STYLE = """
<style>
body {
    margin:0;
    font-family:'Segoe UI', sans-serif;
    background:#f4f6fb;
}

/* NAVBAR */
.navbar {
    background:#1c2333;
    padding:18px 40px;
    display:flex;
    justify-content:space-between;
    align-items:center;
    position:relative;
    z-index:1000;
}

.brand {
    display:flex;
    align-items:center;
    gap:12px;
}
.brand img { height:34px; }
.brand h1 {
    color:white;
    font-size:20px;
    margin:0;
}
.brand span { color:#8ea0ff; }

/* DROPDOWN */
.menu {
    position:relative;
    display:inline-block;
    margin-left:30px;
    color:#cfd6f3;
    cursor:pointer;
    font-weight:500;
}

.menu-content {
    display:none;
    position:absolute;
    top:38px;
    right:0;
    background:white;
    min-width:260px;
    box-shadow:0 10px 25px rgba(0,0,0,0.15);
    border-radius:10px;
    z-index:2000;
}

.menu-content a {
    display:block;
    padding:14px 18px;
    color:#333;
    text-decoration:none;
    font-size:14px;
}

.menu-content a:hover {
    background:#f2f4fb;
}

.menu:hover .menu-content {
    display:block;
}

/* LAYOUT */
.container {
    max-width:1100px;
    margin:70px auto;
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

.hero h2 { font-size:42px; }
.hero p { font-size:18px; color:#555; }

.btn {
    padding:14px 26px;
    border-radius:10px;
    background:#1f4fd8;
    color:white;
    text-decoration:none;
    font-weight:600;
    border:none;
    cursor:pointer;
}

.btn.secondary {
    background:#e4e8ff;
    color:#1f4fd8;
    margin-left:10px;
}

.card {
    background:white;
    padding:30px;
    border-radius:16px;
    box-shadow:0 12px 30px rgba(0,0,0,0.08);
}

.card-grid {
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
    gap:24px;
    margin-top:40px;
}

select, input {
    width:100%;
    padding:14px;
    margin-top:12px;
    border-radius:8px;
    border:1px solid #ccc;
}

.badge {
    display:inline-block;
    margin-top:8px;
    padding:8px 16px;
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
    return f"""
    <html><head><title>Q-SMART by UrbanX</title>{STYLE}</head><body>

    <div class="navbar">
        <div class="brand">
            <img src="/static/Urbanx logo.jpeg">
            <h1>Q-SMART <span>by UrbanX</span></h1>
        </div>
        <div>
            <div class="menu">Company
                <div class="menu-content">
                    <a href="/company">About UrbanX</a>
                    <a href="/vision">Vision & Mission</a>
                    <a href="/contact">Contact</a>
                </div>
            </div>
            <div class="menu">Solutions
                <div class="menu-content">
                    {''.join(f'<a href="/status?location={l}">{l}</a>' for l in LOCATIONS)}
                </div>
            </div>
        </div>
    </div>

    <div class="container">
        <div class="hero">
            <div>
                <h2>Experience Smarter Crowd Planning</h2>
                <p>Predict queues, avoid peak hours, and plan visits efficiently.</p>
                <a class="btn" href="/status">Check Crowd Status</a>
                <a class="btn secondary" href="/join">Join Queue</a>
            </div>
            <div>
                <img src="/static/Urbanx logo.jpeg" width="100%">
            </div>
        </div>
    </div>

    <footer>© 2026 Q-SMART by UrbanX</footer>
    </body></html>
    """

@app.route("/company")
def company():
    return f"""
    <html><head>{STYLE}</head><body>
    <div class="container">
        <div class="card">
            <h2>About UrbanX</h2>
            <p>UrbanX is a smart-city focused initiative working on intelligent
            crowd analytics, urban mobility, and queue optimization using
            data-driven approaches.</p>
        </div>
    </div></body></html>
    """

@app.route("/vision")
def vision():
    return f"""
    <html><head>{STYLE}</head><body>
    <div class="container">
        <div class="card">
            <h2>Vision & Mission</h2>
            <p>Our mission is to reduce waiting times, improve public access,
            and enable smarter urban planning using predictive analytics.</p>
        </div>
    </div></body></html>
    """

@app.route("/contact")
def contact():
    return f"""
    <html><head>{STYLE}</head><body>
    <div class="container">
        <div class="card">
            <h2>Contact</h2>
            <p>Email: urbanx.smart@gmail.com</p>
        </div>
    </div></body></html>
    """

@app.route("/join")
def join():
    options = "".join(f"<option>{l}</option>" for l in LOCATIONS)
    return f"""
    <html><head>{STYLE}</head><body>
    <div class="container">
        <div class="card">
            <h2>Join Queue</h2>
            <form method="post" action="/add">
                <select name="location">{options}</select>
                <input type="submit" value="Register" class="btn">
            </form>
        </div>
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
        <div class="card">
            <h2>Registered Successfully</h2>
            <a class="btn" href="/">Return Home</a>
        </div>
    </div></body></html>
    """

@app.route("/status")
def status():
    location = request.args.get("location")
    options = "".join(
        f'<option {"selected" if l==location else ""}>{l}</option>'
        for l in LOCATIONS
    )

    result = ""
    if location:
        crowd = expected_crowd(location)
        level, color = crowd_level(crowd)
        result = f"""
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
        <div class="card">
            <h2>Check Queue Status</h2>
            <form method="get">
                <select name="location">{options}</select>
                <input type="submit" value="Check Status" class="btn">
            </form>
        </div>
        {result}
    </div></body></html>
    """

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
