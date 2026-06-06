import os
import threading
from flask import Flask, render_template, jsonify
from scanner import scan_for_new_pdfs, save_state
from processor import process_new_pdfs, load_json

app = Flask(__name__)
PORT = 5000

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CERTS_FILE = os.path.join(DATA_DIR, "certs.json")
REVIEW_FILE = os.path.join(DATA_DIR, "needs_manual_review.json")

def startup_routine():
    print("Initializing CertBrain...")
    all_pdfs, new_pdfs, state = scan_for_new_pdfs()
    needs_review = load_json(REVIEW_FILE, [])
    
    print(f"Found {len(all_pdfs)} certs | {len(new_pdfs)} new | {len(needs_review)} need manual review")
    
    if new_pdfs:
        process_new_pdfs(new_pdfs, state)
        save_state(state)
        
    print(f"Done. Dashboard at http://localhost:{PORT}")

@app.route("/")
def index():
    certs = load_json(CERTS_FILE, [])
    needs_review = load_json(REVIEW_FILE, [])
    stats = {
        "total": len(certs) + len(needs_review),
        "processed": len(certs),
        "needs_review": len(needs_review)
    }
    return render_template("index.html", certs=certs, needs_review=needs_review, stats=stats)

@app.route("/api/scan", methods=["POST"])
def manual_scan():
    all_pdfs, new_pdfs, state = scan_for_new_pdfs()
    if new_pdfs:
        process_new_pdfs(new_pdfs, state)
        save_state(state)
        return jsonify({"status": "success", "message": f"Processed {len(new_pdfs)} new certs."})
    return jsonify({"status": "success", "message": "No new certs found."})

if __name__ == "__main__":
    startup_routine()
    app.run(host="127.0.0.1", port=PORT, debug=False)
