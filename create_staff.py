from pymongo import MongoClient

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["smartqueue"]
staff_collection = db["staff"]

while True:
    print("\n➕ Add New Staff User")
    username = input("Enter username: ")
    password = input("Enter password: ")

    staff_collection.insert_one({"username": username, "password": password})
    print("✔ Staff user added:", username)

    another = input("Add another staff? (yes/no): ").lower()
    if another not in ["yes", "y"]:
        print("\n👌 Exiting staff creator script.")
        break
