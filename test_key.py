import os
from google import genai
from dotenv import load_dotenv

def test_gemini_key():
    print(f"Current Working Directory: {os.getcwd()}")
    load_dotenv(override=True)
    key = os.environ.get('GEMINI_API_KEY')
    
    if not key:
        print("ERROR: No GEMINI_API_KEY found in environment variables or .env file.")
        return

    print(f"Loaded Key: '{key[:10]}...{key[-5:]}'")
    print(f"Key length: {len(key)}")

    try:
        client = genai.Client(api_key=key)
        # Try to list models as a simple check
        models = client.models.list()
        print("SUCCESS: API key is valid. Found models.")
        # Print a few models
        for m in list(models)[:5]:
            print(f"- {m.name}")
    except Exception as e:
        print(f"FAILURE: API key validation failed.")
        print(f"Error: {e}")

if __name__ == '__main__':
    test_gemini_key()
