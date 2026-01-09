from flask import Flask, request
import sqlite3, csv, os
from datetime import datetime, timedelta

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

    rows = [r for r in baseline_data if r["location"] == location and r["day"] == today]
    baseline = 0
    if rows:
        hours = sorted(int(r["hour"]) for r in rows)
        chosen = max([h for h in hours if h <= hour], default=min(hours))
        baseline = next(int(r["baseline_crowd"]) for r in rows if int(r["hour"]) == chosen)

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
        return "Low", "green"
    elif crowd <= 120:
        return "Moderate", "orange"
    else:
        return "High", "red"

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

# ---------------- UI ----------------
solutions_menu = "".join(
    f'<a href="/status?location={l}">{l}</a>' for l in LOCATIONS
)

STYLE = """
<style>
body{margin:0;font-family:'Segoe UI',sans-serif;background:#f5f7fb}
.navbar{
 background:#1c2536;color:white;padding:15px 40px;
 display:flex;justify-content:space-between;align-items:center
}
.brand{font-size:20px;font-weight:700;margin-left:10px}
.logo{height:36px;vertical-align:middle}
.nav-right a{color:white;text-decoration:none;margin-left:20px;font-weight:500}
.primary{background:#3b6cff;padding:8px 14px;border-radius:6px}
.dropdown{position:relative;display:inline-block}
.dropbtn{background:none;border:none;color:white;font-size:15px;font-weight:500;cursor:pointer}
.dropdown-content{
 display:none;position:absolute;background:white;color:#333;
 min-width:240px;max-height:300px;overflow-y:auto;
 box-shadow:0 10px 30px rgba(0,0,0,.15);border-radius:8px;z-index:1
}
.dropdown-content a{
 color:#333;padding:10px 15px;text-decoration:none;display:block
}
.dropdown-content a:hover{background:#f0f2f8}
.dropdown:hover .dropdown-content{display:block}

.container{
 max-width:1000px;margin:80px auto;background:white;
 padding:50px;border-radius:16px;box-shadow:0 20px 40px rgba(0,0,0,.08)
}
.hero{display:flex;justify-content:space-between;align-items:center}
.hero h1{font-size:42px;margin-bottom:10px}
.hero p{color:#555;font-size:18px}
.btn{padding:14px 22px;background:#3b6cff;color:white;
 text-decoration:none;border-radius:10px;font-weight:600;margin-right:10px}
.card-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:20px}
.card{background:#f9fafc;padding:25px;border-radius:14px}
.badge{padding:6px 14px;border-radius:20px;color:white;font-weight:600}
.green{background:#28a745}.orange{background:#f0ad4e}.red{background:#dc3545}
select,input{width:100%;padding:14px;border-radius:10px;border:1px solid #ccc}
</style>
"""

NAVBAR = f"""
<div class="navbar">
  <div>
    <img src="/static/Urbanx logo.jpeg" class="logo">
    <span class="brand">Q-SMART <small>by UrbanX</small></span>
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
      <div class="dropdown-content">{solutions_menu}</div>
    </div>

    <a href="/join">Join Queue</a>
    <a href="/status" class="primary">Check Status</a>
  </div>
</div>
"""

# ---------------- ROUTES ----------------
@app.route("/")
def home():
    clear_old_entries()
    return f"""
    <html><head><title>Q-SMART</title>{STYLE}</head>
    <body>{NAVBAR}
    <div class="container hero">
      <div>
        <h1>Experience Smarter Crowd Planning</h1>
        <p>Predict queues, avoid peak hours, and plan visits efficiently.</p>
        <a class="btn" href="/status">Check Crowd Status</a>
        <a class="btn" style="background:#e4e9ff;color:#3b6cff" href="/join">Join Queue</a>
      </div>
      <img src="/static/Urbanx logo.jpeg" style="height:200px">
    </div>
    </body></html>
    """

@app.route("/company")
def company():
    return f"""
    <html><head><title>Company</title>{STYLE}</head>
    <body>{NAVBAR}
    <div class="container" style="text-align:center">
      <img src="/static/Urbanx logo.jpeg" style="height:140px">
      <h1>UrbanX</h1>
      <p style="max-width:600px;margin:auto;color:#555;font-size:18px">
        UrbanX builds smart urban analytics platforms that reduce waiting
        times and improve access to public infrastructure.
      </p>
    </div>
    </body></html>
    """

@app.route("/join")
def join():
    opts = "".join(f"<option>{l}</option>" for l in LOCATIONS)
    return f"""
    <html><head><title>Join Queue</title>{STYLE}</head>
    <body>{NAVBAR}
    <div class="container">
      <h2>Join Queue</h2>
      <form method="post" action="/add">
        <select name="location">{opts}</select><br><br>
        <input type="submit" value="Register" class="btn">
      </form>
    </div></body></html>
    """

@app.route("/add", methods=["POST"])
def add():
    conn = sqlite3.connect("data.db")
    conn.execute(
        "INSERT INTO queue (location,time) VALUES (?,?)",
        (request.form["location"], datetime.now())
    )
    conn.commit()
    conn.close()
    return f"""
    <html><head>{STYLE}</head>
    <body>{NAVBAR}
    <div class="container"><h2>Registered Successfully ✅</h2></div>
    </body></html>
    """

@app.route("/status")
def status():
    loc = request.args.get("location")
    result = ""
    if loc:
        c = expected_crowd(loc)
        lvl, col = crowd_level(c)
        result = f"""
        <div class="card-grid">
          <div class="card"><b>Expected Crowd</b><h2>{c}</h2></div>
          <div class="card"><b>Crowd Level</b><span class="badge {col}">{lvl}</span></div>
          <div class="card"><b>Waiting Time</b><h3>{wait_time(c)} min</h3></div>
          <div class="card"><b>Best Time</b><h3>{best_time(loc)}</h3></div>
        </div>
        """

    opts = "".join(f"<option>{l}</option>" for l in LOCATIONS)
    return f"""
    <html><head><title>Status</title>{STYLE}</head>
    <body>{NAVBAR}
    <div class="container">
      <h2>Check Queue Status</h2>
      <form method="get">
        <select name="location">{opts}</select><br><br>
        <input type="submit" value="Check Status" class="btn">
      </form>
      {result}
    </div></body></html>
    """

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
