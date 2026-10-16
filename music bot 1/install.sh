#!/bin/bash
echo "══════════════════════════════════════════════════════════════"
echo "  🔧 Installing SHADOW CHEATS MUSIC dependencies..."
echo "══════════════════════════════════════════════════════════════"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo ""
echo "══════════════════════════════════════════════════════════════"
echo "  ✅ All dependencies installed inside virtual env!"
echo "  Configure your token in config.json, then run bash run.sh"
echo "══════════════════════════════════════════════════════════════"
