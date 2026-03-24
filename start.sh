#!/bin/bash
# ─────────────────────────────────────────────────────────
#  NexCart — Start Script
#  Usage: ./start.sh
#  Or with API key: ANTHROPIC_API_KEY=sk-ant-... ./start.sh
# ─────────────────────────────────────────────────────────

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║       🛒  NexCart AI Shopping Platform              ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# Load .env if it exists
if [ -f ".env" ]; then
  echo "📄 Loading .env file..."
  export $(grep -v '^#' .env | xargs)
fi

# Check Python
if ! command -v python3 &> /dev/null; then
  echo "❌ Python3 not found. Please install Python 3.8+"
  exit 1
fi

# Check Flask
if ! python3 -c "import flask" 2>/dev/null; then
  echo "📦 Installing Flask..."
  pip3 install flask requests --break-system-packages -q
fi

# Check API key
if [ -z "$ANTHROPIC_API_KEY" ] || [ "$ANTHROPIC_API_KEY" = "your_anthropic_api_key_here" ]; then
  echo "⚠️  No ANTHROPIC_API_KEY set — running in demo mode"
  echo "   To enable AI: export ANTHROPIC_API_KEY=your_key_here"
  echo "   Get a key at: https://console.anthropic.com"
  echo ""
else
  echo "✅ Anthropic API key found — AI chatbot active!"
  echo ""
fi

echo "🚀 Starting NexCart on http://localhost:5000"
echo "   Press Ctrl+C to stop"
echo ""

cd "$(dirname "$0")/app"
python3 app.py
