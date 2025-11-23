# Automatic Pill Dispenser Machine

The **Automatic Pill Dispenser Machine** is a smart health-care assistant designed to help users manage their daily medicine schedules.  
The system allows users to enter medicine information through a web application, and the hardware unit automatically dispenses pills at the scheduled times.

---

## 🚀 Features

### 🔹 **Web Application**
- Add medicine details:
  - Medicine name  
  - Dosage  
  - Pill count  
  - Number of daily doses  
  - Custom schedule for each dose
- View, edit, and delete medicine information
- Clean UI using **HTML, CSS, and JavaScript**

### 🔹 **Backend (Flask + MySQL)**
- REST endpoints for managing medicines
- Stores all schedules in a MySQL database
- Uses **Python threading** to:
  - Continuously check upcoming times
  - Trigger hardware actions at the correct moment

### 🔹 **Hardware System**
- Stepper/servo/DC motors for rotating dispensary slots  
- Dispenses pills automatically when notified by the backend
- Communicates with the server through GPIO / serial (depending on setup)

---

## 🛠️ Technologies Used

| Component | Technologies |
|----------|--------------|
| Frontend | HTML, CSS, JavaScript |
| Backend | Python, Flask |
| Database | MySQL |
| System | Multithreading for task scheduling |
| Hardware | Motor drivers, microcontroller (ESP/Arduino), sensors |

---

## 📦 Project Structure

/frontend
index.html
styles.css
app.js

/backend
app.py
scheduler.py
database.py

/hardware
dispenser_control.ino


---

## 🧠 How It Works

1. The user adds medicine schedules on the web app  
2. Flask saves the data to MySQL  
3. A Python threading system constantly checks for the next medicine time  
4. When the time matches → hardware is triggered  
5. Motors rotate and dispense the correct pill  

---

## 📸 Screenshots (Optional)

_Add UI or hardware photos here_

---

## 💡 Future Improvements
- Mobile app version  
- WhatsApp/SMS reminders  
- OLED display for manual control  
- Battery backup  

---

## 👥 Team Members
- *Add your names here*

---

## 📄 License
MIT License (or any license you choose)

---

## 📝 Acknowledgments
Special thanks to our teachers and mentors for supporting the project.



