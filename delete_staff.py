from pymongo import MongoClient

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["smartqueue"]
staff_collection = db["staff"]

print("🗑 STAFF DELETION TOOL")

while True:
    print("\n📋 Current staff users:")
    for staff in staff_collection.find({}, {"_id": 0, "username": 1}):
        print("   -", staff["username"])

    username = input("\nEnter the username to delete (or 'exit' to quit): ").strip()

    if username.lower() == "exit":
        print("👋 Exiting tool.")
        break

    result = staff_collection.delete_one({"username": username})

    if result.deleted_count > 0:
        print(f"✔ Staff '{username}' deleted successfully.")
    else:
        print(f"⚠ Staff '{username}' not found in database.")

    another = input("\nDelete another? (yes/no): ").lower()
    if another not in ["yes", "y"]:
        break

print("\n🏁 Done.")
