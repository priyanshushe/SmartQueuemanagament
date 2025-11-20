from pymongo import MongoClient

# same URI and DB name as in app.py
client = MongoClient("mongodb://localhost:27017/")
db = client["smartqueue"]
staff_collection = db["staff"]

# change these to whatever you want
username = "admin"
password = "1234"   # plain text, because app.py checks plain text

staff_collection.insert_one({
    "username": username,
    "password": password
})

print("Staff user created:")
print("username:", username)
print("password:", password)
