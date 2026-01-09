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

# ---------------- UI STYLE ----------------
STYLE = """
<style>
:root {
  --primary:#2563eb;
  --bg:#f4f7fb;
  --card:#ffffff;
  --text:#0f172a;
  --muted:#64748b;
}
* { box-sizing:border-box; }

body {
  margin:0;
  font-family:'Inter','Segoe UI',sans-serif;
  background:var(--bg);
  color:var(--text);
}

/* NAVBAR */
.navbar {
  background:#ffffff;
  border-bottom:1px solid #e5e7eb;
  padding:16px 48px;
  display:flex;
  justify-content:space-between;
  align-items:center;
  position:sticky;
  top:0;
  z-index:1000;
}

.brand {
  display:flex;
  align-items:center;
  gap:12px;
  font-weight:700;
}

.brand img { height:36px; }
.brand span { color:var(--primary); }

/* LAYOUT */
.container {
  max-width:1200px;
  margin:60px auto;
  padding:0 24px;
}

/* HERO */
.hero {
  background:linear-gradient(135deg,#2563eb,#4f46e5);
  color:white;
  padding:70px;
  border-radius:28px;
  display:grid;
  grid-template-columns:1.3fr 1fr;
  gap:40px;
  align-items:center;
}

.hero h1 { font-size:44px; margin:0; }
.hero p { font-size:18px; opacity:.9; max-width:520px; }

.hero-actions { margin-top:30px; }

.btn {
  padding:14px 28px;
  border-radius:12px;
  font-weight:600;
  text-decoration:none;
  display:inline-block;
}

.btn.primary { background:white; color:#1e3a8a; }
.btn.secondary {
  background:rgba(255,255,255,.15);
  color:white;
  margin-left:12px;
}

/* DASHBOARD */
.dashboard { margin-top:60px; }
.dashboard h2 { font-size:28px; margin-bottom:20px; }

.grid {
  display:grid;
  grid-template-columns:repeat(auto-fit,minmax(260px,1fr));
  gap:24px;
}

/* CARDS */
.card {
  background:var(--card);
  padding:26px;
  border-radius:20px;
  box-shadow:0 10px 30px rgba(0,0,0,.08);
}

.card h3 {
  margin:0;
  font-size:15px;
  color:var(--muted);
}

.value {
  font-size:34px;
  font-weight:700;
  margin-top:6px;
}

.badge {
  margin-top:10px;
  display:inline-block;
  padding:6px 14px;
  border-radius:20px;
  font-size:13px;
  font-weight:600;
  color:white;
}

.green{background:#22c55e;}
.orange{background:#f59e0b;}
.red{background:#ef4444;}

select,input {
  width:100%;
  padding:14px;
  border-radius:10px;
  border:1px solid #ccc;
  margin-top:14px;
}

footer {
  margin-top:80px;
  padding:40px;
  text-align:center;
  color:var(--muted);
}
</style>
"""

# ---------------- HOME / DASHBOARD ----------------
@app.route("/")
def home():
    clear_old_entries()

    cards = ""
    for loc in LOCATIONS:
        crowd = expected_crowd(loc)
        level, color = crowd_level(crowd)
        cards += f"""
        <div class="card">
            <strong>{loc}</strong>
            <h3>Expected Crowd</h3>
            <div class="value">{crowd}</div>
            <span class="badge {color}">{level}</span>
            <h3 style="margin-top:14px">Best Time</h3>
            <small>{best_time(loc)}</small>
        </div>
        """

    return f"""
    <html><head><title>Q-SMART by UrbanX</title>{STYLE}</head><body>

    <div class="navbar">
        <div class="brand">
            <img src="/static/Urbanx logo.jpeg">
            Q-SMART <span>by UrbanX</span>
        </div>
    </div>

    <div class="container">
        <div class="hero">
            <div>
                <h1>Smart Crowd Intelligence</h1>
                <p>Predict congestion, estimate waiting time, and choose the best time to visit public locations.</p>
                <div class="hero-actions">
                    <a class="btn primary" href="/status">Check Status</a>
                    <a class="btn secondary" href="/join">Join Queue</a>
                </div>
            </div>
            <img src="/static/Urbanx logo.jpeg" width="100%">
        </div>

        <div class="dashboard">
            <h2>Live Crowd Overview</h2>
            <div class="grid">{cards}</div>
        </div>
    </div>

    <footer>© 2026 Q-SMART by UrbanX</footer>
    </body></html>
    """

# ---------------- JOIN QUEUE ----------------
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
                <input type="submit" value="Register" class="btn primary">
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
    return """
    <html><body>
    <h2>Registered Successfully ✅</h2>
    <a href="/">Return to Dashboard</a>
    </body></html>
    """

# ---------------- CHECK STATUS ----------------
@app.route("/status")
def status():
    location = request.args.get("location")

    options = "".join(
        f"<option {'selected' if l==location else ''}>{l}</option>"
        for l in LOCATIONS
    )

    result = ""
    if location:
        crowd = expected_crowd(location)
        level, color = crowd_level(crowd)
        result = f"""
        <div class="grid" style="margin-top:40px">
            <div class="card"><h3>Expected Crowd</h3><div class="value">{crowd}</div></div>
            <div class="card"><h3>Crowd Level</h3><span class="badge {color}">{level}</span></div>
            <div class="card"><h3>Waiting Time</h3><div class="value">{wait_time(crowd)} min</div></div>
            <div class="card"><h3>Best Time</h3><div class="value">{best_time(location)}</div></div>
        </div>
        """

    return f"""
    <html><head>{STYLE}</head><body>
    <div class="container">
        <div class="card">
            <h2>Check Queue Status</h2>
            <form method="get">
                <select name="location">{options}</select>
                <input type="submit" value="Check Status" class="btn primary">
            </form>
        </div>
        {result}
    </div></body></html>
    """

# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
