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
body{margin:0;font-family:'Segoe UI',sans-serif;background:#f4f6fb}
.navbar{background:#1c2333;padding:18px 40px;display:flex;justify-content:space-between;align-items:center}
.brand{display:flex;align-items:center;gap:12px}
.brand img{height:34px}
.brand h1{color:white;font-size:20px;margin:0}
.brand span{color:#8ea0ff}
.menu{position:relative;display:inline-block;margin-left:30px;color:#cfd6f3;cursor:pointer}
.menu-content{display:none;position:absolute;top:30px;background:white;min-width:220px;
box-shadow:0 10px 25px rgba(0,0,0,.15);border-radius:10px;z-index:10}
.menu-content a{display:block;padding:14px 18px;color:#333;text-decoration:none}
.menu-content a:hover{background:#f2f4fb}
.menu:hover .menu-content{display:block}
.container{max-width:1100px;margin:70px auto;padding:0 20px}
.card{background:white;padding:30px;border-radius:16px;box-shadow:0 12px 30px rgba(0,0,0,.08)}
.card-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:24px;margin-top:40px}
select,input{width:100%;padding:14px;border-radius:8px;border:1px solid #ccc;margin-top:12px}
.btn{padding:14px 26px;border-radius:10px;background:#1f4fd8;color:white;text-decoration:none;
font-weight:600;border:none;cursor:pointer}
.badge{padding:8px 16px;border-radius:20px;color:white;font-weight:600}
.green{background:#28a745}.orange{background:#f0ad4e}.red{background:#d9534f}
</style>
"""

# ---------------- NAVBAR ----------------
NAVBAR = """
<div class="navbar">
  <div class="brand">
    <img src="/static/Urbanx logo.jpeg">
    <h1>Q-SMART <span>by UrbanX</span></h1>
  </div>
  <div>
    <div class="menu">Company
      <div class="menu-content">
        <a href="/company">About UrbanX</a>
        <a href="/vision">Our Vision</a>
        <a href="/contact">Contact</a>
      </div>
    </div>
    <div class="menu">Solutions
      <div class="menu-content">
        <a href="/solution/healthcare">Healthcare</a>
        <a href="/solution/transport">Transportation</a>
        <a href="/solution/public">Public Services</a>
        <a href="/solution/education">Education</a>
        <a href="/solution/religious">Religious Places</a>
      </div>
    </div>
  </div>
</div>
"""

# ---------------- INFO PAGES ----------------
@app.route("/company")
def company():
    return f"<html><head>{STYLE}</head><body>{NAVBAR}<div class='container'><div class='card'><h2>About UrbanX</h2><p>UrbanX is a smart-city focused initiative developing data-driven solutions for real-world urban problems. Q-SMART is designed to reduce congestion, waiting time, and inefficiency in public spaces.</p></div></div></body></html>"

@app.route("/vision")
def vision():
    return f"<html><head>{STYLE}</head><body>{NAVBAR}<div class='container'><div class='card'><h2>Our Vision</h2><p>To enable smarter, safer, and more efficient cities using predictive analytics and minimal user data.</p></div></div></body></html>"

@app.route("/contact")
def contact():
    return f"<html><head>{STYLE}</head><body>{NAVBAR}<div class='container'><div class='card'><h2>Contact</h2><p>Email: urbanx.smart@gmail.com<br>Project developed as an academic & smart-city initiative.</p></div></div></body></html>"

@app.route("/solution/<name>")
def solution(name):
    return f"<html><head>{STYLE}</head><body>{NAVBAR}<div class='container'><div class='card'><h2>{name.title()} Solution</h2><p>Q-SMART predicts crowd density and optimal visiting times for {name} environments using historical trends and live registrations.</p></div></div></body></html>"

# ---------------- MAIN PAGES ----------------
@app.route("/")
def home():
    clear_old_entries()
    return f"<html><head>{STYLE}</head><body>{NAVBAR}<div class='container'><div class='card'><h2>Experience Smarter Crowd Planning</h2><p>Predict queues, avoid peak hours, and plan visits efficiently.</p><a class='btn' href='/status'>Check Crowd Status</a> <a class='btn' href='/join'>Join Queue</a></div></div></body></html>"

@app.route("/join")
def join():
    options = "".join(f"<option>{l}</option>" for l in LOCATIONS)
    return f"<html><head>{STYLE}</head><body>{NAVBAR}<div class='container'><div class='card'><h2>Join Queue</h2><form method='post' action='/add'><select name='location'>{options}</select><button class='btn'>Register</button></form></div></div></body></html>"

@app.route("/add", methods=["POST"])
def add():
    conn = sqlite3.connect("data.db")
    conn.execute("INSERT INTO queue (location,time) VALUES (?,?)",
                 (request.form["location"], datetime.now()))
    conn.commit()
    conn.close()
    return f"<html><head>{STYLE}</head><body>{NAVBAR}<div class='container'><div class='card'><h2>Registered Successfully</h2><a class='btn' href='/status'>Check Status</a></div></div></body></html>"

@app.route("/status")
def status():
    selected = request.args.get("location")

    options = "".join(
        f"<option {'selected' if l==selected else ''}>{l}</option>"
        for l in LOCATIONS
    )

    result = ""
    if selected:
        crowd = expected_crowd(selected)
        level, color = crowd_level(crowd)
        result = f"""
        <div class='card-grid'>
          <div class='card'><h3>Expected Crowd</h3><h2>{crowd}</h2></div>
          <div class='card'><h3>Crowd Level</h3><span class='badge {color}'>{level}</span></div>
          <div class='card'><h3>Waiting Time</h3><h2>{wait_time(crowd)} min</h2></div>
          <div class='card'><h3>Best Time</h3><h2>{best_time(selected)}</h2></div>
        </div>
        """

    return f"<html><head>{STYLE}</head><body>{NAVBAR}<div class='container'><div class='card'><h2>Check Queue Status</h2><form method='get'><select name='location'>{options}</select><button class='btn'>Check Status</button></form></div>{result}</div></body></html>"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
