import requests
import json

# Read key from .env
key = ""
try:
    with open('.env', encoding='utf-8') as f:
        for line in f:
            if 'GEMINI_API_KEY=' in line:
                key = line.strip().split('=', 1)[1]
except:
    pass

if not key:
    print("ERROR: No key found in .env")
    exit()

print(f"Using key: {key[:15]}...")

# Get all models from OpenRouter
r = requests.get(
    "https://openrouter.ai/api/v1/models",
    headers={"Authorization": "Bearer " + key}
)

print(f"Status: {r.status_code}")

if r.status_code == 200:
    models = r.json().get("data", [])
    free_models = [m for m in models if ":free" in m.get("id", "")]
    print(f"\n=== FREE MODELS ({len(free_models)} found) ===")
    for m in free_models[:20]:
        print(m["id"])
else:
    print(r.text[:300])
