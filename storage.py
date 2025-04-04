import json
import os
from datetime import datetime
import csv

def load_users():
    with open("data/users.json") as f:
        return json.load(f)

def load_config():
    with open("data/config.json") as f:
        return json.load(f)

def save_config(config_obj):
    with open("data/config.json", "w") as f:
        json.dump(config_obj, f, indent=2)

def is_blackout(config):
    now = datetime.now()
    current_day = now.strftime("%a")[:3]  # e.g., "Mon"
    current_hour = now.hour
    day_blocks = config.get("blackout", {}).get(current_day, [])
    for block in day_blocks:
        if block["start"] <= current_hour < block["end"]:
            return True
    return False

def log_access(uid, name, status, snapshot_path):
    entry = {
        "uid": uid,
        "name": name,
        "status": status,
        "snapshot": snapshot_path,
        "timestamp": datetime.now().isoformat()
    }
    path = "data/logs.json"
    logs = []
    if os.path.exists(path):
        with open(path) as f:
            logs = json.load(f)
    logs.append(entry)
    with open(path, "w") as f:
        json.dump(logs, f, indent=2)

def load_logs():
    if os.path.exists("data/logs.json"):
        with open("data/logs.json") as f:
            return json.load(f)
    return []

def export_logs_to_csv(filepath="data/access_logs.csv"):
    logs = load_logs()
    with open(filepath, "w", newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=["timestamp", "uid", "name", "status", "snapshot"])
        writer.writeheader()
        for log in logs:
            writer.writerow(log)
