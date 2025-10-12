from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
from pymongo import MongoClient
from bson.objectid import ObjectId

app = Flask(__name__)
app.secret_key = "supersecretkey"

# --- MongoDB Setup ---
client = MongoClient("mongodb://localhost:27017/")
db = client["smartqueue"]
tokens_collection = db["tokens"]
staff_collection = db["staff"]

# --- Flask-Login Setup ---
login_manager = LoginManager()
login_manager.login_view = "home"
login_manager.init_app(app)

# --- Staff User Class ---
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

# --- Home Page ---
@app.route('/')
def home():
    today = datetime.now().strftime("%Y-%m-%d")
    login_error = request.args.get('login_error')
    return render_template('index.html', today=today, login_error=login_error)

# --- Staff Login ---
@app.route('/staff_login', methods=['POST'])
def staff_login():
    username = request.form.get("username")
    password = request.form.get("password")
    staff = staff_collection.find_one({"username": username})
    if staff and staff["password"] == password:  # plain text check
        user_obj = Staff(str(staff["_id"]), staff["username"])
        login_user(user_obj)
        return redirect(url_for("staff_dashboard"))
    else:
        return redirect(url_for("home") + "?login_error=1")

# --- Staff Logout ---
@app.route('/staff_logout')
@login_required
def staff_logout():
    logout_user()
    return redirect(url_for("home"))

# --- User Submit ---
@app.route('/user', methods=['POST'])
def user_submit():
    name = request.form.get('name')
    phone = request.form.get('phone')
    address = request.form.get('address')
    date_str = request.form.get('date')

    if not (name and phone and address and date_str):
        return "All fields required!", 400

    service_duration = timedelta(minutes=5)
    now = datetime.now()

    # Get last token for today
    last_token = tokens_collection.find_one(
        {"date": date_str},
        sort=[("token_number", -1)]
    )
    token_number = 1 if not last_token else last_token["token_number"] + 1

    if last_token and "end_time" in last_token:
        last_end_time = datetime.strptime(f"{date_str} {last_token['end_time']}", "%Y-%m-%d %H:%M:%S")
        start_time = max(now, last_end_time)
    else:
        start_time = now

    end_time = start_time + service_duration

    token_data = {
        "token_number": token_number,
        "name": name,
        "phone": phone,
        "address": address,
        "date": date_str,
        "status": "Active",
        "created_at": now,
        "end_time": end_time.strftime("%H:%M:%S"),
        "actual_service_time": None
    }

    tokens_collection.insert_one(token_data)

    return render_template('token.html',
                           token=token_number,
                           date=date_str,
                           time=now.strftime("%H:%M:%S"),
                           end_time=end_time.strftime("%H:%M:%S"))

# --- Staff Dashboard ---
@app.route('/staff')
@login_required
def staff_dashboard():
    today = datetime.now().strftime("%Y-%m-%d")
    tokens = list(tokens_collection.find({"date": today}).sort("token_number", 1))

    active_tokens = tokens_collection.count_documents({"status": "Active", "date": today})
    completed_tokens = tokens_collection.count_documents({"status": "Done", "date": today})

    completed = list(tokens_collection.find({"status": "Done", "date": today}))
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

    return render_template('staff.html', tokens=tokens, stats=stats, user=current_user.username)

# --- Mark Done ---
@app.route('/done/<int:token_number>', methods=['POST'])
@login_required
def mark_done(token_number):
    today = datetime.now().strftime("%Y-%m-%d")
    token = tokens_collection.find_one({"token_number": token_number, "date": today})
    if token and token['status'] == "Active":
        token_datetime = token['created_at']
        now = datetime.now()
        actual_service_time = round((now - token_datetime).total_seconds() / 60, 1)

        tokens_collection.update_one({"token_number": token_number, "date": today},
                                     {"$set": {"status": "Done", "actual_service_time": actual_service_time}})

        remaining_tokens = list(tokens_collection.find(
            {"status": "Active", "token_number": {"$gt": token_number}, "date": today}
        ).sort("token_number", 1))

        prev_end_time = now
        for t in remaining_tokens:
            new_end = prev_end_time + timedelta(minutes=5)
            tokens_collection.update_one({"token_number": t["token_number"], "date": today},
                                         {"$set": {"end_time": new_end.strftime("%H:%M:%S")}})
            prev_end_time = new_end

    return redirect(url_for('staff_dashboard'))

# --- Cancel Token ---
@app.route('/cancel/<int:token_number>', methods=['POST'])
@login_required
def cancel_token(token_number):
    today = datetime.now().strftime("%Y-%m-%d")
    token = tokens_collection.find_one({"token_number": token_number, "date": today})
    if token and token['status'] == "Active":
        tokens_collection.update_one({"token_number": token_number, "date": today},
                                     {"$set": {"status": "Cancelled"}})

        remaining_tokens = list(tokens_collection.find(
            {"status": "Active", "token_number": {"$gt": token_number}, "date": today}
        ).sort("token_number", 1))

        prev_end_time = datetime.now()
        for t in remaining_tokens:
            new_end = prev_end_time + timedelta(minutes=5)
            tokens_collection.update_one({"token_number": t["token_number"], "date": today},
                                         {"$set": {"end_time": new_end.strftime("%H:%M:%S")}})
            prev_end_time = new_end

    return redirect(url_for('staff_dashboard'))

# --- API Token Status ---
@app.route('/api/token_status/<int:token_number>')
def token_status(token_number):
    today = datetime.now().strftime("%Y-%m-%d")
    token = tokens_collection.find_one({"token_number": token_number, "date": today})
    if token:
        response = {
            "token_number": token["token_number"],
            "status": token["status"]
        }
        if token["status"] == "Active":
            response["end_datetime"] = f"{token['date']} {token['end_time']}"
            response["end_time"] = token['end_time']
        return jsonify(response)
    else:
        return jsonify({"error": "Token not found"}), 404

if __name__ == '__main__':
    app.run(debug=True)
