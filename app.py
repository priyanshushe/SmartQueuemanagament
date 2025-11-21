from openai import OpenAI
from predict_slot import predict_best_slot
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
from pymongo import MongoClient
from bson.objectid import ObjectId

app = Flask(__name__)
app.secret_key = "supersecretkey"
def get_department_from_issue(issue_text: str) -> str:
    """
    Very simple keyword-based classifier.
    Looks at the issue text and returns one of:
    'Deposit & Withdrawal', 'Loans', 'KYC & Account Creation', 'General'
    """
    if not issue_text:
        return "General"

    text = issue_text.lower()

    # Deposit & Withdrawal
    deposit_keywords = [
        "deposit", "withdraw", "withdrawal", "cash", "saving", "savings",
        "fd", "fixed deposit", "rd", "recurring deposit", "balance", "passbook", "atm"
    ]
    if any(word in text for word in deposit_keywords):
        return "Deposit & Withdrawal"

    # Loans
    loan_keywords = [
        "loan", "home loan", "car loan", "personal loan", "education loan",
        "emi", "interest rate", "repayment", "mortgage"
    ]
    if any(word in text for word in loan_keywords):
        return "Loans"

    # KYC & Account Creation
    kyc_keywords = [
        "kyc", "account opening", "open account", "new account",
        "current account", "savings account opening",
        "aadhaar", "aadhar", "pan", "id proof", "update kyc"
    ]
    if any(word in text for word in kyc_keywords):
        return "KYC & Account Creation"

    # Fallback
    return "General"


# ----------------- MongoDB Setup -----------------
mongo_client = MongoClient("mongodb://localhost:27017/")
db = mongo_client["smartqueue"]
tokens_collection = db["tokens"]
staff_collection = db["staff"]
feedback_collection = db["feedback"]   # NEW

# ----------------- Flask-Login Setup -----------------
login_manager = LoginManager()
login_manager.login_view = "home"
login_manager.init_app(app)


# ----------------- Staff User Class -----------------
class Staff(UserMixin):
    def __init__(self, id_, username):
        self.id = id_      # must be string
        self.username = username


@login_manager.user_loader
def load_user(user_id):
    staff = staff_collection.find_one({"_id": ObjectId(user_id)})
    if staff:
        return Staff(str(staff["_id"]), staff["username"])
    return None


# ----------------- Helper: auto-expire old tokens -----------------
def expire_old_tokens():
    """Set status='Expired' for tokens whose 15-minute slot is over."""
    now = datetime.now()
    tokens_collection.update_many(
        {
            "status": "Active",
            "expiry_datetime": {"$lt": now}
        },
        {"$set": {"status": "Expired"}}
    )


# ----------------- Home Page -----------------
@app.route('/')
def home():
    today = datetime.now().strftime("%Y-%m-%d")
    login_error = request.args.get('login_error')
    feedback_success = request.args.get('feedback')  # "1" after feedback submitted

    return render_template(
        'index.html',
        today=today,
        login_error=login_error,
        feedback_success=feedback_success
    )

# ----------------- Staff Login -----------------
@app.route('/staff_login', methods=['POST'])
def staff_login():
    username = request.form.get("username")
    password = request.form.get("password")

    staff = staff_collection.find_one({"username": username})
    if staff and staff["password"] == password:  # plain-text check (same as your original)
        user_obj = Staff(str(staff["_id"]), staff["username"])
        login_user(user_obj)
        return redirect(url_for("staff_dashboard"))
    else:
        return redirect(url_for("home") + "?login_error=1")


# ----------------- Staff Logout -----------------
@app.route('/staff_logout')
@login_required
def staff_logout():
    logout_user()
    return redirect(url_for("home"))


# ----------------- User Submit (booking with date + time slot) -----------------
@app.route('/user', methods=['POST'])
def user_submit():
    name = request.form.get('name')
    phone = request.form.get('phone')
    issue = request.form.get('issue')
    date_str = request.form.get('date')          # YYYY-MM-DD
    time_str = request.form.get('time_slot')     # HH:MM

    # ✅ Only check real form fields (no department here)
    if not (name and phone and issue and date_str and time_str):
        return "All fields required!", 400

    # 🚫 1. Block booking if phone already has an active token (any date)
    existing_user = tokens_collection.find_one({
        "phone": phone,
        "status": "Active"
    })
    if existing_user:
        return "This phone number already has an active token. Please complete or cancel it before booking another.", 400

    # 2. Combine date + time into one datetime (start of the slot)
    try:
        slot_start_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    except ValueError:
        return "Invalid date or time format", 400

    now = datetime.now()

    # Prevent booking past slot time
    if slot_start_dt < now:
        return "You cannot book a past time slot.", 400

    # 🔍 Automatically decide department based on issue text
    department = get_department_from_issue(issue)
    print("Inferred department:", department)

    # 3. Each token valid for 15 minutes
    token_life = timedelta(minutes=15)
    slot_end_dt = slot_start_dt + token_life

    # 🟡 4. Find staff in this department with least active tokens
    staffs = list(staff_collection.find({"department": department}))
    if not staffs:
        return f"No staff available for department: {department}. Please contact admin.", 500

    staff_load = {}
    for s in staffs:
        username = s["username"]
        count = tokens_collection.count_documents({
            "status": "Active",
            "assigned_staff": username,
            "department": department
        })
        staff_load[username] = count

    assigned_staff = min(staff_load, key=staff_load.get)
    print("Assigned staff:", assigned_staff, "for department:", department)

    # 5. Generate token number for that date
    last_token = tokens_collection.find_one(
        {"date": date_str},
        sort=[("token_number", -1)]
    )
    token_number = 1 if not last_token else last_token["token_number"] + 1

    # 6. Save token with assigned_staff + department
    token_data = {
        "token_number": token_number,
        "name": name,
        "phone": phone,
        "issue": issue,
        "department": department,
        "date": date_str,
        "slot_time": time_str,
        "start_time": slot_start_dt.strftime("%H:%M"),
        "end_time": slot_end_dt.strftime("%H:%M"),
        "status": "Active",
        "assigned_staff": assigned_staff,
        "created_at": now,
        "booking_datetime": slot_start_dt,
        "expiry_datetime": slot_end_dt,
        "actual_service_time": None
    }

    tokens_collection.insert_one(token_data)

    return render_template(
        'token.html',
        token=token_number,
        date=date_str,
        booking_time=time_str,
        start_time=slot_start_dt.strftime("%H:%M"),
        end_time=slot_end_dt.strftime("%H:%M"),
        department=department,   # optional if you show it on token page
    )
from datetime import datetime  # you already have this at top

@app.route('/feedback', methods=['POST'])
def submit_feedback():
    name = request.form.get("name")              # optional
    department = request.form.get("department")  # required
    message = request.form.get("message")        # required

    if not (department and message):
        return "Department and feedback message are required.", 400

    feedback_doc = {
        "name": name,
        "department": department,
        "message": message,
        "created_at": datetime.now()
    }

    feedback_collection.insert_one(feedback_doc)

    # redirect back to home with a "feedback=1" flag
    return redirect(url_for("home") + "?feedback=1")

# ----------------- Staff Dashboard -----------------
@app.route('/staff')
@login_required
def staff_dashboard():
    expire_old_tokens()  # update statuses based on expiry time

    today = datetime.now().strftime("%Y-%m-%d")

    # 1) Get this staff member's document (to know department)
    staff_doc = staff_collection.find_one({"username": current_user.username})
    staff_department = staff_doc.get("department", "Not assigned") if staff_doc else "Not assigned"

    # 2) Get today's tokens assigned to this staff
    tokens = list(tokens_collection.find({
        "date": today,
        "assigned_staff": current_user.username
    }).sort("token_number", 1))

    # Stats per staff
    active_tokens = tokens_collection.count_documents({
        "status": "Active",
        "date": today,
        "assigned_staff": current_user.username
    })
    completed_tokens = tokens_collection.count_documents({
        "status": "Done",
        "date": today,
        "assigned_staff": current_user.username
    })

    completed = list(tokens_collection.find({
        "status": "Done",
        "date": today,
        "assigned_staff": current_user.username
    }))
    completed_times = [t['actual_service_time'] for t in completed if t.get('actual_service_time') is not None]

    if completed_times:
        avg_wait = round(sum(completed_times) / len(completed_times), 1)
        fastest = min(completed_times)
    else:
        avg_wait = 0
        fastest = 0

    stats = {
        "active": active_tokens,
        "completed": completed_tokens,
        "avg_wait": avg_wait,
        "fastest": fastest
    }

    return render_template(
        'staff.html',
        tokens=tokens,
        stats=stats,
        user=current_user.username,
        department=staff_department  # 👈 pass department
    )


# ----------------- Mark Done -----------------
@app.route('/done/<int:token_number>', methods=['POST'])
@login_required
def mark_done(token_number):
    today = datetime.now().strftime("%Y-%m-%d")
    token = tokens_collection.find_one({"token_number": token_number, "date": today})
    if token and token['status'] == "Active":
        start_dt = token.get('booking_datetime', token['created_at'])
        now = datetime.now()
        actual_service_time = round((now - start_dt).total_seconds() / 60, 1)

        tokens_collection.update_one(
            {"token_number": token_number, "date": today},
            {"$set": {"status": "Done", "actual_service_time": actual_service_time}}
        )

    return redirect(url_for('staff_dashboard'))


# ----------------- Cancel Token -----------------
@app.route('/cancel/<int:token_number>', methods=['POST'])
@login_required
def cancel_token(token_number):
    today = datetime.now().strftime("%Y-%m-%d")
    token = tokens_collection.find_one({"token_number": token_number, "date": today})
    if token and token['status'] == "Active":
        tokens_collection.update_one(
            {"token_number": token_number, "date": today},
            {"$set": {"status": "Cancelled"}}
        )

    return redirect(url_for('staff_dashboard'))


# ----------------- API Token Status -----------------
@app.route('/api/token_status/<int:token_number>')
def token_status(token_number):
    expire_old_tokens()

    today = datetime.now().strftime("%Y-%m-%d")
    token = tokens_collection.find_one({"token_number": token_number, "date": today})
    if token:
        response = {
            "token_number": token["token_number"],
            "status": token["status"]
        }

        if token["status"] == "Active":
            response["date"] = token["date"]
            response["slot_time"] = token.get("slot_time")
            response["start_time"] = token.get("start_time")
            response["end_time"] = token.get("end_time")
            response["end_datetime"] = token["booking_datetime"].strftime("%Y-%m-%d %H:%M:%S")

        return jsonify(response)
    else:
        return jsonify({"error": "Token not found"}), 404


# ----------------- Smart Slot Suggestion (Rule-based) -----------------
@app.route('/api/suggest_slot')
def suggest_slot():
    date_str = request.args.get('date')
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    start_hour = 9
    end_hour = 17
    slot_minutes = 15

    slots = {}
    for h in range(start_hour, end_hour):
        for m in range(0, 60, slot_minutes):
            slot = f"{h:02d}:{m:02d}"
            slots[slot] = 0

    tokens = tokens_collection.find({"date": date_str})
    for t in tokens:
        slot = t.get("slot_time")
        if slot in slots and t.get("status") in ["Active", "Done", "Cancelled", "Expired"]:
            slots[slot] += 1

    today_str = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now()

    def is_future_slot(slot_time_str):
        if date_str != today_str:
            return True
        h, m = map(int, slot_time_str.split(":"))
        slot_dt = now.replace(hour=h, minute=m, second=0, microsecond=0)
        return slot_dt >= now + timedelta(minutes=15)

    candidates = [(slot, count) for slot, count in slots.items() if is_future_slot(slot)]

    if not candidates:
        return jsonify({"error": "No available slots."}), 404

    min_count = min(c[1] for c in candidates)
    best_slot = sorted([slot for slot, count in candidates if count == min_count])[0]

    return jsonify({
        "date": date_str,
        "suggested_slot": best_slot,
        "bookings_in_slot": slots[best_slot]
    })

# --- "AI" Chatbot (rule-based, no external API) ---
@app.route('/chatbot', methods=['POST'])
def chatbot():
    user_query = request.form.get("message", "").lower().strip()
    best_slot = predict_best_slot()  # still uses your ML logic

    # Start building a response
    parts = []

    # 1) Questions about best time / slot
    if "when" in user_query or "time" in user_query or "slot" in user_query or "come" in user_query:
        parts.append(f"Based on current and past bookings, a good time to visit is around {best_slot}.")

    # 2) Questions about waiting
    if "wait" in user_query or "waiting" in user_query or "queue" in user_query:
        parts.append("Earlier slots in the day and the suggested time generally have less waiting time.")

    # 3) If asking about token or status
    if "token" in user_query or "status" in user_query:
        parts.append("You can check your token status using the 'Token Status' tab and entering your token number.")

    # 4) Default fallback if we didn't match anything
    if not parts:
        parts.append(
            "I can help with queue timing and booking questions. "
            "Try asking something like 'When should I come to avoid waiting?'"
        )

    reply_text = " ".join(parts)
    return jsonify({"reply": reply_text})

# ----------------- Run App -----------------
if __name__ == '__main__':
    app.run(debug=True)
