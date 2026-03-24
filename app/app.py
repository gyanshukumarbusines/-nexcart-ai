"""
NexCart — Complete AI Shopping Platform
Flask server: serves all pages + chatbot API
Run: python3 app.py
Open: http://localhost:5000
"""

import json
import os
import re
from flask import Flask, render_template, jsonify, request, send_from_directory
import requests as http_requests

# ─── Load .env file automatically ─────────────────────────────────────────────
def load_env():
    """Load .env file from project root (parent of app/)."""
    env_paths = [
        os.path.join(os.path.dirname(__file__), '..', '.env'),
        os.path.join(os.path.dirname(__file__), '.env'),
        '.env',
    ]
    for path in env_paths:
        path = os.path.abspath(path)
        if os.path.exists(path):
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, val = line.split('=', 1)
                        os.environ[key.strip()] = val.strip()
            print(f"  ✅  Loaded .env from {path}")
            return
    print("  ⚠️   No .env file found")

load_env()

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
import mimetypes
mimetypes.add_type('model/gltf-binary', '.glb')

# Stripe keys
STRIPE_PUBLIC_KEY = os.getenv("STRIPE_PUBLIC_KEY", "")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")

# ─── Gemini API helper ────────────────────────────────────────────────────────
# ── PASTE YOUR GEMINI KEY HERE ──────────────────────────────────────────────
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")  # loaded from .env automatically

def get_gemini_key():
    """Always read fresh key from .env."""
    load_env()
    return os.getenv("GEMINI_API_KEY", "")
# ─────────────────────────────────────────────────────────────────────────────

def call_gemini_ai(history, user_msg, system=""):
    """Call OpenRouter AI API - free credits."""
    load_env()
    key = os.getenv("GEMINI_API_KEY", "")
    if not key:
        return None, "DEMO_MODE"
    print(f"[AI] key={key[:12]}...")
    prompt = (system or "") + "\n\nUser: " + user_msg
    try:
        resp = http_requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": "Bearer " + key,
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:5000",
                "X-Title": "NexCart"
            },
            json={
                "model": "nvidia/nemotron-3-super-120b-a12b:free",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 500
            },
            timeout=30
        )
        print(f"[AI] status={resp.status_code}")
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"], None
        print(f"[AI] Error: {resp.text[:200]}")
        return None, f"API error {resp.status_code}"
    except Exception as e:
        print(f"[AI] Exception: {e}")
        return None, str(e)


# ─── Product catalog ──────────────────────────────────────────────────────────
# Load products from JSON file
import pathlib
_data_file = pathlib.Path(__file__).parent.parent / "data" / "products.json"
if _data_file.exists():
    with open(_data_file, encoding="utf-8") as _f:
        _raw = json.load(_f)
    PRODUCTS = []
    for _p in _raw:
        PRODUCTS.append({
            "id": _p.get("productId", _p.get("id", "")),
            "name": _p.get("name", ""),
            "category": _p.get("category", ""),
            "sub": _p.get("subcategory", _p.get("sub", "")),
            "price": _p.get("price", 0),
            "sale": _p.get("discountPrice", _p.get("sale", _p.get("price", 0))),
            "rating": _p.get("rating", 4.5),
            "reviews": _p.get("reviewCount", _p.get("reviews", 0)),
            "stock": _p.get("stock", 100),
            "desc": _p.get("description", _p.get("desc", "")),
            "tags": _p.get("tags", []),
            "hints": _p.get("embeddingHints", _p.get("hints", "")),
            "colors": _p.get("colors", []),
            "glb_url": _p.get("glb_url", ""),
            "image": _p.get("image", ""),

        })
else:
    PRODUCTS = []

PRODUCT_MAP = {p["id"]: p for p in PRODUCTS}

CATEGORY_INFO = {
    "Electronics":     {"icon": "💻", "color": "#6366f1"},
    "Fashion":         {"icon": "👟", "color": "#ec4899"},
    "Furniture":       {"icon": "🛋️", "color": "#f59e0b"},
    "Watches":         {"icon": "⌚", "color": "#10b981"},
    "Home Appliances": {"icon": "🏠", "color": "#3b82f6"},
    "Beauty":          {"icon": "✨", "color": "#a855f7"},
}

PRODUCT_EMOJIS = {
    "Laptops": "💻", "Smartphones": "📱", "Gaming Accessories": "🎮",
    "Shoes": "👟", "Living Room": "🛋️", "Lighting": "💡",
    "Luxury Watches": "⌚", "Smartwatches": "⌚", "Air Treatment": "💨",
    "Kitchen": "☕", "Skincare": "🧴", "Makeup": "💄", "Fragrance": "🌹",
    "Office": "🖥️", "Personal Transport": "🛹",
}

def get_emoji(product):
    return PRODUCT_EMOJIS.get(product["sub"], CATEGORY_INFO.get(product["category"], {}).get("icon", "📦"))

def search_products(query="", category=None, max_price=None, min_price=None, tags=None, limit=6):
    results = list(PRODUCTS)
    if category and category != "All":
        results = [p for p in results if p["category"] == category or p.get("sub") == category]
    if max_price:
        results = [p for p in results if p["sale"] <= float(max_price)]
    if min_price:
        results = [p for p in results if p["sale"] >= float(min_price)]
    if tags:
        results = [p for p in results if any(t.lower() in " ".join(p["tags"] + [p["hints"]]).lower() for t in tags)]

    if query:
        words = [w for w in query.lower().split() if len(w) > 2]
        def score(p):
            searchable = f"{p['name']} {p['desc']} {p['hints']} {' '.join(p['tags'])} {p['category']} {p.get('sub','')}".lower()
            return sum(3 if w in p["name"].lower() else (1 if w in searchable else 0) for w in words)
        scored = [(score(p), p) for p in results]
        results = [p for s, p in sorted(scored, key=lambda x: -x[0]) if s > 0]
        if not results:
            results = sorted(PRODUCTS, key=lambda p: p["rating"] * (p["reviews"] ** 0.5), reverse=True)[:limit]
    else:
        results.sort(key=lambda p: p["rating"] * (p["reviews"] ** 0.5), reverse=True)

    return results[:int(limit)]

# ─── Chatbot tools ────────────────────────────────────────────────────────────
TOOLS = [
    {
        "name": "search_products",
        "description": "Search the NexCart product catalog. Use for any product discovery request.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query":     {"type": "string"},
                "category":  {"type": "string", "description": "Electronics, Fashion, Furniture, Watches, Home Appliances, Beauty"},
                "max_price": {"type": "number"},
                "min_price": {"type": "number"},
                "tags":      {"type": "array", "items": {"type": "string"}},
                "limit":     {"type": "integer", "default": 5},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_recommendations",
        "description": "Get personalized product recommendations based on context or preferences.",
        "input_schema": {
            "type": "object",
            "properties": {
                "context": {"type": "string"},
                "budget":  {"type": "number"},
                "limit":   {"type": "integer", "default": 4},
            },
            "required": ["context"],
        },
    },
    {
        "name": "compare_products",
        "description": "Compare specific products by their IDs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_ids": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["product_ids"],
        },
    },
]

SYSTEM_PROMPT = """You are NexCart AI, a friendly shopping assistant for NexCart e-commerce.

CATALOG: 20 products — Electronics (Laptops P1001/P1002, Phones P1003/P1004, Gaming P1009-P1011, Transport P1020), Fashion (Shoes P1005/P1006), Furniture (Sofa P1007, Lamp P1008, Desk P1019), Watches (Luxury P1012, Smart P1013), Appliances (Air Purifier P1014, Coffee P1015), Beauty (Serum P1016, Lipstick P1017, Perfume P1018).

RULES:
- ALWAYS use tools for product queries
- Be warm, concise (under 100 words unless comparing)
- Use **bold** for product names, mention prices
- Active promos: Electronics 15% off, free shipping $75+
- All products have 3D viewer and AR preview"""

def run_tool(name, input_data):
    if name == "search_products":
        products = search_products(
            query=input_data.get("query", ""),
            category=input_data.get("category"),
            max_price=input_data.get("max_price"),
            min_price=input_data.get("min_price"),
            tags=input_data.get("tags", []),
            limit=min(input_data.get("limit", 5), 6),
        )
        return (
            f"Found {len(products)} products: " + json.dumps([{"id":p["id"],"name":p["name"],"price":p["sale"],"rating":p["rating"],"category":p["category"],"desc":p["desc"][:80]} for p in products]),
            products
        )
    elif name == "get_recommendations":
        products = search_products(
            query=input_data.get("context", ""),
            max_price=input_data.get("budget"),
            limit=input_data.get("limit", 4),
        )
        return f"Recommendations: " + json.dumps([{"id":p["id"],"name":p["name"],"price":p["sale"],"rating":p["rating"]} for p in products]), products
    elif name == "compare_products":
        products = [PRODUCT_MAP[pid] for pid in input_data.get("product_ids", []) if pid in PRODUCT_MAP]
        return f"Comparing {len(products)} products: " + json.dumps([{"id":p["id"],"name":p["name"],"price":p["sale"],"rating":p["rating"],"tags":p["tags"]} for p in products]), products
    return "Tool not found.", []

# ─── Routes ───────────────────────────────────────────────────────────────────
@app.route("/")
def home():
    featured = sorted(PRODUCTS, key=lambda p: p["rating"] * (p["reviews"] ** 0.5), reverse=True)[:8]
    categories = [{"name": k, **v, "count": sum(1 for p in PRODUCTS if p["category"] == k)} for k, v in CATEGORY_INFO.items()]
    return render_template("home.html",
        products=featured,
        categories=categories,
        category_info=CATEGORY_INFO,
        product_emojis=PRODUCT_EMOJIS,
        api_key=bool(GEMINI_KEY),
    )

@app.route("/catalog")
def catalog():
    category = request.args.get("category", "All")
    query = request.args.get("q", "")
    sort = request.args.get("sort", "featured")
    max_price = request.args.get("max_price")

    results = search_products(query=query, category=category if category != "All" else None, max_price=max_price, limit=20)

    if sort == "price_asc":
        results.sort(key=lambda p: p["sale"])
    elif sort == "price_desc":
        results.sort(key=lambda p: p["sale"], reverse=True)
    elif sort == "rating":
        results.sort(key=lambda p: p["rating"], reverse=True)

    categories = ["All"] + list(CATEGORY_INFO.keys())
    return render_template("catalog.html",
        products=results,
        categories=categories,
        active_category=category,
        query=query,
        category_info=CATEGORY_INFO,
        product_emojis=PRODUCT_EMOJIS,
        all_products_count=len(PRODUCTS),
    )

@app.route("/product/<product_id>")
def product_detail(product_id):
    product = PRODUCT_MAP.get(product_id)
    if not product:
        return render_template("404.html"), 404
    related = [p for p in PRODUCTS if p["category"] == product["category"] and p["id"] != product_id][:4]
    return render_template("product.html",
        product=product,
        related=related,
        category_info=CATEGORY_INFO,
        product_emojis=PRODUCT_EMOJIS,
        emoji=get_emoji(product),
        savings=product["price"] - product["sale"],
        discount=round((product["price"] - product["sale"]) / product["price"] * 100),
    )

# ─── API: Products ────────────────────────────────────────────────────────────
@app.route("/api/products")
def api_products():
    category = request.args.get("category")
    query    = request.args.get("q", "")
    max_p    = request.args.get("max_price")
    limit    = request.args.get("limit", 20)
    results  = search_products(query=query, category=category, max_price=max_p, limit=limit)
    return jsonify({"products": results, "total": len(results)})

@app.route("/api/products/<product_id>")
def api_product(product_id):
    p = PRODUCT_MAP.get(product_id)
    return jsonify(p) if p else (jsonify({"error": "Not found"}), 404)

# ─── API: Chatbot ─────────────────────────────────────────────────────────────
# In-memory session store (use Redis in production)
SESSIONS = {}

@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json()
    user_msg = data.get("message", "")
    session_id = data.get("session_id", "default")
    history = data.get("history", SESSIONS.get(session_id, []))

    if not user_msg:
        return jsonify({"error": "No message"}), 400

    new_history = history + [{"role": "user", "content": user_msg}]

    # Search products based on user message (always done)
    found_products = search_products(query=user_msg, limit=5)

    # If no Gemini key, return demo response
    if not GEMINI_KEY:
        demo_text = f"I found {len(found_products)} products matching your request! Here are my top picks. (Add GEMINI_API_KEY in .env for full AI responses)"
        SESSIONS[session_id] = new_history[-12:]
        return jsonify({"message": demo_text, "products": [compact(p) for p in found_products], "demo_mode": True})

    # Build product context for Gemini
    product_ctx = "\n".join([f"- {p['name']} (${p['sale']}, ★{p['rating']}): {p['desc'][:80]}" for p in found_products])
    gemini_system = SYSTEM_PROMPT + f"\n\nRELEVANT PRODUCTS FOUND:\n{product_ctx}\n\nMention these products naturally in your response with their prices."

    # Call Gemini
    past_history = history  # history before this message
    final_text, error = call_gemini_ai(past_history, user_msg, system=gemini_system)

    if error:
        print(f"[GEMINI ERROR] {error}")
        final_text = f"I found {len(found_products)} great options for you! (AI error: {error[:60]})"

    # Dedup products
    seen = set()
    unique = []
    for p in found_products:
        if p["id"] not in seen:
            seen.add(p["id"])
            unique.append(compact(p))

    # Save session
    new_history.append({"role": "assistant", "content": final_text or ""})
    SESSIONS[session_id] = new_history[-12:]

    return jsonify({
        "message": final_text or "Here are some great options for you!",
        "products": unique[:5],
    })

def compact(p):
    return {
        "id": p["id"], "name": p["name"], "category": p["category"], "sub": p.get("sub", ""),
        "price": p["price"], "sale": p["sale"], "rating": p["rating"],
        "reviews": p["reviews"], "emoji": get_emoji(p),
        "badge": "Sale" if p["sale"] < p["price"] else None,
        "discount": round((p["price"] - p["sale"]) / p["price"] * 100) if p["sale"] < p["price"] else 0,
    }

@app.route("/checkout")
def checkout():
    return render_template("checkout.html",stripe_public_key=os.getenv("STRIPE_PUBLIC_KEY",""))

@app.route("/order-success")
def order_success():
    from flask import render_template
    return render_template("order_success.html")

@app.route("/api/create-payment-intent",methods=["POST"])
def create_payment_intent():
    load_env()
    key=os.getenv("STRIPE_SECRET_KEY","")
    data=request.json
    amount=int(float(data.get("amount",0))*100)
    resp=http_requests.post("https://api.stripe.com/v1/payment_intents",auth=(key,""),data={"amount":amount,"currency":"usd","automatic_payment_methods[enabled]":"true"})
    return jsonify({"clientSecret":resp.json()["client_secret"]}) if resp.status_code==200 else jsonify({"error":resp.text}),400

@app.route("/api/health")
def health():
    return jsonify({
        "status": "healthy",
        "products": len(PRODUCTS),
        "ai_enabled": bool(GEMINI_KEY),
    })

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"\n{'='*55}")
    print(f"  🛒  NexCart is running!")
    print(f"{'='*55}")
    print(f"  👉  Open:  http://localhost:{port}")
    print(f"  🛍️  Shop:  http://localhost:{port}/catalog")
    print(f"  📦  API:   http://localhost:{port}/api/products")
    print(f"  🤖  Chat:  http://localhost:{port}/api/chat")
    if not GEMINI_KEY:
        print(f"\n  ⚠️   Add ANTHROPIC_API_KEY to .env for AI features")
    else:
        print(f"\n  ✅  AI chatbot active")
    print(f"{'='*55}\n")
    app.run(debug=True, port=port, host="0.0.0.0")
