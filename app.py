from flask import Flask, request
import sqlite3
from datetime import datetime, timedelta
import csv

app = Flask(__name__)

# ---------------- ALL LOCATIONS (MATCHES CSV) ----------------
LOCATIONS = [
    "Government Hospital", "Private Hospital", "Primary Health Centre",
    "Ration Shop", "Supermarket", "Shopping Complex", "Shopping Mall",
    "Restaurant", "Hotel", "Bus Stand", "Railway Station", "Metro Station",
    "Airport", "Post Office", "Bank", "ATM", "Police Station",
    "Municipal Office", "Village Office", "Taluk Office",
    "Fuel Station", "Temple", "Mosque", "Church",
    "Public Library", "Examination Centre"
]

# ---------------- SERVICE PARAMETERS ----------------
AVG_SERVICE_TIME = 2      # minutes per person
SERVICE_COUNTERS = 3      # assumed parallel service capacity

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

# ---------------- LOAD BASELINE CSV ----------------
def load_baseline_data():
    with open("baseline_crowd.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

baseline_data = load_baseline_data()

# ---------------- EXPECTED CROWD ENGINE ----------------
def expected_crowd(location):
    now = datetime.now()
    today = now.strftime("%A")
    current_hour = now.hour

    # --- Historical baseline (nearest past hour) ---
    today_rows = [
        r for r in baseline_data
        if r["location"] == location and r["day"] == today
    ]

    baseline = 0
    if today_rows:
        hours = sorted(int(r["hour"]) for r in today_rows)
        past_hours = [h for h in hours if h <= current_hour]
        chosen_hour = max(past_hours) if past_hours else min(hours)

        for r in today_rows:
            if int(r["hour"]) == chosen_hour:
                baseline = int(r["baseline_crowd"])
                break

    # --- Registered users (queue demand) ---
    conn = sqlite3.connect("data.db")
    registered = conn.execute(
        "SELECT COUNT(*) FROM queue WHERE location=?",
        (location,)
    ).fetchone()[0]
    conn.close()

    return baseline + registered

# ---------------- WAITING TIME MODEL ----------------
def estimate_wait_time(crowd):
    if crowd <= 0:
        return 0
    return int((crowd / SERVICE_COUNTERS) * AVG_SERVICE_TIME)

# ---------------- CROWD LEVEL ----------------
def crowd_level(crowd):
    if crowd <= 50:
        return "Low 🟢"
    elif crowd <= 120:
        return "Moderate 🟡"
    else:
        return "High 🔴"

# ---------------- BEST TIME TO VISIT ----------------
def best_time_to_visit(location):
    hourly = {}

    for r in baseline_data:
        if r["location"] == location:
            h = int(r["hour"])
            c = int(r["baseline_crowd"])
            hourly[h] = min(hourly.get(h, c), c)

    if not hourly:
        return "Data unavailable"

    best = min(hourly, key=hourly.get)
    return f"{best}:00 – {best + 1}:00"

# ---------------- UI STYLE ----------------
STYLE = """
<style>
body { font-family: Arial; background:#f4f6f8; }
.container {
    width: 650px; margin: 60px auto; background:white;
    padding: 30px; border-radius:10px;
    box-shadow:0 0 12px rgba(0,0,0,0.15);
}
h1, h2 { color:#1f4fd8; }
select, input { padding:8px; margin-top:10px; }
input[type=submit] {
    background:#1f4fd8; color:white; border:none;
    padding:8px 18px; border-radius:5px;
}
</style>
"""

# ---------------- HOME ----------------
@app.route("/")
def home():
    clear_old_entries()
    return f"""
    <html><head><title>Q-SMART</title>{STYLE}</head><body>
    <div class="container">
        <h1>Q-SMART</h1>
        <p>Smart Crowd Prediction & Queue Management System</p>
        <a href="/join">Join Queue</a> |
        <a href="/status">Check Status</a>
    </div></body></html>
    """

# ---------------- JOIN QUEUE ----------------
@app.route("/join")
def join():
    options = "".join(f"<option>{l}</option>" for l in LOCATIONS)
    return f"""
    <html><head>{STYLE}</head><body>
    <div class="container">
        <h2>Register in Queue</h2>
        <form action="/add" method="post">
            <select name="location">{options}</select><br>
            <input type="submit" value="Register">
        </form>
        <br><a href="/">Back</a>
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
        <a href="/">Home</a>
    </div></body></html>
    """

# ---------------- STATUS PAGE ----------------
@app.route("/status")
def status():
    location = request.args.get("location")
    options = "".join(f"<option>{l}</option>" for l in LOCATIONS)
    output = ""

    if location:
        crowd = expected_crowd(location)
        output = f"""
        <p><b>Expected Crowd:</b> {crowd} people</p>
        <p><b>Crowd Level:</b> {crowd_level(crowd)}</p>
        <p><b>Estimated Waiting Time:</b> {estimate_wait_time(crowd)} minutes</p>
        <p><b>Best Time to Visit:</b> {best_time_to_visit(location)}</p>
        """

    return f"""
    <html><head>{STYLE}</head><body>
    <div class="container">
        <h2>Queue Status</h2>
        <form method="get">
            <select name="location">{options}</select>
            <input type="submit" value="Check">
        </form>
        <br>{output}
        <br><a href="/">Back</a>
    </div></body></html>
    """

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run()
