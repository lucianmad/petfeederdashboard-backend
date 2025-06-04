from flask import Flask, jsonify
from flask_cors import CORS
import boto3
import time
from decimal import Decimal
from boto3.dynamodb.conditions import Key
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)
dynamodb = boto3.resource('dynamodb', region_name='eu-north-1')
table = dynamodb.Table('BowlEventsTable')

DEVICE_ID = 'bowl_1'

def parse_decimal(obj):
    if isinstance(obj, list):
        return [parse_decimal(i) for i in obj]
    if isinstance(obj, dict):
        return {k: parse_decimal(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        return float(obj)
    return obj

@app.route("/api/latest-events")
def latest_events():
    resp = table.query(
        KeyConditionExpression=Key('device_id').eq(DEVICE_ID),
        ScanIndexForward=False,  # DESC order
        Limit=20
    )
    return jsonify(parse_decimal(resp["Items"]))

@app.route("/api/stats/last-24h")
def stats_last_24h():
    cutoff = int(time.time()) - 86400
    resp = table.query(
        KeyConditionExpression=Key('device_id').eq(DEVICE_ID) & Key('timestamp').gte(cutoff)
    )
    counts = {"dog": 0, "cat": 0, "other": 0}
    for item in resp["Items"]:
        obj = item.get("detected_object", "other")
        if obj not in counts:
            obj = "other"
        counts[obj] += 1
    return jsonify(counts)

@app.route("/api/stats/by-hour")
def stats_by_hour():
    cutoff = int(time.time()) - 86400
    resp = table.query(
        KeyConditionExpression=Key('device_id').eq(DEVICE_ID) & Key('timestamp').gte(cutoff)
    )
    hourly = {f"{h:02d}": {"dog": 0, "cat": 0, "other": 0} for h in range(24)}
    for item in resp["Items"]:
        ts = int(item["timestamp"])
        obj = item.get("detected_object", "other")
        if obj not in ["dog", "cat"]:
            obj = "other"
        hour = datetime.fromtimestamp(ts).strftime("%H")
        hourly[hour][obj] += 1
    return jsonify(hourly)

@app.route("/api/photos")
def photo_gallery():
    cutoff = int(time.time()) - 86400
    resp = table.query(
        KeyConditionExpression=Key('device_id').eq(DEVICE_ID) & Key('timestamp').gte(cutoff)
    )
    photos = [
        {
            "timestamp": item["timestamp"],
            "photo_url": item["photo_url"],
            "detected_object": item.get("detected_object", "unknown")
        }
        for item in resp["Items"]
        if "photo_url" in item and item["photo_url"]
    ]
    sorted_photos = sorted(photos, key=lambda x: x["timestamp"], reverse=True)
    return jsonify(parse_decimal(sorted_photos))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
