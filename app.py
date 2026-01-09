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
body {
    margin:0;
    font-family:'Segoe UI', sans-serif;
    background:#f4f6fb;
}
.container {
    max-width:1100px;
    margin:60px auto;
    padding:0 20px;
}
.card {
    background:white;
    padding:40px;
    border-radius:18px;
    box-shadow:0 15px 40px rgba(0,0,0,0.08);
}
select, input {
    width:100%;
    padding:14px;
    margin-top:14px;
    border-radius:8px;
    border:1px solid #ccc;
}
.btn {
    margin-top:20px;
    padding:14px 28px;
    background:#1f4fd8;
    color:white;
    border-radius:10px;
    font-weight:600;
    text-decoration:none;
    border:none;
    cursor:pointer;
}
.grid {
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
    gap:20px;
    margin-top:30px;
}
.badge {
    padding:6px 16px;
    border-radius:20px;
    color:white;
    font-weight:600;
    display:inline-block;
    margin-top:6px;
}
.green{background:#28a745;}
.orange{background:#f0ad4e;}
.red{background:#d9534f;}
</style>
"""

# ---------------- HOME / DASHBOARD ----------------
@app.route("/")
def home():
    clear_old_entries()

    rows = ""
    for loc in LOCATIONS:
        crowd = expected_crowd(loc)
        level, color = crowd_level(crowd)
        rows += f"""
        <tr>
            <td>{loc}</td>
            <td>{crowd}</td>
            <td><span class="badge {color}">{level}</span></td>
            <td>{wait_time(crowd)} min</td>
            <td>{best_time(loc)}</td>
        </tr>
        """

    return f"""
    <html><head><title>Q-SMART by UrbanX</title>{STYLE}</head><body>
    <div class="container">
        <h1>Q-SMART Dashboard</h1>
        <a class="btn" href="/status">Check Status</a>
        <a class="btn" href="/join" style="margin-left:10px;">Join Queue</a>

        <table style="width:100%;margin-top:40px;border-collapse:collapse;">
            <tr style="background:#1c2333;color:white;">
                <th>Location</th>
                <th>Expected Crowd</th>
                <th>Crowd Level</th>
                <th>Wait Time</th>
                <th>Best Time</th>
            </tr>
            {rows}
        </table>
    </div>
    </body></html>
    """

# ---------------- JOIN QUEUE ----------------
@app.route("/join")
def join():
    options = "".join(f"<option>{l}</option>" for l in LOCATIONS)
    return f"""
    <html><head><title>Join Queue</title>{STYLE}</head><body>
    <div class="container">
        <div class="card">
            <h2>Join Queue</h2>
            <form method="post" action="/add">
                <select name="location">{options}</select>
                <input type="submit" value="Register" class="btn">
            </form>
            <br><a href="/">← Back to Dashboard</a>
        </div>
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
    return """
    <html><body>
    <h2>Registered Successfully ✅</h2>
    <a href="/">Go Home</a>
    </body></html>
    """

# ---------------- CHECK STATUS ----------------
@app.route("/status")
def status():
    location = request.args.get("location")

    options = "".join(
        f"<option {'selected' if l == location else ''}>{l}</option>"
        for l in LOCATIONS
    )

    result = ""
    if location:
        crowd = expected_crowd(location)
        level, color = crowd_level(crowd)
        result = f"""
        <div class="grid">
            <div class="card"><h3>Expected Crowd</h3><h2>{crowd}</h2></div>
            <div class="card"><h3>Crowd Level</h3><span class="badge {color}">{level}</span></div>
            <div class="card"><h3>Waiting Time</h3><h3>{wait_time(crowd)} min</h3></div>
            <div class="card"><h3>Best Time</h3><h3>{best_time(location)}</h3></div>
        </div>
        """

    return f"""
    <html><head><title>Check Status</title>{STYLE}</head><body>
    <div class="container">
        <div class="card">
            <h2>Check Queue Status</h2>
            <form method="get">
                <select name="location">{options}</select>
                <input type="submit" value="Check Status" class="btn">
            </form>
        </div>
        {result}
        <br><a href="/">← Back to Dashboard</a>
    </div>
    </body></html>
    """

# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
