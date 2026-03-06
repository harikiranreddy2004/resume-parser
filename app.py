import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
import logging
import re
import io
import tempfile
import PIL.Image
import pythoncom
import win32com.client
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from docx import Document
import pdfplumber
from pypdf import PdfReader

# Load environment variables from .env file
load_dotenv(override=True)

# Configure logging to file
logging.basicConfig(
    filename='app_debug.log',
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s'
)

app = Flask(__name__)
CORS(app)

# Gemini API Configuration
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    # Fallback to hardcoded only if necessary, but environmental is preferred
    GEMINI_API_KEY = "AIzaSyDL28S_PoHxCXFQE3oVlZOAAeNKLARPzBk"

logging.info(f"Using API Key: {GEMINI_API_KEY[:5]}...{GEMINI_API_KEY[-5:]}")
genai.configure(api_key=GEMINI_API_KEY)

def get_available_model():
    try:
        # Get all models that support generating content
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # Preference list
        preferences = [
            'models/gemini-2.5-flash',
            'models/gemini-2.0-flash',
            'models/gemini-1.5-flash',
            'models/gemini-flash-latest',
        ]
        
        for pref in preferences:
            if pref in models:
                logging.info(f"Using preferred model: {pref}")
                return pref
        
        if models:
            logging.info(f"Using first available model: {models[0]}")
            return models[0]
    except Exception as e:
        logging.error(f"Error listing models: {e}")
    
    return 'models/gemini-2.0-flash' # Fallback

# Initialize model dynamically
model_name = get_available_model()
model = genai.GenerativeModel(model_name)

def extract_text_from_pdf(file):
    text = ""
    try:
        # Try pdfplumber first
        file.seek(0)
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        
        # If pdfplumber failed to get any text, try pypdf as fallback
        if not text.strip():
            logging.info("pdfplumber returned no text, trying pypdf fallback...")
            file.seek(0)
            reader = PdfReader(file)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        logging.error(f"PDF extraction error: {e}")
    return text

def extract_text_from_docx(file):
    try:
        doc = Document(file)
        full_text = []
        
        # 1. Main body paragraphs
        full_text.extend([para.text for para in doc.paragraphs])
        
        # 2. Tables
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    full_text.append(cell.text)
                    
        # 3. Headers & Footers
        for section in doc.sections:
            for header in [section.header, section.footer]:
                if header:
                    full_text.extend([p.text for p in header.paragraphs])

        return "\n".join(full_text)
    except Exception as e:
        logging.error(f"DOCX extraction error: {e}")
        return ""

def extract_text_from_html(file):
    try:
        file.seek(0)
        # Preread to handle decoding
        raw_content = file.read()
        try:
            html_content = raw_content.decode('utf-8')
        except:
            html_content = raw_content.decode('latin-1', errors='ignore')
            
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Remove scripts, styles, and other metadata tag types
        for script_or_style in soup(["script", "style", "meta", "link", "noscript", "header", "footer", "nav"]):
            script_or_style.decompose()
            
        # Get text with better separation
        lines = (line.strip() for line in soup.get_text(separator="\n").splitlines())
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # Drop blank lines
        text = "\n".join(chunk for chunk in chunks if chunk)
        return text
    except Exception as e:
        logging.error(f"HTML extraction error: {e}")
        return ""

def extract_text_from_doc_legacy(file):
    # Save to tmp because win32com needs a file path
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".doc")
    os.close(tmp_fd)
    file.seek(0)
    with open(tmp_path, "wb") as f:
        f.write(file.read())
    
    pythoncom.CoInitialize()
    word = None
    combined_text = []
    try:
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        doc = word.Documents.Open(tmp_path, ReadOnly=True)
        
        # Standard content
        combined_text.append(doc.Content.Text)
        
        # Check all headers/footers and stories (textboxes, etc)
        # 1: wdMainTextStory, 6-11: Headers/Footers
        for i in range(1, 12):
            try:
                story = doc.StoryRanges(i)
                while story:
                    combined_text.append(story.Text)
                    story = story.NextStoryRange
            except:
                continue

        doc.Close(False)
    except Exception as e:
        logging.error(f"Legacy DOC error: {e}")
    finally:
        if word:
            try: word.Quit()
            except: pass
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        pythoncom.CoUninitialize()
    return "\n".join(combined_text)

@app.route('/scan', methods=['POST'])
def scan_resume():
    logging.info("Received scan request")
    if 'resume' not in request.files:
        logging.warning("No file uploaded")
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['resume']
    if file.filename == '':
        logging.warning("No file selected")
        return jsonify({"error": "No file selected"}), 400

    try:
        logging.info(f"File name: {file.filename}")
        filename = file.filename.lower()
        
        is_multimodal = False
        resume_text = ""
        multimodal_data = None
        mime_type = "application/octet-stream"

        # Pre-read bytes and reset pointer
        file.seek(0)
        file_bytes = file.read()
        file.seek(0)

        # 1. Primary Text Extraction
        if filename.endswith('.pdf'):
            resume_text = extract_text_from_pdf(file)
            mime_type = "application/pdf"
        elif filename.endswith('.docx'):
            resume_text = extract_text_from_docx(file)
        elif filename.endswith('.doc'):
            resume_text = extract_text_from_doc_legacy(file)
        elif filename.endswith(('.html', '.htm')):
            resume_text = extract_text_from_html(file)
        elif filename.endswith(('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff')):
            is_multimodal = True
            if filename.endswith('.webp'): mime_type = "image/webp"
            elif filename.endswith('.bmp'): mime_type = "image/bmp"
            elif filename.endswith('.tiff'): mime_type = "image/tiff"
            elif filename.endswith('.png'): mime_type = "image/png"
            else: mime_type = "image/jpeg"
            multimodal_data = file_bytes
        elif filename.endswith(('.txt', '.md', '.rtf')):
            resume_text = file_bytes.decode('utf-8', errors='ignore')
        else:
            # Universal Fallback: Try decoding as text, then try Gemini's multimodal
            try:
                resume_text = file_bytes.decode('utf-8')
                logging.info(f"Unknown extension {filename} successfully decoded as text")
            except:
                logging.info(f"Unknown extension {filename} binary detected, trying multimodal blob")
                is_multimodal = True
                multimodal_data = file_bytes
                mime_type = "application/octet-stream"

        # 2. Final check for empty text fallbacks
        if not is_multimodal and not resume_text.strip():
            if filename.endswith('.pdf'):
                logging.info("PDF text extraction empty, switching to Multimodal Vision path")
                is_multimodal = True
                multimodal_data = file_bytes
                mime_type = "application/pdf"
            elif filename.endswith(('.doc', '.docx', '.html', '.htm')):
                 # These aren't natively supported as blobs by Gemini for vision, so if text fails, we're stuck
                 logging.warning(f"No text extracted from document {filename}")
                 return jsonify({"error": f"Could not extract any content from the file '{file.filename}'. Please ensure it is not password protected."}), 400
            else:
                # Default to trying the blob for anything else that's empty
                logging.info(f"No text extracted from {filename}, trying multimodal blob fallback")
                is_multimodal = True
                multimodal_data = file_bytes
                mime_type = "application/octet-stream"

        prompt = """
        ACT AS A PROFESSIONAL RESUME PARSER. 
        Extract all details from the provided resume and return them ONLY in a valid JSON format.
        
        STRICT PARSING RULES:
        1. THE APPLICANT'S FULL NAME IS MANDATORY. 
           - Look at the VERY TOP of the document.
           - The largest, first text is almost always the name.
           - Never return an empty string for "full_name".
        2. NO conversational text, NO markdown code blocks, JUST JSON.
        3. Use empty strings "" for missing text fields and empty lists [] for missing arrays.

        JSON STRUCTURE:
        {
          "full_name": "Applicant Full Name",
          "contact_info": { "email": "", "phone": "", "linkedin": "" },
          "summary": "Short 2-3 sentence overview",
          "education": [{ "degree": "", "institution": "", "years": "" }],
          "experience": [{ "job_title": "", "company": "", "duration": "", "responsibilities": [] }],
          "skills": { "technical": [], "soft": [] },
          "projects": [{ "name": "", "description": "" }]
        }
        """

        if is_multimodal:
            logging.info(f"Sending multimodal request to Gemini ({mime_type})...")
            response = model.generate_content([
                prompt,
                {
                    "mime_type": mime_type,
                    "data": multimodal_data
                }
            ])
        else:
            logging.info(f"Extracted Resume Text (first 500 chars): {resume_text[:500]}")
            logging.info(f"Sending text request to Gemini (Text length: {len(resume_text)})...")
            full_prompt = f"{prompt}\n\nResume text:\n{resume_text}"
            response = model.generate_content(full_prompt)
        
        content = response.text.strip()
        logging.info(f"Raw Gemini Response: {content}")
        
        # Clean response: Handle markdown code blocks if they appear despite instructions
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
            
        # Extract the JSON part from the response using regex as a final fallback
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            content = json_match.group(0)
        
        try:
            data = json.loads(content)
            
            # Name Fallback: If AI misses the name or returns a placeholder, take the first line
            ai_name = data.get("full_name", "").lower()
            if (not ai_name or "not found" in ai_name or "unknown" in ai_name) and resume_text:
                first_lines = [line.strip() for line in resume_text.split("\n") if line.strip()]
                # Skip common noise at the start
                search_lines = first_lines[:5]
                for line in search_lines:
                    if len(line) > 3 and not any(kw in line.lower() for kw in ['resume', 'curriculum', 'page']):
                        data["full_name"] = line
                        logging.info(f"Using fallback name identification: {data['full_name']}")
                        break
            
            return jsonify(data)
        except json.JSONDecodeError:
            logging.error(f"Failed to parse JSON: {content}")
            return jsonify({"error": "Failed to parse AI response into JSON", "raw": content}), 500

    except Exception as e:
        logging.exception("Error occurred during scan")
        # Check for specific API key errors
        if "API_KEY_INVALID" in str(e):
            return jsonify({"error": "The Gemini API key provided is invalid. Please check your key."}), 401
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    logging.info("Starting server on port 5001")
    app.run(debug=True, port=5001)
