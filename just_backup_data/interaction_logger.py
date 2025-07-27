import json
from datetime import datetime, timedelta
import os

LOG_FILE = "interaction_log.json"

def plan_followup(sent_time):
    return sent_time + timedelta(days=5)

def log_interaction(entry, path=LOG_FILE):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                logs = json.load(f)
        else:
            logs = []
        logs.append(entry)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=2)
    except Exception as e:
        print("Logging failed:", e)
