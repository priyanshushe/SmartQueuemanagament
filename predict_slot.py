from pymongo import MongoClient
import pandas as pd
from sklearn.linear_model import LinearRegression

client = MongoClient("mongodb://localhost:27017/")
db = client["smartqueue"]
tokens_collection = db["tokens"]

def predict_best_slot():
    tokens = list(tokens_collection.find({"slot_time": {"$exists": True}}))

    if len(tokens) < 5:
        return "11:00"

    df = pd.DataFrame(tokens)

    def time_to_minutes(t):
        h, m = map(int, t.split(":"))
        return h * 60 + m

    df["slot_minutes"] = df["slot_time"].apply(time_to_minutes)
    X = df[["token_number"]]
    y = df["slot_minutes"]

    model = LinearRegression()
    model.fit(X, y)

    next_token_num = df["token_number"].max() + 1
    predicted_minutes = model.predict([[next_token_num]])[0]

    predicted_minutes = max(9 * 60, min(17 * 60, predicted_minutes))

    best_hour = int(predicted_minutes // 60)
    best_minute = int(predicted_minutes % 60)

    return f"{best_hour:02d}:{best_minute:02d}"
