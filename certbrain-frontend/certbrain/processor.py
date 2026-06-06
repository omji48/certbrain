import os
import json
import requests
import pdfplumber

CERTS_DIR = os.path.expanduser("~/Documents/certs-pdf")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CERTS_FILE = os.path.join(DATA_DIR, "certs.json")
MD_FILE = os.path.join(DATA_DIR, "certs.md")
REVIEW_FILE = os.path.join(DATA_DIR, "needs_manual_review.json")

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "gpt-os-120b"

def load_json(filepath, default):
    if not os.path.exists(filepath):
        return default
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except:
        return default

def save_json(filepath, data):
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")
        return None
    return text.strip()

def process_with_ollama(text):
    prompt = """You are processing a certification document for Om Mehta, 
a cybersecurity student. Extract and return ONLY valid JSON 
with these keys:
cert_name, issuer, year, one_liner (max 10 words), 
learnings (array of exactly 3 strings), 
use_case (1-2 sentences, practical and real),
interview_answer (2-3 sentences, confident, conversational, 
first person, no jargon overload)

If any field cannot be determined, use null.
Return nothing except the JSON object.

DOCUMENT TEXT:
""" + text

    try:
        response = requests.post(OLLAMA_URL, json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }, timeout=60)
        response.raise_for_status()
        
        # Some models return markdown blocks (```json ... ```)
        result_text = response.json().get("response", "{}")
        if result_text.startswith("```json"):
            result_text = result_text.split("```json")[-1].split("```")[0].strip()
        elif result_text.startswith("```"):
            result_text = result_text.split("```")[-1].split("```")[0].strip()

        return json.loads(result_text)
    except Exception as e:
        print(f"Ollama API Error: {e}")
        return None

def update_markdown(certs):
    with open(MD_FILE, "w") as f:
        f.write("# CertBrain Knowledge Base\n\n")
        for cert in certs:
            f.write(f"## {cert.get('cert_name', 'Unknown')}\n")
            f.write(f"**Issuer:** {cert.get('issuer', 'Unknown')} | **Year:** {cert.get('year', 'Unknown')}\n\n")
            f.write(f"> {cert.get('one_liner', '')}\n\n")
            f.write("### Learnings\n")
            for learning in cert.get('learnings', []):
                f.write(f"- {learning}\n")
            f.write(f"\n### Practical Use Case\n{cert.get('use_case', '')}\n\n")
            f.write(f"### Interview Answer\n\"{cert.get('interview_answer', '')}\"\n\n")
            f.write("---\n\n")

def process_new_pdfs(new_pdfs, state):
    if not new_pdfs:
        return

    certs = load_json(CERTS_FILE, [])
    needs_review = set(load_json(REVIEW_FILE, []))
    processed_files = set(state.get("processed_files", []))

    for pdf_file in new_pdfs:
        print(f"Processing: {pdf_file}")
        pdf_path = os.path.join(CERTS_DIR, pdf_file)
        text = extract_text_from_pdf(pdf_path)

        if not text or len(text) < 50:
            needs_review.add(pdf_file)
            print(f"  -> Flagged for manual review (unreadable / image-only)")
        else:
            cert_data = process_with_ollama(text)
            if cert_data:
                cert_data['_filename'] = pdf_file
                certs.append(cert_data)
                print(f"  -> Successfully extracted data for '{cert_data.get('cert_name')}'")
            else:
                needs_review.add(pdf_file)
                print(f"  -> Flagged for manual review (LLM extraction failed)")

        processed_files.add(pdf_file)

    # Save everything
    save_json(CERTS_FILE, certs)
    save_json(REVIEW_FILE, list(needs_review))
    
    state["last_known_count"] = len(processed_files)
    state["processed_files"] = list(processed_files)
    
    update_markdown(certs)
