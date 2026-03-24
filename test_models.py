import requests

# Read key from .env
key = ""
with open('.env', encoding='utf-8') as f:
    for line in f:
        if 'GEMINI_API_KEY=' in line:
            key = line.strip().split('=', 1)[1]

print(f"Key: {key[:15]}...")

# Get free models
r = requests.get("https://openrouter.ai/api/v1/models", headers={"Authorization": "Bearer " + key})
models = [m["id"] for m in r.json().get("data", []) if ":free" in m.get("id", "")]

print(f"\nTesting {len(models)} free models...")
body = {"messages": [{"role": "user", "content": "say hi"}], "max_tokens": 10}

for model in models:
    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": "Bearer " + key, "Content-Type": "application/json", "HTTP-Referer": "http://localhost:5000"},
            json={**body, "model": model},
            timeout=10
        )
        if resp.status_code == 200:
            print(f"✅ WORKING: {model}")
            break
        else:
            print(f"❌ {resp.status_code}: {model}")
    except Exception as e:
        print(f"❌ Error: {model}: {e}")
