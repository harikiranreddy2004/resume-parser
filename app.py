import os
import json
import tempfile
import subprocess
import time   # ✅ ADDED (for API delay)

import pdfplumber
import docx
import psycopg2

import pytesseract
from PIL import Image
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from flask_cors import CORS
from dotenv import load_dotenv

from google import genai
import google.genai.types as types


# ---------------- LOAD ENV ----------------
load_dotenv(override=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env file")

client = genai.Client(api_key=GEMINI_API_KEY)


# ---------------- FLASK APP ----------------
app = Flask(__name__)
CORS(app)

# Check if Tesseract is installed at the default path
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.exists(TESSERACT_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
else:
    print("Warning: Tesseract OCR not found. Scanned PDFs and images may not be readable.")


# ---------------- DATABASE CONNECTION ----------------
def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        database="resume_parser_db",
        user="postgres",
        password="2004",
        port="5432"
    )


# ---------------- SAVE RESUME ----------------
def save_resume(data):

    conn = get_db_connection()
    cursor = conn.cursor()

    contact = data.get("contact_info")
    if not isinstance(contact, dict):
        contact = {}

    cursor.execute("""
        INSERT INTO resumes
        (full_name, email, phone, summary, skills, education, experience, projects)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        data.get("full_name"),
        contact.get("email"),
        contact.get("phone"),
        data.get("summary"),
        json.dumps(data.get("skills") or {}),
        json.dumps(data.get("education") or []),
        json.dumps(data.get("experience") or []),
        json.dumps(data.get("projects") or [])
    ))

    conn.commit()
    cursor.close()
    conn.close()


# ---------------- TEXT EXTRACTION ----------------
def extract_text(file):

    text = ""
    temp_path = None
    converted_path = None

    try:
        filename = secure_filename(file.filename)
        ext = filename.split(".")[-1].lower()

        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, filename)

        file.save(temp_path)

        # -------- PDF --------
        if ext == "pdf":

            try:
                with pdfplumber.open(temp_path) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"

            except Exception as e:
                print("pdfplumber error:", e)

            if not text.strip():
                try:
                    if os.path.exists(TESSERACT_PATH):
                        image = Image.open(temp_path)
                        text = pytesseract.image_to_string(image)
                except:
                    pass


        # -------- DOCX --------
        elif ext == "docx":

            try:
                import docx2txt
                text = docx2txt.process(temp_path)

            except:
                doc = docx.Document(temp_path)
                for para in doc.paragraphs:
                    text += para.text + "\n"


        # -------- DOC --------
        elif ext == "doc":

            possible_soffice_paths = [
                r"C:\Program Files\LibreOffice\program\soffice.exe",
                r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"
            ]

            soffice_path = next((p for p in possible_soffice_paths if os.path.exists(p)), None)

            if not soffice_path:
                raise FileNotFoundError("LibreOffice not found")

            subprocess.run(
                [soffice_path, "--headless", "--convert-to", "docx", temp_path, "--outdir", temp_dir],
                check=True
            )

            converted_file = os.path.join(temp_dir, filename.rsplit(".", 1)[0] + ".docx")

            converted_path = converted_file

            if os.path.exists(converted_file):
                import docx2txt
                text = docx2txt.process(converted_file)


        # -------- HTML --------
        elif ext in ["html", "htm"]:

            with open(temp_path, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f, "html.parser")

                for s in soup(["script", "style"]):
                    s.decompose()

                text = soup.get_text(separator="\n")


        # -------- IMAGE --------
        elif ext in ["jpg", "jpeg", "png", "bmp", "tiff"]:
            if os.path.exists(TESSERACT_PATH):
                image = Image.open(temp_path)
                text = pytesseract.image_to_string(image)
            else:
                raise ValueError("Tesseract OCR not installed. Cannot process images.")


        # -------- TXT --------
        elif ext == "txt":

            for enc in ['utf-8', 'latin-1', 'cp1252']:
                try:
                    with open(temp_path, "r", encoding=enc) as f:
                        text = f.read()
                        break
                except:
                    continue

        else:
            raise ValueError("Unsupported file format")


    except Exception as e:
        print("Extraction error:", e)
        raise ValueError(str(e))

    finally:

        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

        if converted_path and os.path.exists(converted_path):
            os.remove(converted_path)


    if not text.strip():
        raise ValueError("File contains no readable text")

    return text


# ---------------- GEMINI RESUME PARSER ----------------
def parse_resume(text):

    text = text[:12000]   # ✅ prevent very long inputs

    prompt = f"""
You are an expert resume parser.
Extract resume information and return ONLY valid JSON.

Schema:
{{
 "full_name": "",
 "skills": {{"technical": [], "soft": []}},
 "education": [{{"degree": "", "institution": ""}}],
 "experience": [{{"job_title": "", "company": "", "duration": ""}}],
 "projects": [{{"name": "", "description": ""}}],
 "summary": "",
 "contact_info": {{"email": "", "phone": ""}}
}}

Resume Text:
{text}
"""

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )

            time.sleep(1) # small delay
            return json.loads(response.text)

        except Exception as e:
            if "429" in str(e):
                print(f"Rate limit hit (429), retrying in 10s... (Attempt {attempt+1}/3)")
                time.sleep(10)
                continue
            
            print("Gemini API Error:", str(e))
            return {"error": str(e)}
    
    return {"error": "API quota exceeded. Please try again in a minute."}


# ---------------- HOME ROUTE ----------------
@app.route("/")
def index():
    return render_template("index.html")


# ---------------- SCAN API ----------------
@app.route("/scan", methods=["POST"])
def scan():

    if "resume" not in request.files:
        return jsonify({"error": "No resume file provided"}), 400

    file = request.files["resume"]

    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    try:
        text = extract_text(file)

    except Exception as e:
        return jsonify({"error": str(e)}), 400


    result = parse_resume(text)

    if "error" in result:
        return jsonify({"error": result["error"]}), 500


    save_resume(result)

    return jsonify(result)


# ---------------- VIEW RESUMES ----------------
@app.route("/resumes")
def view_resumes():

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, full_name, email, phone, summary FROM resumes"
    )

    resumes = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("resumes.html", resumes=resumes)


# ---------------- RUN SERVER ----------------
if __name__ == "__main__":

    print("Server running at http://127.0.0.1:5001")

    app.run(
        host="127.0.0.1",
        port=5001,
        debug=True
    )