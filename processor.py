# -*- coding: utf-8 -*-
"""
processor.py - extracts text from PDFs and sends to Ollama Cloud
for structured JSON extraction using gemma4:27b via OpenAI-compatible API.
"""
import sys
import io
# Force UTF-8 output so Windows terminal doesn't choke
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import os
import json
import re
from datetime import datetime
from openai import OpenAI

import pdfplumber

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CERTS_FILE = os.path.join(DATA_DIR, "certs.json")
CERTS_MD_FILE = os.path.join(DATA_DIR, "certs.md")
REVIEW_FILE = os.path.join(DATA_DIR, "needs_manual_review.json")

# ── Ollama Cloud config ───────────────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv()

OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY", "")
OLLAMA_BASE_URL = "https://ollama.com/v1"
OLLAMA_MODEL = "gemma3:27b"

_client = OpenAI(
    base_url=OLLAMA_BASE_URL,
    api_key=OLLAMA_API_KEY,
)

EXTRACTION_PROMPT = """You are processing a certification document for Om Mehta, a cybersecurity student. Extract and return ONLY valid JSON with these keys:
cert_name, issuer, year, one_liner (max 10 words), learnings (array of exactly 3 strings), use_case (1-2 sentences, practical and real), interview_answer (2-3 sentences, confident, conversational, first person, no jargon overload)

If any field cannot be determined, use null.
Return nothing except the JSON object."""

# Supported file types
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png")

os.makedirs(DATA_DIR, exist_ok=True)

def load_certs():
    if os.path.exists(CERTS_FILE):
        try:
            with open(CERTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def load_review():
    if os.path.exists(REVIEW_FILE):
        try:
            with open(REVIEW_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_certs(certs):
    with open(CERTS_FILE, "w", encoding="utf-8") as f:
        json.dump(certs, f, indent=2, ensure_ascii=False)


def save_review(review):
    with open(REVIEW_FILE, "w", encoding="utf-8") as f:
        json.dump(review, f, indent=2)


def save_markdown(certs):
    lines = ["# CertBrain — Certificate Knowledge Base\n"]
    lines.append(f"_Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_\n")
    lines.append(f"**Total Certs:** {len(certs)}\n\n---\n")

    for cert in certs:
        name = cert.get("cert_name") or "Unknown Cert"
        issuer = cert.get("issuer") or "Unknown Issuer"
        year = cert.get("year") or "N/A"
        one_liner = cert.get("one_liner") or ""
        learnings = cert.get("learnings") or []
        use_case = cert.get("use_case") or ""
        interview = cert.get("interview_answer") or ""

        lines.append(f"## {name}\n")
        lines.append(f"**Issuer:** {issuer}  |  **Year:** {year}\n\n")
        if one_liner:
            lines.append(f"> {one_liner}\n\n")
        if learnings:
            lines.append("### Key Learnings\n")
            for l in learnings:
                lines.append(f"- {l}\n")
            lines.append("\n")
        if use_case:
            lines.append(f"### Use Case\n{use_case}\n\n")
        if interview:
            lines.append(f"### Interview Answer\n_{interview}_\n\n")
        lines.append("---\n\n")

    with open(CERTS_MD_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)


def extract_text_from_pdf(pdf_path):
    """
    Attempts to extract text from a PDF using pdfplumber.
    Returns (text, is_readable).
    """
    try:
        text_parts = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text_parts.append(t.strip())
        full_text = "\n".join(text_parts).strip()
        if len(full_text) < 50:
            # Too little text — likely image-only
            return full_text, False
        return full_text, True
    except Exception as e:
        print(f"  [WARN] Error reading {os.path.basename(pdf_path)}: {e}")
        return "", False


def query_ollama_vision(image_path):
    """
    Sends a certificate image directly to Ollama Cloud (gemma3:27b vision).
    Returns parsed JSON dict, or None on failure.
    """
    import base64
    ext = os.path.splitext(image_path)[1].lower()
    mime = "image/png" if ext == ".png" else "image/jpeg"

    try:
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        print(f"  [ERROR] Could not read image file: {e}")
        return None

    try:
        response = _client.chat.completions.create(
            model=OLLAMA_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a structured data extractor. Return ONLY valid JSON, no markdown, no explanation.",
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": EXTRACTION_PROMPT,
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime};base64,{b64}"
                            },
                        },
                    ],
                },
            ],
            temperature=0.1,
            timeout=120,
        )
        raw = response.choices[0].message.content.strip()

        # Strip markdown code fences if model wrapped JSON in them
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return json.loads(raw)

    except json.JSONDecodeError as e:
        print(f"  [ERROR] JSON parse error from vision response: {e}")
        return None
    except Exception as e:
        print(f"  [ERROR] Ollama Cloud vision error: {e}")
        return None

def query_ollama(text):
    """
    Sends extracted text to Ollama Cloud (gemma3:27b) via OpenAI-compatible API.
    Returns parsed JSON dict, or None on failure.
    """
    prompt = f"{EXTRACTION_PROMPT}\n\nDocument text:\n{text[:6000]}"
    try:
        response = _client.chat.completions.create(
            model=OLLAMA_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a structured data extractor. Return ONLY valid JSON, no markdown, no explanation.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.1,
            timeout=120,
        )
        raw = response.choices[0].message.content.strip()

        # Strip markdown code fences if model wrapped JSON in them
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        # Try to extract JSON object from response
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return json.loads(raw)

    except json.JSONDecodeError as e:
        print(f"  [ERROR] JSON parse error from cloud response: {e}")
        return None
    except Exception as e:
        print(f"  [ERROR] Ollama Cloud error: {e}")
        return None


def _norm_name(name):
    """Normalize a cert name for duplicate comparison."""
    if not name:
        return ""
    import re as _re
    return _re.sub(r"\s+", " ", str(name).lower().strip())


def _count_non_null(cert):
    """Count how many top-level values in a cert dict are non-null/non-empty."""
    keys = ["cert_name", "issuer", "year", "one_liner", "learnings", "use_case", "interview_answer"]
    score = 0
    for k in keys:
        v = cert.get(k)
        if v is not None and v != [] and v != [None, None, None]:
            score += 1
    return score


def deduplicate_certs(certs):
    """
    Remove duplicate certs by normalized cert_name.
    When duplicates exist, keep the entry with the most non-null fields.
    Merge source_file lists so we know all PDFs that contributed.
    Certs with no name (null) are each kept separately by their source_file.
    """
    named = {}   # norm_name -> best cert dict
    unnamed = [] # certs where cert_name is null — keep all, dedup by source_file

    seen_sources = set()

    for cert in certs:
        norm = _norm_name(cert.get("cert_name"))
        src = cert.get("source_file", "")

        if not norm:
            # No name extracted — bucket by source file
            if src not in seen_sources:
                seen_sources.add(src)
                unnamed.append(cert)
            continue

        if norm not in named:
            named[norm] = dict(cert)
            # Ensure source_files list exists
            named[norm]["source_files"] = [src] if src else []
        else:
            existing = named[norm]
            # Track all contributing source files
            if src and src not in existing.get("source_files", []):
                existing.setdefault("source_files", []).append(src)
            # Keep whichever entry has richer data
            if _count_non_null(cert) > _count_non_null(existing):
                src_files = existing.get("source_files", [])
                named[norm] = dict(cert)
                named[norm]["source_files"] = src_files

    result = list(named.values()) + unnamed
    return result


def process_new_certs(pdf_paths):
    """
    Process a list of new PDF file paths:
    - Extract text
    - Flag unreadable ones
    - Query Ollama
    - Save results
    """
    existing_certs = load_certs()
    review_list = load_review()
    # Track already-processed source files
    processed_sources = {c.get("source_file") for c in existing_certs}

    new_certs = []

    for file_path in pdf_paths:
        filename = os.path.basename(file_path)
        if filename in processed_sources:
            continue

        ext = os.path.splitext(filename)[1].lower()
        is_image = ext in IMAGE_EXTENSIONS

        print(f"  [>>] Processing: {filename}")

        if is_image:
            # Route image files directly to the vision model
            print(f"  [IMG] Sending image to vision model: {filename}")
            cert_data = query_ollama_vision(file_path)
        else:
            # PDF path: extract text first
            text, is_readable = extract_text_from_pdf(file_path)

            if not is_readable:
                print(f"  [FLAG] Needs manual review: {filename}")
                if filename not in review_list:
                    review_list.append(filename)
                save_review(review_list)
                continue

            cert_data = query_ollama(text)

        if cert_data is None:
            stem = os.path.splitext(filename)[0]
            cert_data = {
                "cert_name": stem,
                "issuer": None,
                "year": None,
                "one_liner": "Could not extract — Ollama unavailable",
                "learnings": [None, None, None],
                "use_case": None,
                "interview_answer": None,
            }

        cert_data["source_file"] = filename
        cert_data["processed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_certs.append(cert_data)
        print(f"  [OK] Done: {cert_data.get('cert_name', filename)}")

    all_certs = deduplicate_certs(existing_certs + new_certs)
    dupes_removed = (len(existing_certs) + len(new_certs)) - len(all_certs)
    if dupes_removed:
        print(f"  [DEDUP] Removed {dupes_removed} duplicate cert(s)")
    save_certs(all_certs)
    save_markdown(all_certs)

    # Update state last_updated timestamp
    state_file = os.path.join(DATA_DIR, "state.json")
    state = {}
    if os.path.exists(state_file):
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            pass
    state["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    state["scanning"] = False
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

    print(f"\n  [SAVED] {len(all_certs)} total certs written to data/certs.json")
    if review_list:
        print(f"  [REVIEW] {len(review_list)} cert(s) flagged for manual review")

    return new_certs
