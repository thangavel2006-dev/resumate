import os
import uuid
import sqlite3
import fitz  # PyMuPDF
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from rapidfuzz import process, fuzz

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

DB_PATH = 'resumate.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, email TEXT UNIQUE, password TEXT, name TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS history (id TEXT PRIMARY KEY, user_id TEXT, job_title TEXT, score INTEGER, matched TEXT, missing TEXT, created_at TEXT)')
    conn.commit()
    conn.close()

init_db()

def extract_text_from_pdf(file_storage):
    try:
        pdf_bytes = file_storage.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = " ".join([page.get_text() for page in doc])
        file_storage.seek(0)
        return text.strip()
    except Exception as e:
        print(f"PDF Error: {e}")
        return ""

def calculate_ats_score(resume_text, job_desc):
    if not resume_text or not job_desc:
        return 0, [], ["Unable to read resume or description"]
    
    keywords = list(set([w.lower().strip(",.!") for w in job_desc.split() if len(w) > 3]))
    stops = {'with', 'from', 'this', 'that', 'their', 'work', 'using', 'strong', 'ability', 'required', 'client'}
    keywords = [w for w in keywords if w not in stops]

    matched, missing = [], []
    resume_words = resume_text.lower().split()
    
    for kw in keywords:
        res = process.extractOne(kw, resume_words, scorer=fuzz.ratio)
        if res and res[1] > 85:
            matched.append(kw)
        else:
            missing.append(kw)
            
    score = int((len(matched) / len(keywords)) * 100) if keywords else 0
    return score, list(set(matched))[:12], list(set(missing))[:12]

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    email, password = data.get('email'), data.get('password')
    hashed_pw = generate_password_hash(password)
    user_id = str(uuid.uuid4())
    try:
        conn = sqlite3.connect(DB_PATH)
        curr = conn.cursor()
        curr.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (user_id, email, hashed_pw, email.split('@')[0]))
        conn.commit()
        return jsonify({"id": user_id, "name": email.split('@')[0]}), 201
    except:
        return jsonify({"message": "User exists"}), 400
    finally: conn.close()

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    curr = conn.cursor()
    curr.execute("SELECT id, password, name FROM users WHERE email = ?", (data.get('email'),))
    user = curr.fetchone()
    conn.close()
    if user and check_password_hash(user[1], data.get('password')):
        return jsonify({"id": user[0], "name": user[2]}), 200
    return jsonify({"message": "Invalid Credentials"}), 401

@app.route('/analyze', methods=['POST'])
def analyze():
    user_id = request.form.get('user_id', 'guest')
    job_title = request.form.get('job_title', 'Role')
    description = request.form.get('description', '')
    file = request.files.get('resume')
    
    if not file:
        return jsonify({"message": "No file uploaded"}), 400

    text = extract_text_from_pdf(file)
    score, matched, missing = calculate_ats_score(text, description)
    
    # Dynamic Suggestions Logic
    if score < 40:
        suggestion = "Major mismatch. Focus on adding core technical skills and matching the job terminology closely."
    elif score < 70:
        suggestion = "Good start! Try to incorporate more of the missing keywords highlighted below into your experience bullet points."
    else:
        suggestion = "Excellent match! Your resume is highly optimized for this role."

    conn = sqlite3.connect(DB_PATH)
    curr = conn.cursor()
    curr.execute("INSERT INTO history VALUES (?, ?, ?, ?, ?, ?, ?)", 
                 (str(uuid.uuid4()), user_id, job_title, score, ",".join(matched), ",".join(missing), 
                  datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()

    return jsonify({
        "ats_score": score, 
        "matched": matched, 
        "missing": missing, 
        "suggestions": [suggestion] # Sending as a list for frontend compatibility
    })

@app.route('/history/<user_id>', methods=['GET'])
def get_history(user_id):
    conn = sqlite3.connect(DB_PATH)
    curr = conn.cursor()
    curr.execute("SELECT job_title, score, created_at FROM history WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
    rows = curr.fetchall()
    conn.close()
    return jsonify([{"job_title": r[0], "score": r[1], "created_at": r[2]} for r in rows])

if __name__ == '__main__':
    print("Backend ready at http://127.0.0.1:5000")
    app.run(debug=True, port=5000)