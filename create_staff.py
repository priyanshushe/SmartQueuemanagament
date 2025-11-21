from pymongo import MongoClient

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["smartqueue"]
staff_collection = db["staff"]

print("🔔 Staff Creation Tool Started")
while True:
    print("\n➕ Add New Staff User")
    username = input("Enter username: ").strip()
    password = input("Enter password: ").strip()

    # Check if staff already exists
    existing_staff = staff_collection.find_one({"username": username})
    if existing_staff:
        print(f"⚠️ Username '{username}' already exists. Please try another one.")
    else:
        staff_collection.insert_one({"username": username, "password": password})
        print(f"✔ Staff user added successfully: {username}")

    another = input("\nAdd another staff? (yes/no): ").lower()
    if another not in ["yes", "y"]:
        break

# Display all staff members
print("\n📋 Current staff in database:")
for staff in staff_collection.find({}, {"_id": 0, "username": 1}):
    print("   -", staff["username"])

print("\n👌 Done. Exiting staff creator script.")
