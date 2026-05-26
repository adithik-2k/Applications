import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

print("Listing models...")
try:
    models = client.models.list()
    for m in models:
        # Just print the whole object or name
        print(m.name)
except Exception as e:
    print(f"Error listing models: {e}")
