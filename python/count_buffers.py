from pymongo import MongoClient
from datetime import datetime, timedelta

# MongoDB setup
client = MongoClient('mongodb://localhost:27017/')
db = client.tracking_data
collection = db.test9

# Get total count
total = collection.count_documents({})

# Get count for last hour
since = datetime.utcnow() - timedelta(hours=1)
recent = collection.count_documents({"timestamp": {"$gte": since}})

print(f"Total buffers: {total}")
print(f"Buffers in last hour: {recent}")
if recent > 13:
    step = recent // 13
    print(f"\nSince there are more than 13 points ({recent} buffers):")
    print(f"Step size: {step}")
    print(f"This means each point in the graph represents the average of {step} buffers")
else:
    print("\nLess than 13 points, so no averaging is done") 