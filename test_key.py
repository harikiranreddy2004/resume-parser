import google.generativeai as genai
import os
from dotenv import load_dotenv

def test_api_key():
    print(f"Current Working Directory: {os.getcwd()}")
    load_dotenv()
    key = os.environ.get('GEMINI_API_KEY')
    print(f"Loaded Key: '{key}'")
    if key:
        print(f"Key length: {len(key)}")
    
    if not key:
        print("ERROR: No GEMINI_API_KEY found in environment variables or .env file.")
        return

    try:
        genai.configure(api_key=key)
        # Try to list models as a simple check
        models = genai.list_models()
        print("SUCCESS: API key is valid. Found the following models:")
        for m in list(models)[:5]: # Just show first 5
            print(f"- {m.name}")
    except Exception as e:
        print(f"FAILURE: API key validation failed.")
        print(f"Error: {e}")

if __name__ == '__main__':
    test_api_key()
