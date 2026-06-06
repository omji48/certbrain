"""
scanner.py — scans ~/Documents/certs-pdf for PDFs,
compares against stored state, returns new files.
"""

import os
import json
from datetime import datetime

CERT_DIR = os.path.abspath(os.path.expanduser("~/Documents/certs-pdf"))
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
STATE_FILE = os.path.join(DATA_DIR, "state.json")

SUPPORTED_EXTENSIONS = (".pdf", ".jpg", ".jpeg", ".png")

os.makedirs(DATA_DIR, exist_ok=True)


def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_state(state: dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def get_pdf_files():
    """Return list of supported cert filenames found in the certs directory."""
    if not os.path.exists(CERT_DIR):
        os.makedirs(CERT_DIR, exist_ok=True)
        return []
    return [
        f for f in os.listdir(CERT_DIR)
        if f.lower().endswith(SUPPORTED_EXTENSIONS)
    ]


def scan_certs(force=False):
    """
    Scan CERT_DIR for PDFs, compare with saved state.

    Returns:
        new_pdfs (list[str]): Full paths to PDFs that are new.
        summary  (dict):      {total, new, needs_review}
    """
    state = load_state()
    known_files = set(state.get("files", []))

    current_files = get_pdf_files()
    current_set = set(current_files)

    new_files = list(current_set - known_files)

    if force:
        # On manual scan, reprocess everything not yet in certs.json
        certs_file = os.path.join(DATA_DIR, "certs.json")
        processed = set()
        if os.path.exists(certs_file):
            try:
                with open(certs_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                processed = {c.get("source_file", "") for c in data}
            except Exception:
                pass
        new_files = [f for f in current_files if f not in processed]

    # Update state with current file list (filenames only, not full paths)
    state["files"] = list(current_set)
    state["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_state(state)

    review_file = os.path.join(DATA_DIR, "needs_manual_review.json")
    review_count = 0
    if os.path.exists(review_file):
        try:
            with open(review_file, "r", encoding="utf-8") as f:
                review_count = len(json.load(f))
        except Exception:
            pass

    summary = {
        "total": len(current_files),
        "new": len(new_files),
        "needs_review": review_count,
    }

    # Return full paths for processing
    full_paths = [os.path.join(CERT_DIR, f) for f in new_files]
    return full_paths, summary
