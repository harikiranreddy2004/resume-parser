import os
import re
import json
import subprocess
import tempfile
import psycopg2
import pdfplumber
import docx2txt
from bs4 import BeautifulSoup
from google import genai
import google.genai.types as types
from dotenv import load_dotenv

load_dotenv(override=True)

# -------- CONFIGURATION --------
TARGET_FOLDER = r"C:\Users\hkyar\OneDrive\Desktop\Resume parser"

DATABASE_CONFIG = {
    "host": "localhost",
    "database": "resume_parser_db",
    "user": "postgres",
    "password": "2004",
    "port": "5432"
}

SUPPORTED_FORMATS = [".pdf", ".docx", ".doc", ".html", ".htm", ".txt"]

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    print("Error: GEMINI_API_KEY not found in .env")
    exit(1)

client = genai.Client(api_key=API_KEY)

# -------- FILE READERS --------

def read_pdf(path):
    text = ""
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"PDF Error: {e}")
    return text

def read_docx(path):
    try:
        return docx2txt.process(path)
    except Exception as e:
        print(f"DOCX Error: {e}")
        return ""

def read_doc(path):
    try:
        temp_dir = tempfile.gettempdir()
        soffice_path = r"C:\Program Files\LibreOffice\program\soffice.exe"
        if not os.path.exists(soffice_path):
            soffice_path = r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"
        
        if not os.path.exists(soffice_path):
            print("LibreOffice not found for .doc conversion")
            return ""
            
        subprocess.run([soffice_path, "--headless", "--convert-to", "docx", path, "--outdir", temp_dir], check=True)
        filename = os.path.basename(path)
        converted_file = os.path.join(temp_dir, filename.rsplit(".", 1)[0] + ".docx")
        if os.path.exists(converted_file):
            text = docx2txt.process(converted_file)
            os.remove(converted_file)
            return text
    except Exception as e:
        print(f"DOC Error: {e}")
    return ""

def read_html(path):
    try:
        with open(path, "r", encoding="utf-8") as file:
            soup = BeautifulSoup(file.read(), "html.parser")
            for s in soup(["script", "style"]):
                s.decompose()
            return soup.get_text(separator="\n")
    except Exception as e:
        print(f"HTML Error: {e}")
        return ""

# -------- GEMINI PARSER --------

def parse_resume_with_ai(text):
    prompt = f"""
You are an expert resume parser. Extract information in JSON format.

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
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"AI Parsing Error: {e}")
        return None

# -------- DATABASE FUNCTION --------

def save_to_database(data):
    try:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        cursor = conn.cursor()

        query = """
        INSERT INTO resumes 
        (full_name, email, phone, summary, skills, education, experience, projects)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        cursor.execute(query, (
            data.get("full_name"),
            data.get("contact_info", {}).get("email"),
            data.get("contact_info", {}).get("phone"),
            data.get("summary"),
            json.dumps(data.get("skills")),
            json.dumps(data.get("education")),
            json.dumps(data.get("experience")),
            json.dumps(data.get("projects"))
        ))
        conn.commit()
        cursor.close()
        conn.close()
        print(f"Saved to DB: {data.get('full_name')}")
    except Exception as e:
        print(f"Database Error: {e}")

# -------- MAIN PROCESS --------

print(f"Scanning folder: {TARGET_FOLDER}\n")

if not os.path.exists(TARGET_FOLDER):
    print(f"Error: Target folder {TARGET_FOLDER} does not exist.")
    exit(1)

for filename in os.listdir(TARGET_FOLDER):
    file_path = os.path.join(TARGET_FOLDER, filename)
    ext = os.path.splitext(filename)[1].lower()

    if ext not in SUPPORTED_FORMATS:
        continue

    print(f"Processing: {filename}")
    raw_text = ""

    if ext == ".pdf":
        raw_text = read_pdf(file_path)
    elif ext == ".docx":
        raw_text = read_docx(file_path)
    elif ext == ".doc":
        raw_text = read_doc(file_path)
    elif ext in [".html", ".htm"]:
        raw_text = read_html(file_path)
    elif ext == ".txt":
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                raw_text = f.read()
        except: pass

    if not raw_text or not raw_text.strip():
        print(f"Could not extract text from {filename}")
        continue

    result = parse_resume_with_ai(raw_text)
    if result:
        save_to_database(result)
        print("-" * 40)

print("All resumes processed!")