from pymongo import MongoClient

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["smartqueue"]
staff_collection = db["staff"]

# 🟢 Change these to your actual staff usernames
department_mapping = {
    "Deposit & Withdrawal": ["Priyanshu Shekhar", "Preeti Raj"],
    "Loans": ["Pranjal Kumar", "Srikant Sharma"],
    "KYC & Account Creation": ["Priyansu Keshri", "Raman Kumar"],
    "General": ["Aman Kumar", "Ram "],
}

# Apply department mapping
for dept, users in department_mapping.items():
    for username in users:
        result = staff_collection.update_one(
            {"username": username},
            {"$set": {"department": dept}}
        )
        if result.modified_count > 0:
            print(f"✔ Updated '{username}' → {dept}")
        else:
            print(f"⚠ '{username}' not found or already assigned.")

print("\n🎉 Department mapping finished!")
