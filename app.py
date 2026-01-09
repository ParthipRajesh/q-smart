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

# ---------------- BASELINE ----------------
def load_baseline():
    with open("baseline_crowd.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

baseline_data = load_baseline()

# ---------------- LOGIC ----------------
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

# ---------------- STYLE ----------------
STYLE = """
<style>
body { margin:0; font-family:Segoe UI, sans-serif; background:#f4f6fb; }
.navbar {
    background:#1c2333; padding:18px 40px;
    display:flex; justify-content:space-between; align-items:center;
}
.navbar h1 { color:white; font-size:20px; margin:0; }
.navbar span { color:#8ea0ff; font-weight:500; }
.container { max-width:1100px; margin:70px auto; padding:0 20px; }
.hero { display:grid; grid-template-columns:1.2fr 1fr; gap:40px; align-items:center; }
.hero h2 { font-size:42px; }
.hero p { font-size:18px; color:#555; }
.btn {
    padding:14px 26px; border-radius:10px; background:#1f4fd8;
    color:white; text-decoration:none; font-weight:600; display:inline-block;
}
.btn.secondary { background:#e4e8ff; color:#1f4fd8; margin-left:10px; }
.card {
    background:white; padding:30px; border-radius:16px;
    box-shadow:0 12px 30px rgba(0,0,0,0.08);
}
.card-grid {
    display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
    gap:24px; margin-top:50px;
}
select, input { width:100%; padding:14px; margin-top:15px; border-radius:8px; border:1px solid #ccc; }
.badge { padding:8px 16px; border-radius:20px; color:white; font-weight:600; }
.green{background:#28a745;} .orange{background:#f0ad4e;} .red{background:#d9534f;}
footer { margin-top:80px; background:#1c2333; color:#aaa; padding:40px; text-align:center; }
</style>
"""

# ---------------- ROUTES ----------------
@app.route("/")
def home():
    clear_old_entries()
    return f"""
    <html><head><title>Q-SMART</title>{STYLE}</head><body>

    <div class="navbar">
        <h1>Q-SMART <span>by UrbanX</span></h1>
        <div style="color:#cfd6f3">Company | Solutions</div>
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
                <img src="https://illustrations.popsy.co/gray/work-from-home.svg" width="100%">
            </div>
        </div>

        <div class="card-grid">
            <div class="card"><h3>Expected Crowd</h3><p>Calculated from trends + registrations</p></div>
            <div class="card"><h3>Waiting Time</h3><p>Based on service capacity</p></div>
            <div class="card"><h3>Best Time</h3><p>Suggested low-crowd hour</p></div>
            <div class="card"><h3>Privacy First</h3><p>No personal data collected</p></div>
        </div>
    </div>

    <footer>© 2026 Q-SMART by UrbanX</footer>
    </body></html>
    """

@app.route("/join")
def join():
    options = "".join(f"<option>{l}</option>" for l in LOCATIONS)
    return f"""
    <html><head>{STYLE}</head><body>
    <div class="container">
        <div class="card">
            <h2>Join Queue</h2>
            <p>Select your location to register.</p>
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
            <h2>Registration Successful</h2>
            <p>You have been added to the queue.</p>
            <a class="btn" href="/">Return Home</a>
        </div>
    </div></body></html>
    """

@app.route("/status")
def status():
    location = request.args.get("location")
    options = "".join(f"<option>{l}</option>" for l in LOCATIONS)
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
