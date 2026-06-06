import os
import json
from pathlib import Path

# Config
CERTS_DIR = os.path.expanduser("~/Documents/certs-pdf")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
STATE_FILE = os.path.join(DATA_DIR, "state.json")

def ensure_dirs_exist():
    os.makedirs(CERTS_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)
    
    if not os.path.exists(STATE_FILE):
        with open(STATE_FILE, "w") as f:
            json.dump({"last_known_count": 0, "processed_files": []}, f)

def load_state():
    ensure_dirs_exist()
    with open(STATE_FILE, "r") as f:
        return json.load(f)

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def scan_for_new_pdfs():
    ensure_dirs_exist()
    state = load_state()
    processed_files = set(state.get("processed_files", []))
    
    all_pdfs = [f for f in os.listdir(CERTS_DIR) if f.lower().endswith(".pdf")]
    new_pdfs = [f for f in all_pdfs if f not in processed_files]
    
    return all_pdfs, new_pdfs, state
