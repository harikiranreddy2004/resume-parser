import os
from google import genai
from dotenv import load_dotenv

load_dotenv(override=True)
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("Error: GEMINI_API_KEY not found in .env")
else:
    client = genai.Client(api_key=api_key)
    with open("models.txt", "w") as f:
        try:
            models = client.models.list()
            for m in models:
                f.write(f"{m.name}\n")
            print("Gemini Models saved to models.txt")
        except Exception as e:
            f.write(f"Error: {e}\n")
            print(f"Error: {e}")