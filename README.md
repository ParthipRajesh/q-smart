# Q-SMART by UrbanX  
### Smart Crowd Prediction & Queue Management Platform

🔗 **Live Application:**  
👉 https://q-smart-7jz2.onrender.com/

Q-SMART is a web-based crowd prediction and queue management system designed to reduce congestion at public and commercial locations. The platform predicts expected crowd levels by combining historical baseline data with real-time user registrations, helping users plan visits efficiently and avoid peak hours.

---

## 🎯 Project Aim

The primary aim of Q-SMART is to tackle the growing **crisis of congestion in urban environments** by providing a smart, data-driven system that:
- Predicts crowd levels in advance
- Reduces waiting time uncertainty
- Improves accessibility to public services
- Enables informed decision-making for users

---

## 🚀 Key Features

- **Expected Crowd Prediction**  
  Calculates crowd size using historical baseline data and live queue registrations.

- **Crowd Level Classification**  
  Indicates crowd intensity as **Low**, **Moderate**, or **High**.

- **Estimated Waiting Time**  
  Computes waiting time based on service capacity and queue size.

- **Best Time to Visit Recommendation**  
  Suggests the least crowded time slot using historical trends.

- **Join Queue System**  
  Allows users to register themselves virtually before visiting.

- **Live Multi-Location Dashboard**  
  Displays real-time crowd insights for all supported locations.

- **Privacy-First Design**  
  No personal or sensitive user data is collected or stored.

---

## 🏙️ Supported Locations

Q-SMART supports **30 commonly used public and commercial locations**, including:

- Government Hospital  
- Private Hospital  
- Primary Health Centre  
- Bank, ATM, Post Office  
- Bus Stand, Railway Station, Metro Station, Airport  
- Shopping Mall, Supermarket, Shopping Complex  
- Restaurant, Hotel  
- Police Station, Municipal Office, Village Office, Taluk Office  
- Fuel Station  
- Public Library, Examination Centre  
- Temple, Mosque, Church  

---

## 🧠 System Architecture

- **Frontend:** HTML & CSS (served dynamically via Flask)
- **Backend:** Python (Flask Framework)
- **Database:** SQLite (for live queue registrations)
- **Baseline Data:** CSV-based historical crowd dataset
- **Deployment Platform:** Render (Cloud Hosting)

---

## 🔄 Methodology (Step-by-Step Flow)

1. Load baseline crowd data from `baseline_crowd.csv`
2. Capture live queue registrations through the web interface
3. Store real-time registrations in SQLite database
4. Compute expected crowd:
5. Classify crowd level using predefined thresholds
6. Estimate waiting time using service rate assumptions
7. Determine best visiting time from historical trends
8. Display results via dashboard and status pages

---

## 🧭 User Journey

1. User accesses the Q-SMART homepage
2. Views overall crowd dashboard for all locations
3. Selects a specific location to check queue status
4. Reviews expected crowd, waiting time, and best time to visit
5. Optionally joins the queue virtually
6. Plans visit accordingly with reduced uncertainty

---

## 📊 Live Dashboard

The homepage includes a **live dashboard table** showing:
- Location Name
- Predicted Crowd
- Crowd Level
- Estimated Waiting Time
- Best Time to Visit

This provides a centralized overview of congestion across all locations.

---

## 📁 Repository Structure

q-smart/
│
├── app.py # Main Flask application
├── baseline_crowd.csv # Historical baseline crowd dataset
├── requirements.txt # Python dependencies
├── static/
│ ├── Urbanx logo.jpeg # Company logo
│ ├── pic1.jpeg – pic6.jpeg # Website screenshots
│ ├── WEBSITE WORKING VIDEO.mp4
│ └── QUEUESMART.pptx # Project presentation
│
└── README.md # Project documentation


---

## ▶️ Running the Project Locally

```bash
pip install -r requirements.txt
python app.py

http://127.0.0.1:5000

Deployment

The application is deployed on Render with continuous deployment enabled via GitHub.

🔗 Live URL:
https://q-smart-7jz2.onrender.com/

Demo & Media

The repository includes:

🎥 Screen-recorded working demo video

🖼️ Screenshots of the website UI

📊 Project presentation (PPT)


These are provided for demonstration, evaluation, and presentation purposes.

Developed By

UrbanX

Team members:
Aswiny B Kaimal
Neeraj P Raju
Nafih Nazar
Parthip
              
