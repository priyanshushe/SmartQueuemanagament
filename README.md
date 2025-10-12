# 🎯 Smart Queue Management System

A **web-based Smart Queue System** built with **Python Flask** and **MongoDB** for efficient token management, live tracking, and staff analytics.  
Designed to save time, reduce waiting, and provide a smooth queue experience for both users and staff.

---

## 🚀 Overview

The Smart Queue Management System allows users to generate tokens, monitor their turn with live countdowns, and allows staff to manage active, completed, and cancelled tokens.  
It provides real-time updates, analytics for staff, and an interactive, responsive interface.

---

## ✨ Features

### User Side
- Generate and track tokens in real-time  
- Live countdown for active tokens  
- View token status (Active / Completed / Cancelled)  

### Staff Side
- Secure login system  
- Dashboard showing all tokens for the day  
- Update token statuses (Done / Cancelled)  
- View analytics: active tokens, completed tokens, average wait time, fastest service  

### System
- Persistent storage using MongoDB  
- Responsive front-end with Bootstrap and animations  
- Works on desktop and mobile browsers  

---

## 🧠 Tech Stack

| Layer      | Technologies                                    |
|------------|-------------------------------------------------|
| Frontend   | HTML5, CSS3, JavaScript, Bootstrap, Animate.css |
| Backend    | Python Flask                                    |
| Database   | MongoDB                                         |

---

## ⚙️ Installation & Setup

1️⃣ Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/SmartQueue.git
cd SmartQueue

2️⃣ Install Dependencies
pip install -r requirements.txt

3️⃣ Start MongoDB

Ensure MongoDB is running locally, or update your connection string in app.py.

4️⃣ Run the Flask App
python app.py

5️⃣ Open in Browser

Visit: http://127.0.0.1:5000


### 🧩 Project Structure
SmartQueue/
├── app.py                 # Flask main application
├── requirements.txt       # Python dependencies
├── templates/             # HTML templates
│   ├── index.html         # Home / User login
│   ├── staff.html         # Staff dashboard
│   ├── token.html         # Token display
├── static/                # CSS, JS, images
│   ├── background.jpg
│   ├── style.css
│   ├── script.js
└── README.md              # Project documentation

📊 Future Enhancements

Staff performance analytics dashboard

SMS/email notifications for users

Multi-counter or multi-branch support

Cloud deployment on Render, AWS, or PythonAnywhere

🤝 Contributing

Contributions are welcome!

Fork the repository

Create your feature branch:

git checkout -b feature/AmazingFeature


Commit your changes:

git commit -m "Add AmazingFeature"


Push the branch:

git push origin feature/AmazingFeature


Open a Pull Request

🪪 License

This project is licensed under the MIT License. See the LICENSE file for details.