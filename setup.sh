#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
#  APEX OMNI AGENT – One-Command Termux Deploy
#  কপি-পেস্ট করে Enter দিলেই সম্পূর্ণ সিস্টেম তৈরি হবে
# ============================================================

pkill -9 -f omni_agent 2>/dev/null || true
pkill -9 -f ollama 2>/dev/null || true
rm -rf ~/apex_omni 2>/dev/null || true
mkdir -p ~/apex_omni/{data,logs,models}

echo "[SETUP] Downloading APEX OMNI AGENT..."

# Try multiple download methods (curl may be broken on fresh Termux)
# Try main branch first, then PR branch
AGENT_URL_MAIN="https://raw.githubusercontent.com/alvie382218-debug/Turmux-/main/omni_agent.py"
AGENT_URL_DEV="https://raw.githubusercontent.com/alvie382218-debug/Turmux-/devin/1777240495-termux-setup-script/omni_agent.py"
AGENT_URL="$AGENT_URL_MAIN"

if command -v python &>/dev/null; then
    python -c "
import urllib.request, sys
try:
    urllib.request.urlretrieve('${AGENT_URL}', sys.argv[1])
    print('[SETUP] Downloaded via Python')
except Exception as e:
    print(f'[SETUP] Python download failed: {e}')
    sys.exit(1)
" ~/apex_omni/omni_agent.py 2>/dev/null && DONE=1
fi

if [ -z "$DONE" ] && command -v wget &>/dev/null; then
    wget -q -O ~/apex_omni/omni_agent.py "$AGENT_URL" && DONE=1 && echo "[SETUP] Downloaded via wget"
fi

if [ -z "$DONE" ] && command -v curl &>/dev/null; then
    curl -sL -o ~/apex_omni/omni_agent.py "$AGENT_URL" && DONE=1 && echo "[SETUP] Downloaded via curl"
fi

# If main branch failed, try dev branch
if [ -z "$DONE" ]; then
    echo "[SETUP] Trying dev branch..."
    AGENT_URL="$AGENT_URL_DEV"
    if command -v python &>/dev/null; then
        python -c "
import urllib.request, sys
try:
    urllib.request.urlretrieve('${AGENT_URL}', sys.argv[1])
    print('[SETUP] Downloaded via Python (dev)')
except: sys.exit(1)
" ~/apex_omni/omni_agent.py 2>/dev/null && DONE=1
    fi
    if [ -z "$DONE" ] && command -v wget &>/dev/null; then
        wget -q -O ~/apex_omni/omni_agent.py "$AGENT_URL" && DONE=1
    fi
fi

if [ -z "$DONE" ]; then
    echo "[ERROR] Download failed. Check internet or install python:"
    echo "  pkg install python"
    echo "Then run this script again."
    exit 1
fi

# Verify file was downloaded properly
if [ ! -s ~/apex_omni/omni_agent.py ]; then
    echo "[ERROR] Downloaded file is empty. Check internet connection."
    exit 1
fi

LINES=$(wc -l < ~/apex_omni/omni_agent.py)
if [ "$LINES" -lt 100 ]; then
    echo "[ERROR] Downloaded file is incomplete ($LINES lines). Check internet."
    exit 1
fi

echo "[SETUP] File OK ($LINES lines). Starting system..."
python ~/apex_omni/omni_agent.py
