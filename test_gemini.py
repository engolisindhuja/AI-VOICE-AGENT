import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
c = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

for name in ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-3.7-flash"]:
    try:
        r = c.models.generate_content(model=name, contents="Say hi")
        print("OK  ", name, "->", r.text.strip())
    except Exception as e:
        print("FAIL", name, "->", str(e)[:80])