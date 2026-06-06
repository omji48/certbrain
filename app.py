# -*- coding: utf-8 -*-
import os
import json
import threading
from flask import Flask, jsonify, render_template, request, send_from_directory
from scanner import scan_certs
from processor import process_new_certs, deduplicate_certs

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="/static")

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CERTS_FILE = os.path.join(DATA_DIR, "certs.json")
STATE_FILE = os.path.join(DATA_DIR, "state.json")
REVIEW_FILE = os.path.join(DATA_DIR, "needs_manual_review.json")

os.makedirs(DATA_DIR, exist_ok=True)


def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default


@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/api/certs")
def api_certs():
    certs = deduplicate_certs(load_json(CERTS_FILE, []))
    return jsonify(certs)


@app.route("/api/stats")
def api_stats():
    certs = deduplicate_certs(load_json(CERTS_FILE, []))
    state = load_json(STATE_FILE, {})
    review = load_json(REVIEW_FILE, [])
    return jsonify({
        "total": len(certs),
        "last_updated": state.get("last_updated", "Never"),
        "pending_review": len(review),
        "pending_review_files": review,
    })


@app.route("/api/scan", methods=["POST"])
def api_scan():
    """Trigger a manual scan."""
    def run_scan():
        new_pdfs, _ = scan_certs(force=True)
        if new_pdfs:
            process_new_certs(new_pdfs)

    t = threading.Thread(target=run_scan, daemon=True)
    t.start()
    return jsonify({"status": "scan_started"})


@app.route("/api/scan_status")
def api_scan_status():
    state = load_json(STATE_FILE, {})
    return jsonify({
        "scanning": state.get("scanning", False),
        "last_updated": state.get("last_updated", "Never"),
    })


if __name__ == "__main__":
    import sys
    from datetime import datetime

    # ── Startup scan ──────────────────────────────────────────────────────────
    print("\nCertBrain starting up...")
    new_pdfs, summary = scan_certs()

    new_count = summary["new"]
    total_count = summary["total"]
    review_count = summary["needs_review"]

    if new_pdfs:
        process_new_certs(new_pdfs)
        # Refresh counts after processing
        review_data = load_json(REVIEW_FILE, [])
        review_count = len(review_data)

    print("\nFound {} certs | {} new | {} need manual review".format(total_count, new_count, review_count))
    print("Done. Dashboard at http://localhost:5000\n")

    app.run(host="0.0.0.0", port=5000, debug=False)
