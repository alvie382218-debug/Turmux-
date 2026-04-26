#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
#  APEX OMNI AGENT v22.1 — 47+ Features | Rich TUI | Offline AI | Web UI
#  সম্পূর্ণ ফিল্ড ইন্টেলিজেন্স ও AI কমান্ড সেন্টার
#  Full User-Friendliness Audit Applied
# =============================================================================
import os, sys, subprocess, time, json, uuid, sqlite3, threading, hashlib
import socket, base64, io, re, secrets, shutil, queue, math, logging, signal
from datetime import datetime
from pathlib import Path
from collections import deque

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
    except subprocess.TimeoutExpired:
        logging.warning(f"cmd timed out: {cmd}")
        return None
    except FileNotFoundError:
        logging.warning(f"cmd not found: {cmd}")
        return None
    except Exception as e:
        logging.warning(f"cmd failed: {cmd} – {e}")
        return None

def has_termux_api():
    r = run_cmd(["which", "termux-battery-status"], timeout=5)
    return r is not None and r.returncode == 0

def get_battery():
    try:
        out = subprocess.check_output(["termux-battery-status"], text=True, timeout=5)
        d = json.loads(out)
        return d.get("percentage", -1), d.get("status", "unknown")
    except Exception:
        return -1, "unknown"

# ======================== THREAD-SAFE DB ========================
_db_lock = threading.Lock()

def db_execute(query, params=(), fetch=False, fetchall=False):
    with _db_lock:
        try:
            conn = sqlite3.connect(str(DB_PATH))
            c = conn.cursor()
            c.execute(query, params)
            if fetchall:
                result = c.fetchall()
            elif fetch:
                result = c.fetchone()
            else:
                result = None
            conn.commit()
            conn.close()
            return result
        except Exception as e:
            logging.error(f"db_execute: {e}")
            return [] if fetchall else None

def db_execute_many(queries):
    with _db_lock:
        try:
            conn = sqlite3.connect(str(DB_PATH))
            c = conn.cursor()
            for q, p in queries:
                c.execute(q, p)
            conn.commit()
            conn.close()
        except Exception as e:
            logging.error(f"db_execute_many: {e}")

# ======================== BOOTSTRAP ========================
def bootstrap():
    total_steps = 6
    def step(n, msg_bn, msg_en):
        pct = int(n / total_steps * 100)
        bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
        print(f"\033[1;33m[{n}/{total_steps}] {bar} {pct}% — {msg_bn}\033[0m")
        print(f"       {msg_en}")

    print("\033[1;36m╔═══════════════════════════════════════════════════╗")
    print("║   APEX OMNI AGENT — বুটস্ট্র্যাপ / BOOTSTRAP     ║")
    print("╚═══════════════════════════════════════════════════╝\033[0m")
    print()

    step(1, "প্যাকেজ আপডেট করা হচ্ছে...", "Updating packages (fixes curl SSL)...")
    run_cmd(["apt", "update", "-y"], timeout=120)
    run_cmd(["apt", "full-upgrade", "-y"], timeout=300)
    print("  \033[1;32m✓ প্যাকেজ আপডেট সম্পন্ন\033[0m\n")

    step(2, "সিস্টেম প্যাকেজ ইনস্টল...", "Installing system packages...")
    pkgs = (
        "python python-pip python-pillow nmap netcat-openbsd git curl wget "
        "jq termux-api tshark tcpdump coreutils sqlite openssh "
        "openssl tar zip unzip figlet"
    ).split()
    installed = 0
    for p in pkgs:
        r = run_cmd(["pkg", "install", "-y", p])
        installed += 1
        if installed % 5 == 0:
            print(f"  ... {installed}/{len(pkgs)} প্যাকেজ")
    print(f"  \033[1;32m✓ {installed} প্যাকেজ ইনস্টল সম্পন্ন\033[0m\n")

    # PIL (optional)
    pil_ok = False
    try:
        from PIL import Image
        pil_ok = True
    except ImportError:
        run_cmd(["pkg", "install", "-y", "python-pillow"])
        try:
            from PIL import Image
            pil_ok = True
        except ImportError:
            os.environ["LDFLAGS"] = "-L/system/lib/"
            os.environ["CFLAGS"] = f"-I{PREFIX}/include/"
            run_cmd([sys.executable, "-m", "pip", "install", "--quiet", "pillow"])
            try:
                from PIL import Image
                pil_ok = True
            except ImportError:
                pass
    if pil_ok:
        print("  \033[1;32m✓ PIL/Pillow\033[0m")
    else:
        print("  \033[1;33m⚠ PIL নেই — QR কোড SVG মোডে কাজ করবে\033[0m")

    step(3, "Python মডিউল ইনস্টল...", "Installing Python modules...")
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
            print(f"  \033[1;33m⏳ {mod} ইনস্টল হচ্ছে...\033[0m")
            run_cmd([sys.executable, "-m", "pip", "install", "--quiet", mod])
    print()

    step(4, "Ollama AI ইঞ্জিন...", "Downloading Ollama AI engine...")
    if not OLLAMA_BIN.exists():
        try:
            import requests as _req
            url = "https://github.com/ollama/ollama/releases/download/v0.6.2/ollama-linux-arm64"
            print("  \033[1;33m⏳ ডাউনলোড হচ্ছে (এটি কিছু সময় নেবে)...\033[0m")
            r = _req.get(url, timeout=180, allow_redirects=True, stream=True)
            if r.status_code == 200:
                total = int(r.headers.get('content-length', 0))
                downloaded = 0
                with open(OLLAMA_BIN, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024*1024):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            pct = int(downloaded / total * 100)
                            print(f"\r  ডাউনলোড: {pct}% ({downloaded // (1024*1024)}MB)", end="", flush=True)
                print()
                OLLAMA_BIN.chmod(0o755)
                if OLLAMA_BIN.exists() and OLLAMA_BIN.stat().st_size > 10000:
                    print("  \033[1;32m✓ Ollama ডাউনলোড সম্পন্ন\033[0m")
                else:
                    OLLAMA_BIN.unlink(missing_ok=True)
                    print("  \033[1;31m✗ Ollama ফাইল ত্রুটিপূর্ণ\033[0m")
            else:
                print(f"  \033[1;31m✗ ডাউনলোড ব্যর্থ (HTTP {r.status_code})\033[0m")
        except Exception as e:
            print(f"  \033[1;31m✗ Ollama ডাউনলোড ব্যর্থ: {e}\033[0m")
    else:
        print("  \033[1;32m✓ Ollama ইতিমধ্যে আছে\033[0m")
    print()

    step(5, "AI মডেল শুরু করা হচ্ছে...", "Starting AI model (background)...")
    if OLLAMA_BIN.exists() and OLLAMA_BIN.stat().st_size > 10000:
        try:
            os.environ["OLLAMA_HOST"] = "127.0.0.1:11434"
            os.environ["OLLAMA_MODELS"] = str(MODELS_DIR)
            subprocess.Popen(
                [str(OLLAMA_BIN), "serve"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                env={**os.environ, "OLLAMA_HOST": "127.0.0.1:11434", "OLLAMA_MODELS": str(MODELS_DIR)}
            )
            time.sleep(5)
            threading.Thread(
                target=lambda: run_cmd([str(OLLAMA_BIN), "pull", MODEL_NAME], timeout=600),
                daemon=True
            ).start()
            print("  \033[1;32m✓ Ollama চালু, মডেল ব্যাকগ্রাউন্ডে ডাউনলোড হচ্ছে\033[0m")
        except Exception as e:
            print(f"  \033[1;31m✗ Ollama শুরু করতে ব্যর্থ: {e}\033[0m")
    else:
        print("  \033[1;33m⚠ Ollama পাওয়া যায়নি — AI পরে ইনস্টল করা যাবে\033[0m")
    print()

    step(6, "Wake lock সক্রিয়...", "Activating wake lock...")
    r = run_cmd(["termux-wake-lock"])
    if r and r.returncode == 0:
        print("  \033[1;32m✓ Wake lock সক্রিয়\033[0m")
    else:
        print("  \033[1;33m⚠ Wake lock ব্যর্থ — Termux:API ইনস্টল আছে?\033[0m")

    # Check Termux:API
    if not has_termux_api():
        print("\n  \033[1;33m⚠ সতর্কতা: Termux:API অ্যাপ পাওয়া যায়নি!\033[0m")
        print("  \033[1;33m  → F-Droid থেকে 'Termux:API' ইনস্টল করুন\033[0m")
        print("  \033[1;33m  → ক্যামেরা, GPS, SMS, ভয়েস কাজ করতে এটি দরকার\033[0m")

    print(f"\n\033[1;32m{'═'*50}")
    print("  বুটস্ট্র্যাপ সম্পন্ন! সিস্টেম চালু হচ্ছে...")
    print(f"{'═'*50}\033[0m\n")

bootstrap()

# ======================== IMPORTS (safe after bootstrap) ========================
from flask import Flask, request, jsonify, render_template_string, send_file, Response
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import qrcode
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
import requests as req
import urllib3
urllib3.disable_warnings()

def make_qr_png_bytes(data):
    if HAS_PIL:
        img = qrcode.make(data)
        buf = io.BytesIO()
        img.save(buf, "PNG")
        buf.seek(0)
        return buf.getvalue(), "image/png"
    else:
        import qrcode.image.svg
        factory = qrcode.image.svg.SvgPathImage
        img = qrcode.make(data, image_factory=factory)
        buf = io.BytesIO()
        img.save(buf)
        buf.seek(0)
        return buf.getvalue(), "image/svg+xml"

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
    db_execute_many([
        ("CREATE TABLE IF NOT EXISTS officers (id INTEGER PRIMARY KEY AUTOINCREMENT, device_id TEXT UNIQUE, name TEXT, ip TEXT, token TEXT, cloud_url TEXT, last_seen TEXT)", ()),
        ("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, event TEXT, ip TEXT, data TEXT, prev_hash TEXT, hash TEXT)", ()),
        ("CREATE TABLE IF NOT EXISTS arp_log (ts TEXT, mac TEXT, ip TEXT)", ()),
        ("CREATE TABLE IF NOT EXISTS system_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, level TEXT, message TEXT, source TEXT)", ()),
    ])

init_db()

# ======================== HASH-CHAIN AUDIT LOG ========================
def log_event(ev, ip, data):
    try:
        row = db_execute("SELECT hash FROM events ORDER BY id DESC LIMIT 1", fetch=True)
        prev = row[0] if row else "0" * 64
        ts = datetime.now().isoformat()
        raw = f"{ts}{ev}{ip}{data}{prev}"
        h = hashlib.sha256(raw.encode()).hexdigest()
        db_execute(
            "INSERT INTO events (ts,event,ip,data,prev_hash,hash) VALUES (?,?,?,?,?,?)",
            (ts, ev, ip, data, prev, h),
        )
    except Exception as e:
        logging.error(f"log_event: {e}")

log_event("OMNI_BOOT", "127.0.0.1", "v22.1 All Features")

# Thread-safe log deque (no race conditions)
_log_entries = deque(maxlen=200)
_log_lock = threading.Lock()

def log_msg(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    entry = f"[{ts}] {level}: {msg}"
    with _log_lock:
        _log_entries.append(entry)
    logging.info(msg)

def get_log_entries(n=50):
    with _log_lock:
        return list(_log_entries)[-n:]

log_msg("সিস্টেম চালু হয়েছে / System booted")

# ======================== NETWORK ========================
def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(3)
        s.connect(("8.8.8.8", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            if ip and ip != "127.0.0.1":
                return ip
        except Exception:
            pass
        # Try ip route
        try:
            r = subprocess.check_output("ip route get 1.1.1.1 2>/dev/null | head -1", shell=True, text=True, timeout=5)
            m = re.search(r'src (\d+\.\d+\.\d+\.\d+)', r)
            if m:
                return m.group(1)
        except Exception:
            pass
        return "127.0.0.1"

DIR_IP = get_ip()

_prev_cpu = {"idle": 0, "total": 0}

def cpu_ram():
    cpu = 0
    ram = 0
    try:
        with open("/proc/stat") as f:
            parts = f.readline().split()
            idle = float(parts[4])
            total = sum(float(x) for x in parts[1:])
            d_idle = idle - _prev_cpu["idle"]
            d_total = total - _prev_cpu["total"]
            _prev_cpu["idle"] = idle
            _prev_cpu["total"] = total
            if d_total > 0:
                cpu = round(100.0 * (1 - d_idle / d_total), 1)
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
OLLAMA_ENV = {
    **os.environ,
    "OLLAMA_HOST": "127.0.0.1:11434",
    "OLLAMA_MODELS": str(MODELS_DIR),
    "PATH": f"{PREFIX}/bin:{os.environ.get('PATH','')}",
}

def is_ollama_running():
    try:
        r = req.get("http://127.0.0.1:11434/api/tags", timeout=3)
        return r.status_code == 200
    except Exception:
        return False

def start_ollama():
    if not OLLAMA_BIN.exists():
        log_msg("Ollama binary পাওয়া যায়নি", "WARN")
        return False
    if is_ollama_running():
        log_msg("Ollama চলছে")
        return True
    try:
        subprocess.Popen(
            [str(OLLAMA_BIN), "serve"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            env=OLLAMA_ENV,
        )
    except Exception as e:
        log_msg(f"Ollama চালু করতে ব্যর্থ: {e}", "ERROR")
        return False
    for _ in range(15):
        time.sleep(2)
        if is_ollama_running():
            log_msg("Ollama সার্ভার চালু হয়েছে")
            return True
    log_msg("Ollama ৩০ সেকেন্ডে চালু হয়নি", "WARN")
    return False

def pull_model():
    if not OLLAMA_BIN.exists():
        return
    if not start_ollama():
        return
    try:
        r = req.get("http://127.0.0.1:11434/api/tags", timeout=5)
        if r.status_code == 200:
            models = [m.get("name","") for m in r.json().get("models",[])]
            if any(MODEL_NAME in m for m in models):
                log_msg(f"মডেল {MODEL_NAME} ইতিমধ্যে আছে")
                return
    except Exception:
        pass
    log_msg(f"মডেল {MODEL_NAME} ডাউনলোড হচ্ছে...")
    run_cmd([str(OLLAMA_BIN), "pull", MODEL_NAME], timeout=600)
    log_msg(f"মডেল {MODEL_NAME} ডাউনলোড সম্পন্ন")

def ai_generate(prompt):
    if not OLLAMA_BIN.exists():
        return "AI ইঞ্জিন ইনস্টল নেই। Settings থেকে Ollama ইনস্টল করুন।"
    if not is_ollama_running():
        started = start_ollama()
        if not started:
            return "AI অফলাইন — Ollama চালু হয়নি। কিছুক্ষণ পর আবার চেষ্টা করুন।"
    try:
        r = req.post(
            "http://127.0.0.1:11434/api/generate",
            json={"model": MODEL_NAME, "prompt": prompt, "stream": False},
            timeout=120,
        )
        if r.status_code == 200:
            resp = r.json().get("response", "")
            if resp:
                return resp.strip()
            return "AI খালি উত্তর দিয়েছে। মডেল এখনও লোড হচ্ছে, কিছুক্ষণ পর চেষ্টা করুন।"
        return f"AI ত্রুটি (HTTP {r.status_code})। মডেল এখনও ডাউনলোড হচ্ছে।"
    except req.exceptions.Timeout:
        return "AI উত্তর দিতে বেশি সময় নিচ্ছে। ছোট প্রশ্ন করুন।"
    except req.exceptions.ConnectionError:
        return "AI অফলাইন — Ollama সার্ভারে সংযোগ করতে পারছি না।"
    except Exception as e:
        return f"AI ত্রুটি: {e}"

threading.Thread(target=pull_model, daemon=True).start()

# ======================== SMS AUTH ========================
def get_alert_number():
    try:
        if ALERT_NUMBER_FILE.exists():
            n = ALERT_NUMBER_FILE.read_text().strip()
            if n:
                return n
    except Exception:
        pass
    return None

def is_authorized_sender(sender):
    alert_num = get_alert_number()
    if not alert_num:
        return False
    sender_clean = re.sub(r'[^\d+]', '', sender)
    alert_clean = re.sub(r'[^\d+]', '', alert_num)
    return sender_clean.endswith(alert_clean[-10:]) or alert_clean.endswith(sender_clean[-10:])

# ======================== BACKGROUND SURVEILLANCE ========================
def silent_capture():
    while True:
        try:
            if not get_alert_number():
                time.sleep(600)
                continue
            subprocess.run(
                ["termux-camera-photo", "-c", "0", str(DATA_DIR / "silent.jpg")],
                timeout=15, capture_output=True,
            )
            try:
                loc_out = subprocess.check_output(
                    ["termux-location"], text=True, timeout=20
                )
                with open(DATA_DIR / "gps.log", "a") as f:
                    f.write(f"{datetime.now().isoformat()}: {loc_out}\n")
            except Exception:
                pass

            if GEOFENCE_FILE.exists():
                try:
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
                            log_msg(f"জিওফেন্স ভঙ্গ! দূরত্ব={dist:.0f}m", "ALERT")
                            num = get_alert_number()
                            if num:
                                subprocess.run(
                                    ["termux-sms-send", "-n", num,
                                     f"GEOFENCE BREACH! Distance: {dist:.0f}m"],
                                    capture_output=True,
                                )
                except Exception:
                    pass
        except Exception:
            pass
        time.sleep(600)

def arp_monitor():
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
                        db_execute(
                            "INSERT INTO arp_log (ts,mac,ip) VALUES (?,?,?)",
                            (datetime.now().isoformat(), mac, ip_addr),
                        )
                        log_msg(f"নতুন ডিভাইস: {ip_addr} [{mac}]")
                        num = get_alert_number()
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

_processed_sms_ids = set()

def sms_poller():
    while True:
        try:
            out = subprocess.check_output(
                ["termux-sms-list", "-l", "5"], text=True, timeout=10
            )
            for sms in json.loads(out):
                body = sms.get("body", "")
                sms_id = sms.get("_id", "") or sms.get("threadid", "") or body
                if sms_id in _processed_sms_ids:
                    continue
                if body.startswith("!!"):
                    sender = sms.get("number", "")
                    if not is_authorized_sender(sender):
                        log_msg(f"অননুমোদিত SMS কমান্ড: {sender}", "WARN")
                        _processed_sms_ids.add(sms_id)
                        continue
                    cmd = body[2:].strip().upper()
                    _processed_sms_ids.add(sms_id)
                    log_event("SMS_CMD", sender, cmd)
                    log_msg(f"SMS কমান্ড: {cmd} — {sender}")
                    if cmd == "LOC":
                        try:
                            loc = subprocess.check_output(
                                ["termux-location"], text=True, timeout=15
                            )
                            subprocess.run(
                                ["termux-sms-send", "-n", sender, f"LOC:{loc}"],
                                capture_output=True,
                            )
                        except Exception:
                            pass
                    elif cmd == "PHOTO":
                        subprocess.run(
                            ["termux-camera-photo", "-c", "0",
                             str(DATA_DIR / "sms_cap.jpg")],
                            capture_output=True, timeout=15,
                        )
                    elif cmd == "WIPE":
                        log_event("PANIC_WIPE", "SMS", f"Remote wipe by {sender}")
                        db_execute_many([
                            ("DELETE FROM officers", ()),
                            ("DELETE FROM events", ()),
                            ("DELETE FROM arp_log", ()),
                        ])
                        init_db()
                        subprocess.run(
                            ["termux-sms-send", "-n", sender, "WIPE complete"],
                            capture_output=True,
                        )
                    elif cmd == "SCAN":
                        try:
                            subnet = ".".join(DIR_IP.split(".")[:3]) + ".0/24"
                            scan_out = subprocess.check_output(
                                ["nmap", "-sn", subnet], text=True, timeout=30
                            )
                            subprocess.run(
                                ["termux-sms-send", "-n", sender, scan_out[:160]],
                                capture_output=True,
                            )
                        except Exception:
                            pass
                    elif cmd == "PING":
                        subprocess.run(
                            ["termux-sms-send", "-n", sender, "PONG from APEX"],
                            capture_output=True,
                        )
                    elif cmd == "RECORD":
                        try:
                            subprocess.run(
                                ["termux-microphone-record", "-l", "10",
                                 "-f", str(DATA_DIR / "sms_rec.wav")],
                                capture_output=True, timeout=15,
                            )
                        except Exception:
                            pass
        except Exception:
            pass
        if len(_processed_sms_ids) > 1000:
            _processed_sms_ids.clear()
        time.sleep(15)

def self_healing():
    while True:
        try:
            if LOG_FILE.exists() and LOG_FILE.stat().st_size > 5_000_000:
                lines = LOG_FILE.read_text().splitlines()
                LOG_FILE.write_text("\n".join(lines[-5000:]) + "\n")
                log_msg("লগ রোটেশন সম্পন্ন")
        except Exception:
            pass
        time.sleep(300)

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
HOME=os.path.expanduser("~")
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
            cam_path=os.path.join(HOME,"cam.jpg")
            subprocess.run(["termux-camera-photo","-c","0",cam_path],capture_output=True,timeout=15)
            upload("camera",path=cam_path)
            loc=subprocess.check_output(["termux-location"],text=True,timeout=15)
            upload("location",data=loc)
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

# HTML entity escaping for XSS protection
def html_escape(s):
    return (str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;"))

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
    name = html_escape(request.args.get("name", "Officer"))
    cloud = request.args.get("cloud", "")
    if not cloud:
        return jsonify({"error": "Cloud URL দরকার"}), 400
    if not cloud.startswith("http"):
        return jsonify({"error": "সঠিক URL দিন (http:// বা https:// দিয়ে)"}), 400
    token = secrets.token_urlsafe(24)
    db_execute(
        "INSERT OR REPLACE INTO officers (device_id,name,ip,token,cloud_url,last_seen) VALUES (?,?,?,?,?,?)",
        (str(uuid.uuid4()), name, "0.0.0.0", token, cloud, datetime.now().isoformat()),
    )
    url = f"http://{DIR_IP}:8080/install?token={token}&cloud={cloud}"
    qr_bytes, _ = make_qr_png_bytes(url)
    log_event("DEPLOY", DIR_IP, name)
    log_msg(f"অফিসার deploy: {name}")
    return jsonify({"url": url, "qr": base64.b64encode(qr_bytes).decode()})

@app.route("/install")
def install_officer():
    t = request.args.get("token")
    c = request.args.get("cloud")
    if not t or not c:
        return "প্যারামিটার নেই", 400
    script = OFFICER_NODE.format(token=t, cloud=c)
    return Response(script, mimetype="text/x-python")

@app.route("/api/scan")
def scan():
    try:
        subnet = ".".join(DIR_IP.split(".")[:3]) + ".0/24"
        out = subprocess.check_output(
            ["nmap", "-sn", subnet], text=True, timeout=30
        )
        log_msg("Nmap স্ক্যান সম্পন্ন")
        return jsonify({"output": out})
    except FileNotFoundError:
        return jsonify({"error": "nmap ইনস্টল নেই। চালান: pkg install nmap"})
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
    except FileNotFoundError:
        return jsonify({"error": "bettercap ইনস্টল নেই এবং root প্রয়োজন।"})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/wipe", methods=["POST"])
def wipe():
    confirm = request.json.get("confirm", False) if request.is_json else False
    if not confirm:
        return jsonify({"error": "নিশ্চিত করুন", "need_confirm": True}), 400
    try:
        db_execute_many([
            ("DELETE FROM officers", ()),
            ("DELETE FROM events", ()),
            ("DELETE FROM arp_log", ()),
        ])
        log_event("PANIC_WIPE", "127.0.0.1", "Manual wipe")
        log_msg("প্যানিক ওয়াইপ সম্পন্ন", "ALERT")
        return jsonify({"output": "সব ডেটা মুছে ফেলা হয়েছে।"})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/officers")
def officers_list():
    rows = db_execute("SELECT name, ip, cloud_url, last_seen FROM officers ORDER BY id DESC LIMIT 20", fetchall=True) or []
    return jsonify([{"name": r[0], "ip": r[1], "cloud": r[2], "last": r[3]} for r in rows])

@app.route("/api/arp")
def arp_table():
    rows = db_execute("SELECT ts, mac, ip FROM arp_log ORDER BY ts DESC LIMIT 30", fetchall=True) or []
    return jsonify([{"ts": r[0], "mac": r[1], "ip": r[2]} for r in rows])

@app.route("/api/qr")
def qr_endpoint():
    qr_bytes, mime = make_qr_png_bytes(f"http://{DIR_IP}:8080")
    return Response(qr_bytes, mimetype=mime)

@app.route("/api/health")
def health():
    cpu, ram = cpu_ram()
    ai_running = is_ollama_running()
    if ai_running:
        ai_status = "online"
    elif OLLAMA_BIN.exists():
        ai_status = "starting"
    else:
        ai_status = "not_installed"
    batt_pct, batt_status = get_battery()
    return jsonify({
        "cpu": cpu, "ram": ram, "ai": ai_status, "ip": DIR_IP,
        "battery": batt_pct, "battery_status": batt_status,
        "termux_api": has_termux_api(),
    })

@app.route("/api/ai/restart")
def ai_restart():
    if not OLLAMA_BIN.exists():
        return jsonify({"status": "Ollama binary পাওয়া যায়নি"})
    run_cmd(["pkill", "-f", "ollama"], timeout=5)
    time.sleep(2)
    ok = start_ollama()
    if ok:
        threading.Thread(target=pull_model, daemon=True).start()
        return jsonify({"status": "Ollama রিস্টার্ট হয়েছে, মডেল ডাউনলোড হচ্ছে"})
    return jsonify({"status": "Ollama রিস্টার্ট ব্যর্থ"})

@app.route("/api/ai", methods=["POST"])
def ai_chat():
    data = request.json or {}
    prompt = data.get("prompt", "").strip()
    if not prompt:
        return jsonify({"reply": "কিছু লিখুন বা বলুন।"})
    if len(prompt) > 5000:
        return jsonify({"reply": "প্রশ্ন অনেক বড়। ছোট করে লিখুন।"})
    reply = ai_generate(prompt)
    log_msg(f"AI: {prompt[:50]}")
    return jsonify({"reply": reply})

@app.route("/api/voice", methods=["POST"])
def voice():
    if not has_termux_api():
        return jsonify({"text": "", "error": "Termux:API ইনস্টল নেই। F-Droid থেকে ইনস্টল করুন।"})
    try:
        out = subprocess.check_output(
            ["termux-speech-to-text"], timeout=30
        ).decode().strip()
        if not out or out.lower() in ("", "null", "none"):
            return jsonify({"text": "", "error": "কিছু শোনা যায়নি। আরেকটু জোরে বলুন।"})
        return jsonify({"text": out, "error": ""})
    except subprocess.TimeoutExpired:
        return jsonify({"text": "", "error": "ভয়েস টাইমআউট — ২০ সেকেন্ডের মধ্যে বলুন।"})
    except FileNotFoundError:
        return jsonify({"text": "", "error": "termux-speech-to-text পাওয়া যায়নি। Termux:API ইনস্টল করুন।"})
    except Exception as e:
        return jsonify({"text": "", "error": f"ভয়েস ত্রুটি: {e}"})

@app.route("/api/speak", methods=["POST"])
def speak():
    data = request.json or {}
    text = data.get("text", "").strip()
    if text:
        try:
            subprocess.Popen(
                ["termux-tts-speak", text], stderr=subprocess.DEVNULL
            )
        except FileNotFoundError:
            return jsonify({"status": "error", "msg": "Termux:API দরকার"})
    return jsonify({"status": "ok"})

@app.route("/api/record")
def record():
    try:
        rec_path = str(DATA_DIR / "rec.wav")
        subprocess.run(
            ["termux-microphone-record", "-l", "10", "-f", rec_path],
            timeout=15, capture_output=True,
        )
        time.sleep(1)
        subprocess.run(["termux-microphone-record", "-q"], timeout=5, capture_output=True)
        if Path(rec_path).exists():
            return send_file(rec_path, mimetype="audio/wav")
        return jsonify({"error": "রেকর্ডিং ফাইল তৈরি হয়নি"})
    except FileNotFoundError:
        return jsonify({"error": "Termux:API দরকার। F-Droid থেকে ইনস্টল করুন।"})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/camera")
def camera():
    if not has_termux_api():
        return jsonify({"error": "Termux:API দরকার। F-Droid থেকে ইনস্টল করুন।"})
    try:
        cam_path = str(DATA_DIR / "web_cap.jpg")
        subprocess.run(
            ["termux-camera-photo", "-c", "0", cam_path],
            timeout=15, capture_output=True,
        )
        if Path(cam_path).exists():
            return send_file(cam_path, mimetype="image/jpeg")
        return jsonify({"error": "ছবি তোলা যায়নি। ক্যামেরা পারমিশন দিন।"})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/gps")
def gps():
    if not has_termux_api():
        return jsonify({"error": "Termux:API দরকার। F-Droid থেকে ইনস্টল করুন।"})
    try:
        loc = subprocess.check_output(
            ["termux-location"], text=True, timeout=20
        )
        return jsonify(json.loads(loc))
    except subprocess.TimeoutExpired:
        return jsonify({"error": "GPS টাইমআউট — লোকেশন চালু আছে?"})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/config", methods=["POST"])
def config():
    data = request.json or {}
    if "alert_number" in data:
        num = data["alert_number"].strip()
        if num and not re.match(r'^\+?[\d\s\-]{7,15}$', num):
            return jsonify({"status": "error", "msg": "সঠিক ফোন নম্বর দিন (যেমন: +8801XXXXXXXXX)"}), 400
        ALERT_NUMBER_FILE.write_text(num)
    if "geofence" in data:
        geo = data["geofence"]
        lat = geo.get("lat")
        lon = geo.get("lon")
        if lat is not None and lon is not None:
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                return jsonify({"status": "error", "msg": "ভুল lat/lon মান"}), 400
        GEOFENCE_FILE.write_text(json.dumps(geo))
    log_msg("কনফিগ আপডেট হয়েছে")
    return jsonify({"status": "ok", "msg": "সেটিংস সেভ হয়েছে!"})

@app.route("/api/logs")
def logs_endpoint():
    items = get_log_entries(50)
    return jsonify(items)

@app.route("/api/audit")
def audit():
    rows = db_execute("SELECT ts, event, ip, data, hash FROM events ORDER BY id DESC LIMIT 50", fetchall=True) or []
    return jsonify([
        {"ts": r[0], "event": r[1], "ip": r[2], "data": r[3], "hash": r[4][:16] + "..."}
        for r in rows
    ])

# --- Tools install ---
TOOLS = {
    "metasploit": {"cmd": "cd ~ && git clone --depth 1 https://github.com/rapid7/metasploit-framework 2>&1 | tail -5", "name": "Metasploit", "size": "~500MB"},
    "sqlmap": {"cmd": "cd ~ && git clone --depth 1 https://github.com/sqlmapproject/sqlmap.git 2>&1 | tail -3", "name": "SQLMap", "size": "~20MB"},
    "hydra": {"cmd": "pkg install hydra -y 2>&1 | tail -3", "name": "Hydra", "size": "~5MB"},
    "aircrack": {"cmd": "pkg install aircrack-ng -y 2>&1 | tail -3", "name": "Aircrack-ng", "size": "~3MB"},
    "kali": {"cmd": "pkg install wget proot -y && wget -q https://raw.githubusercontent.com/EXALAB/AnLinux-Resources/master/Scripts/Installer/Kali/kali.sh && bash kali.sh 2>&1 | tail -5", "name": "Kali Linux", "size": "~1GB"},
    "wascan": {"cmd": "cd ~ && git clone --depth 1 https://github.com/m4ll0k/WAScan.git 2>&1 | tail -3", "name": "WAScan", "size": "~5MB"},
    "nikto": {"cmd": "cd ~ && git clone --depth 1 https://github.com/sullo/nikto.git 2>&1 | tail -3", "name": "Nikto", "size": "~10MB"},
    "theharvester": {"cmd": "cd ~ && git clone --depth 1 https://github.com/laramies/theHarvester.git 2>&1 | tail -3", "name": "theHarvester", "size": "~15MB"},
}

@app.route("/api/tools/install/<name>")
def install_tool(name):
    if name not in TOOLS:
        return jsonify({"error": "অজানা টুল"}), 400
    tool = TOOLS[name]
    try:
        out = subprocess.check_output(
            tool["cmd"], shell=True, text=True, timeout=300
        )
        log_msg(f"টুল ইনস্টল: {tool['name']}")
        return jsonify({"output": out.strip() or f"{tool['name']} ইনস্টল সম্পন্ন!"})
    except subprocess.TimeoutExpired:
        return jsonify({"error": f"{tool['name']} ইনস্টল টাইমআউট। আবার চেষ্টা করুন।"})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/tools/list")
def tools_list():
    return jsonify([{"id": k, "name": v["name"], "size": v["size"]} for k, v in TOOLS.items()])

# ======================== WEB UI (Glassmorphism + Bengali + XSS-safe) ========================
HTML_UI = r'''<!DOCTYPE html>
<html lang="bn">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#00f0ff">
<meta name="apple-mobile-web-app-capable" content="yes">
<title>APEX OMNI AGENT</title>
<style>
:root{--bg:#0b0f1a;--card:rgba(20,30,48,0.75);--accent:#00f0ff;--green:#00ff88;--text:#e0f0ff;--out:#080c16;--warn:#ff6b35;--danger:#e03030}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;padding:10px;min-height:100vh;-webkit-tap-highlight-color:transparent}
.header{text-align:center;padding:14px 0 8px;border-bottom:1px solid rgba(0,240,255,0.2);margin-bottom:12px}
.header h1{font-size:1.3em;color:var(--accent);text-shadow:0 0 20px rgba(0,240,255,0.3)}
.header p{font-size:.72em;color:#6080a0;margin-top:4px}
.conn-dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px;vertical-align:middle}
.conn-online{background:var(--green);box-shadow:0 0 6px var(--green)}
.conn-offline{background:var(--danger);box-shadow:0 0 6px var(--danger)}
.tabs{display:flex;gap:5px;margin-bottom:12px;overflow-x:auto;padding-bottom:4px;-webkit-overflow-scrolling:touch}
.tab{padding:9px 14px;background:var(--card);backdrop-filter:blur(12px);border-radius:12px;cursor:pointer;color:#8090b0;font-weight:600;white-space:nowrap;border:1px solid transparent;transition:.2s;font-size:.82em;user-select:none}
.tab:hover{border-color:rgba(0,240,255,0.3)}
.tab.active{background:var(--accent);color:#000;border-color:var(--accent)}
.view{display:none;animation:fadeIn .3s}.view.active{display:block}
@keyframes fadeIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin-bottom:12px}
@media(min-width:600px){.grid{grid-template-columns:repeat(4,1fr)}}
.card{background:var(--card);backdrop-filter:blur(14px);border:1px solid #1a2a40;border-radius:16px;padding:14px 8px;text-align:center;cursor:pointer;transition:.15s;font-size:.8em;user-select:none}
.card:active{transform:scale(0.95);border-color:var(--accent)}
.card .icon{font-size:1.6rem;margin-bottom:4px}
.output{background:var(--out);border:1px solid #1a2a40;border-radius:12px;padding:12px;min-height:80px;font-family:'Fira Code',monospace;color:var(--green);white-space:pre-wrap;font-size:.75rem;max-height:250px;overflow-y:auto;margin-top:8px;word-break:break-word}
.btn{background:var(--accent);border:none;padding:9px 18px;border-radius:16px;color:#000;font-weight:700;cursor:pointer;font-size:.82em;transition:.15s;user-select:none}
.btn:active{transform:scale(0.95)}
.btn:disabled{opacity:0.5;cursor:not-allowed}
.btn-danger{background:var(--danger);color:#fff}
.btn-warn{background:var(--warn);color:#000}
.btn-sm{padding:6px 12px;font-size:.75em}
input,textarea{width:100%;padding:10px 12px;margin:5px 0;border-radius:10px;border:1px solid #1a2a40;background:var(--out);color:#fff;font-size:.82em}
.status-bar{display:flex;gap:8px;justify-content:center;flex-wrap:wrap;margin:8px 0;font-size:.72em;color:#6080a0}
.status-bar span{background:var(--card);padding:5px 10px;border-radius:8px;white-space:nowrap}
.ai-online{color:var(--green)}
.ai-starting{color:var(--warn);animation:pulse 1.5s infinite}
.ai-offline{color:var(--danger)}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.5}}
.chat-box{height:250px;overflow-y:auto;padding:8px;scroll-behavior:smooth}
.chat-msg{margin:5px 0;padding:7px 11px;border-radius:10px;max-width:85%;font-size:.85em;line-height:1.4;word-break:break-word}
.chat-user{background:#1a2a40;margin-left:auto;text-align:right}
.chat-ai{background:#0a1a2a;border:1px solid #1a3050}
.chat-loading{color:#6080a0;font-style:italic}
.spinner{display:inline-block;width:14px;height:14px;border:2px solid var(--accent);border-top-color:transparent;border-radius:50%;animation:spin .8s linear infinite;vertical-align:middle;margin-right:6px}
@keyframes spin{to{transform:rotate(360deg)}}
#deployModal{display:none;position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.7);justify-content:center;align-items:center;z-index:100}
.modal-box{background:#101828;padding:20px;border-radius:18px;width:92%;max-width:400px;border:1px solid #1a2a40}
.toast{position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:var(--accent);color:#000;padding:10px 20px;border-radius:12px;font-weight:600;font-size:.82em;z-index:200;animation:fadeIn .3s}
.help-section{background:var(--card);border-radius:14px;padding:14px;margin-top:10px;font-size:.78em;line-height:1.6}
.help-section h4{color:var(--accent);margin-bottom:6px}
.settings-group{background:var(--card);border-radius:14px;padding:16px;margin-bottom:12px}
.settings-group h3{color:var(--accent);margin-bottom:10px;font-size:.95em}
.settings-group label{font-size:.78em;color:#6080a0;display:block;margin-top:8px}
.geo-inputs{display:flex;gap:6px;margin-top:4px}
.geo-inputs input{flex:1;min-width:0}
</style>
</head>
<body>

<div class="header">
  <h1>APEX OMNI AGENT</h1>
  <p><span class="conn-dot conn-offline" id="connDot"></span><span id="statusLine">সংযোগ হচ্ছে...</span></p>
</div>

<div class="status-bar" id="healthBar">
  <span id="hCpu">CPU: --</span>
  <span id="hRam">RAM: --</span>
  <span id="hBatt">ব্যাটারি: --</span>
  <span id="hAi">AI: --</span>
</div>

<div class="tabs" id="tabBar">
  <div class="tab active" data-tab="commando">কমান্ডো</div>
  <div class="tab" data-tab="ai">AI চ্যাট</div>
  <div class="tab" data-tab="tools">টুলস</div>
  <div class="tab" data-tab="network">নেটওয়ার্ক</div>
  <div class="tab" data-tab="logs">লগ</div>
  <div class="tab" data-tab="settings">সেটিংস</div>
</div>

<!-- COMMANDO -->
<div class="view active" id="view-commando">
  <div class="grid">
    <div class="card" onclick="openDeploy()"><div class="icon">🚀</div>অফিসার Deploy</div>
    <div class="card" onclick="runCmd('scan')"><div class="icon">📡</div>Nmap স্ক্যান</div>
    <div class="card" onclick="runCmd('bettercap')"><div class="icon">📶</div>Bettercap</div>
    <div class="card" onclick="confirmWipe()"><div class="icon">⚠️</div>প্যানিক ওয়াইপ</div>
    <div class="card" onclick="showOfficers()"><div class="icon">👥</div>অফিসার তালিকা</div>
    <div class="card" onclick="showARP()"><div class="icon">📋</div>ARP টেবিল</div>
    <div class="card" onclick="showQR()"><div class="icon">📷</div>QR কোড</div>
    <div class="card" onclick="recordAudio()"><div class="icon">🎤</div>রেকর্ড ১০সে.</div>
  </div>
  <div class="output" id="commandoOut">[ প্রস্তুত — একটি কমান্ড নির্বাচন করুন ]</div>
</div>

<!-- AI CHAT -->
<div class="view" id="view-ai">
  <div class="output chat-box" id="aiChatBox">
    <div class="chat-msg chat-ai">স্বাগতম! আমি AI সহকারী। আপনার প্রশ্ন লিখুন বা ভয়েস বোতাম ব্যবহার করুন।</div>
  </div>
  <div style="display:flex;gap:6px;margin-top:8px">
    <input id="aiPrompt" placeholder="প্রশ্ন লিখুন..." onkeypress="if(event.key==='Enter')askAI()"/>
    <button class="btn" onclick="askAI()" id="btnSend">পাঠান</button>
  </div>
  <div style="margin-top:6px;display:flex;gap:6px;flex-wrap:wrap">
    <button class="btn btn-sm" onclick="voiceInput()" id="btnVoice">🎤 ভয়েস</button>
    <button class="btn btn-sm" onclick="speakLast()">🔊 শোনান</button>
    <button class="btn btn-sm btn-warn" onclick="restartAI()">🔄 AI রিস্টার্ট</button>
    <button class="btn btn-sm" onclick="clearChat()">🗑 চ্যাট মুছুন</button>
  </div>
  <div class="output" id="aiStatus" style="min-height:24px;margin-top:6px;font-size:.72em;color:#6080a0"></div>
</div>

<!-- TOOLS -->
<div class="view" id="view-tools">
  <div class="grid">
    <div class="card" onclick="installTool('metasploit')"><div class="icon">💀</div>Metasploit<div style="font-size:.65em;color:#6080a0">~500MB</div></div>
    <div class="card" onclick="installTool('sqlmap')"><div class="icon">💉</div>SQLMap<div style="font-size:.65em;color:#6080a0">~20MB</div></div>
    <div class="card" onclick="installTool('hydra')"><div class="icon">🔑</div>Hydra<div style="font-size:.65em;color:#6080a0">~5MB</div></div>
    <div class="card" onclick="installTool('aircrack')"><div class="icon">📻</div>Aircrack<div style="font-size:.65em;color:#6080a0">~3MB</div></div>
    <div class="card" onclick="installTool('kali')"><div class="icon">🐉</div>Kali Linux<div style="font-size:.65em;color:#6080a0">~1GB</div></div>
    <div class="card" onclick="installTool('wascan')"><div class="icon">🌐</div>WAScan<div style="font-size:.65em;color:#6080a0">~5MB</div></div>
    <div class="card" onclick="installTool('nikto')"><div class="icon">🔍</div>Nikto<div style="font-size:.65em;color:#6080a0">~10MB</div></div>
    <div class="card" onclick="installTool('theharvester')"><div class="icon">🌾</div>theHarvester<div style="font-size:.65em;color:#6080a0">~15MB</div></div>
  </div>
  <div class="output" id="toolOut">একটি টুল নির্বাচন করুন ইনস্টল করতে</div>
</div>

<!-- NETWORK -->
<div class="view" id="view-network">
  <div class="grid">
    <div class="card" onclick="getCamera()"><div class="icon">📸</div>ক্যামেরা</div>
    <div class="card" onclick="getGPS()"><div class="icon">📍</div>GPS লোকেশন</div>
  </div>
  <div class="output" id="netOut">ক্যামেরা বা GPS নির্বাচন করুন</div>
</div>

<!-- LOGS -->
<div class="view" id="view-logs">
  <div style="display:flex;gap:6px;margin-bottom:8px">
    <button class="btn btn-sm" onclick="refreshLogs()">রিফ্রেশ</button>
    <button class="btn btn-sm" onclick="showAudit()">অডিট চেইন</button>
  </div>
  <div class="output" id="logsOut" style="height:300px">লগ লোড হচ্ছে...</div>
</div>

<!-- SETTINGS -->
<div class="view" id="view-settings">
  <div class="settings-group">
    <h3>এলার্ট সেটিংস</h3>
    <label>SMS এলার্ট নম্বর</label>
    <input id="alertNumber" placeholder="+8801XXXXXXXXX"/>
    <label>জিওফেন্স (নির্ধারিত এলাকা)</label>
    <div class="geo-inputs">
      <input id="geoLat" placeholder="Latitude" type="number" step="any"/>
      <input id="geoLon" placeholder="Longitude" type="number" step="any"/>
      <input id="geoRad" placeholder="Radius (m)" type="number" min="10"/>
    </div>
    <br>
    <button class="btn" onclick="saveConfig()" id="btnSave">সেটিংস সেভ করুন</button>
    <div id="configMsg" style="margin-top:8px;font-size:.78em"></div>
  </div>

  <div class="help-section">
    <h4>সাহায্য ও তথ্য</h4>
    <p><b>SMS কমান্ড:</b> অন্য ফোন থেকে এই নম্বরে SMS পাঠান:</p>
    <p>• <code>!!LOC</code> — বর্তমান লোকেশন পাবেন</p>
    <p>• <code>!!PHOTO</code> — গোপনে ছবি তুলবে</p>
    <p>• <code>!!WIPE</code> — সব ডেটা মুছে ফেলবে</p>
    <p>• <code>!!SCAN</code> — নেটওয়ার্ক স্ক্যান করবে</p>
    <p>• <code>!!PING</code> — ফোন চালু আছে কিনা জানাবে</p>
    <p>• <code>!!RECORD</code> — ১০সে. অডিও রেকর্ড করবে</p>
    <br>
    <p><b>নিরাপত্তা:</b> শুধুমাত্র উপরে সেট করা নম্বর থেকে SMS কমান্ড কাজ করবে।</p>
    <br>
    <p><b>Termux:API:</b> ক্যামেরা, GPS, SMS, ভয়েস ব্যবহার করতে F-Droid থেকে <b>Termux:API</b> অ্যাপ ইনস্টল করুন।</p>
    <br>
    <p><b>QR কোড:</b> একই WiFi নেটওয়ার্কে থাকলে QR স্ক্যান করে অন্য ডিভাইস থেকে ঢুকতে পারবেন।</p>
  </div>
</div>

<!-- Deploy Modal -->
<div id="deployModal" onclick="if(event.target===this)this.style.display='none'">
  <div class="modal-box">
    <h3 style="color:var(--accent);margin-bottom:10px">অফিসার Deploy</h3>
    <input id="ofName" placeholder="অফিসারের নাম"/>
    <input id="cloudUrl" placeholder="Webhook/Cloud URL (https://...)"/>
    <button class="btn" onclick="doDeploy()">QR ও লিংক তৈরি করুন</button>
    <div id="deployResult" style="margin-top:10px"></div>
    <br><button class="btn btn-sm" onclick="document.getElementById('deployModal').style.display='none'">বন্ধ করুন</button>
  </div>
</div>

<div id="toast" class="toast" style="display:none"></div>

<script src="https://cdn.socket.io/4.5.0/socket.io.min.js"></script>
<script>
const socket = io();
let lastAIReply = '';
let isConnected = false;

// XSS-safe text insertion
function esc(s){let d=document.createElement('div');d.textContent=s;return d.innerHTML;}

// Toast notification
function toast(msg,ms){
  let t=document.getElementById('toast');
  t.textContent=msg;t.style.display='block';
  setTimeout(()=>t.style.display='none',ms||3000);
}

// Tab switching (event delegation, no event.target bug)
document.getElementById('tabBar').addEventListener('click',function(e){
  let tab=e.target.closest('.tab');
  if(!tab)return;
  let t=tab.dataset.tab;
  document.querySelectorAll('.tab').forEach(e=>e.classList.remove('active'));
  tab.classList.add('active');
  document.querySelectorAll('.view').forEach(v=>v.classList.remove('active'));
  document.getElementById('view-'+t).classList.add('active');
});

// Connection status
socket.on('connect',()=>{
  isConnected=true;
  document.getElementById('connDot').className='conn-dot conn-online';
});
socket.on('disconnect',()=>{
  isConnected=false;
  document.getElementById('connDot').className='conn-dot conn-offline';
  document.getElementById('statusLine').textContent='সংযোগ বিচ্ছিন্ন — পুনরায় সংযোগ হচ্ছে...';
});

// Health bar auto-update
async function updateHealth(){
  try{
    let r=await fetch('/api/health');let d=await r.json();
    document.getElementById('hCpu').innerText='CPU: '+d.cpu+'%';
    document.getElementById('hRam').innerText='RAM: '+d.ram+'%';
    let aiEl=document.getElementById('hAi');
    if(d.ai==='online'){aiEl.innerHTML='AI: <span class="ai-online">চালু</span>';}
    else if(d.ai==='starting'){aiEl.innerHTML='AI: <span class="ai-starting">চালু হচ্ছে...</span>';}
    else{aiEl.innerHTML='AI: <span class="ai-offline">বন্ধ</span>';}
    if(d.battery>=0){
      let bIcon=d.battery>80?'🔋':d.battery>20?'🔋':'🪫';
      document.getElementById('hBatt').innerText=bIcon+' '+d.battery+'%';
    }
    document.getElementById('statusLine').innerText='IP: '+d.ip+' | Port: 8080 | পাসওয়ার্ড লাগবে না';
    document.getElementById('connDot').className='conn-dot conn-online';
  }catch(e){
    document.getElementById('connDot').className='conn-dot conn-offline';
  }
}
updateHealth(); setInterval(updateHealth, 5000);

// Commando
function openDeploy(){document.getElementById('deployModal').style.display='flex';}
async function doDeploy(){
  let n=document.getElementById('ofName').value,c=document.getElementById('cloudUrl').value;
  if(!n||!c)return toast('দুটি ফিল্ডই পূরণ করুন');
  let r=await fetch('/api/deploy?name='+encodeURIComponent(n)+'&cloud='+encodeURIComponent(c));
  let d=await r.json();
  if(d.error){toast(d.error);return;}
  document.getElementById('deployResult').innerHTML=
    '<p style="word-break:break-all"><a href="'+esc(d.url)+'" style="color:#00f0ff">'+esc(d.url)+'</a></p>'+
    '<img src="data:image/png;base64,'+d.qr+'" style="width:180px;margin-top:8px;border-radius:10px">';
}

async function runCmd(cmd){
  let out=document.getElementById('commandoOut');
  out.innerHTML='<span class="spinner"></span> চলছে...';
  try{
    let r=await fetch('/api/'+cmd);let d=await r.json();
    out.textContent=d.output||d.error||'সম্পন্ন';
  }catch(e){out.textContent='ত্রুটি: সার্ভারে সংযোগ করতে পারছি না';}
}

function confirmWipe(){
  if(confirm('⚠️ সতর্কতা!\n\nসব ডেটা স্থায়ীভাবে মুছে যাবে!\nআপনি কি নিশ্চিত?')){
    if(confirm('🔴 শেষ সুযোগ!\nএই কাজ undo করা যাবে না। আবারও নিশ্চিত করুন।')){
      doWipe();
    }
  }
}

async function doWipe(){
  let out=document.getElementById('commandoOut');
  out.innerHTML='<span class="spinner"></span> ডেটা মুছে ফেলা হচ্ছে...';
  try{
    let r=await fetch('/api/wipe',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({confirm:true})});
    let d=await r.json();
    out.textContent=d.output||d.error;
    toast('ওয়াইপ সম্পন্ন');
  }catch(e){out.textContent='ত্রুটি: '+e;}
}

async function showOfficers(){
  let out=document.getElementById('commandoOut');
  out.innerHTML='<span class="spinner"></span> লোড হচ্ছে...';
  let r=await fetch('/api/officers');let d=await r.json();
  let t='';d.forEach(o=>t+=esc(o.name)+' ('+esc(o.ip)+') — '+esc(o.last)+'\n');
  out.textContent=t||'কোন অফিসার নেই';
}

async function showARP(){
  let out=document.getElementById('commandoOut');
  out.innerHTML='<span class="spinner"></span> লোড হচ্ছে...';
  let r=await fetch('/api/arp');let d=await r.json();
  let t='';d.forEach(e=>t+=esc(e.ts)+' '+esc(e.mac)+' '+esc(e.ip)+'\n');
  out.textContent=t||'কোন ARP ডেটা নেই';
}

function showQR(){
  document.getElementById('commandoOut').innerHTML='<img src="/api/qr?t='+Date.now()+'" style="width:200px;border-radius:12px"><p style="margin-top:8px;font-size:.8em;color:#6080a0">একই WiFi তে অন্য ডিভাইস থেকে স্ক্যান করুন</p>';
}

async function recordAudio(){
  let out=document.getElementById('commandoOut');
  out.innerHTML='<span class="spinner"></span> রেকর্ডিং (১০ সেকেন্ড)...';
  try{
    let r=await fetch('/api/record');
    if(r.headers.get('content-type')?.includes('audio')){
      let blob=await r.blob();
      out.innerHTML='<audio controls src="'+URL.createObjectURL(blob)+'" style="width:100%"></audio>';
    }else{
      let d=await r.json();
      out.textContent=d.error||'রেকর্ডিং ব্যর্থ';
    }
  }catch(e){out.textContent='ত্রুটি: '+e;}
}

// AI Chat
async function askAI(){
  let inp=document.getElementById('aiPrompt');
  let p=inp.value.trim();if(!p)return;
  let box=document.getElementById('aiChatBox');
  let userDiv=document.createElement('div');
  userDiv.className='chat-msg chat-user';
  userDiv.textContent=p;
  box.appendChild(userDiv);
  let loadDiv=document.createElement('div');
  loadDiv.className='chat-msg chat-ai chat-loading';
  loadDiv.innerHTML='<span class="spinner"></span> চিন্তা করছে...';
  box.appendChild(loadDiv);
  box.scrollTop=box.scrollHeight;
  inp.value='';
  document.getElementById('btnSend').disabled=true;
  try{
    let r=await fetch('/api/ai',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:p})});
    let d=await r.json();
    lastAIReply=d.reply;
    loadDiv.className='chat-msg chat-ai';
    loadDiv.textContent=d.reply;
  }catch(e){
    loadDiv.className='chat-msg chat-ai';
    loadDiv.textContent='ত্রুটি: সার্ভারে সংযোগ করতে পারছি না';
  }
  document.getElementById('btnSend').disabled=false;
  box.scrollTop=box.scrollHeight;
}

async function voiceInput(){
  let btn=document.getElementById('btnVoice');
  btn.disabled=true;btn.textContent='🎤 শুনছি...';
  let box=document.getElementById('aiChatBox');
  try{
    let r=await fetch('/api/voice',{method:'POST'});
    let d=await r.json();
    if(d.text && d.text.trim()){
      document.getElementById('aiPrompt').value=d.text;
      askAI();
    }else if(d.error){
      let errDiv=document.createElement('div');
      errDiv.className='chat-msg chat-ai';
      errDiv.style.color='var(--warn)';
      errDiv.textContent=d.error;
      box.appendChild(errDiv);
      box.scrollTop=box.scrollHeight;
    }
  }catch(e){toast('ভয়েস ত্রুটি');}
  btn.disabled=false;btn.textContent='🎤 ভয়েস';
}

function speakLast(){
  if(lastAIReply)fetch('/api/speak',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:lastAIReply})});
  else toast('আগে AI কে কিছু জিজ্ঞেস করুন');
}

async function restartAI(){
  document.getElementById('aiStatus').innerHTML='<span class="spinner"></span> Ollama AI রিস্টার্ট হচ্ছে...';
  try{
    let r=await fetch('/api/ai/restart');let d=await r.json();
    document.getElementById('aiStatus').textContent=d.status;
  }catch(e){document.getElementById('aiStatus').textContent='ত্রুটি: '+e;}
}

function clearChat(){
  document.getElementById('aiChatBox').innerHTML='<div class="chat-msg chat-ai">চ্যাট পরিষ্কার করা হয়েছে। নতুন প্রশ্ন করুন!</div>';
  lastAIReply='';
}

// Tools
async function installTool(n){
  let out=document.getElementById('toolOut');
  out.innerHTML='<span class="spinner"></span> '+esc(n)+' ইনস্টল হচ্ছে... (কিছু সময় লাগবে)';
  try{
    let r=await fetch('/api/tools/install/'+n);let d=await r.json();
    out.textContent=d.output||d.error;
  }catch(e){out.textContent='ত্রুটি: '+e;}
}

// Network
async function getCamera(){
  let out=document.getElementById('netOut');
  out.innerHTML='<span class="spinner"></span> ক্যামেরা থেকে ছবি নেওয়া হচ্ছে...';
  try{
    let r=await fetch('/api/camera?t='+Date.now());
    if(r.headers.get('content-type')?.includes('image')){
      let blob=await r.blob();
      out.innerHTML='<img src="'+URL.createObjectURL(blob)+'" style="max-width:100%;border-radius:12px">';
    }else{
      let d=await r.json();
      out.textContent=d.error||'ছবি নেওয়া যায়নি';
    }
  }catch(e){out.textContent='ত্রুটি: '+e;}
}
async function getGPS(){
  let out=document.getElementById('netOut');
  out.innerHTML='<span class="spinner"></span> GPS লোকেশন নেওয়া হচ্ছে...';
  try{
    let r=await fetch('/api/gps');let d=await r.json();
    if(d.error){out.textContent=d.error;}
    else{
      let t='লোকেশন তথ্য:\n';
      t+='Latitude: '+(d.latitude||'N/A')+'\n';
      t+='Longitude: '+(d.longitude||'N/A')+'\n';
      t+='Accuracy: '+(d.accuracy||'N/A')+'m\n';
      t+='Provider: '+(d.provider||'N/A');
      out.textContent=t;
    }
  }catch(e){out.textContent='ত্রুটি: '+e;}
}

// Logs
async function refreshLogs(){
  let out=document.getElementById('logsOut');
  out.innerHTML='<span class="spinner"></span> লোড হচ্ছে...';
  try{
    let r=await fetch('/api/logs');let d=await r.json();
    out.textContent=d.join('\n')||'কোন লগ নেই';
  }catch(e){out.textContent='ত্রুটি: '+e;}
}
async function showAudit(){
  let out=document.getElementById('logsOut');
  out.innerHTML='<span class="spinner"></span> অডিট চেইন লোড হচ্ছে...';
  try{
    let r=await fetch('/api/audit');let d=await r.json();
    let t='';d.forEach(e=>t+=esc(e.ts)+' ['+esc(e.event)+'] '+esc(e.data)+' #'+esc(e.hash)+'\n');
    out.textContent=t||'কোন অডিট এন্ট্রি নেই';
  }catch(e){out.textContent='ত্রুটি: '+e;}
}

// Settings
async function saveConfig(){
  let btn=document.getElementById('btnSave');
  btn.disabled=true;btn.textContent='সেভ হচ্ছে...';
  let num=document.getElementById('alertNumber').value;
  let lat=parseFloat(document.getElementById('geoLat').value);
  let lon=parseFloat(document.getElementById('geoLon').value);
  let rad=parseFloat(document.getElementById('geoRad').value)||100;
  let body={alert_number:num};
  if(!isNaN(lat)&&!isNaN(lon))body.geofence={lat:lat,lon:lon,radius:rad};
  try{
    let r=await fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    let d=await r.json();
    let msg=document.getElementById('configMsg');
    if(d.status==='ok'){
      msg.style.color='var(--green)';msg.textContent=d.msg||'সেভ হয়েছে!';
      toast('সেটিংস সেভ হয়েছে!');
    }else{
      msg.style.color='var(--danger)';msg.textContent=d.msg||'ত্রুটি!';
    }
  }catch(e){toast('সেভ ব্যর্থ');}
  btn.disabled=false;btn.textContent='সেটিংস সেভ করুন';
}

// Socket events
socket.on('new_device',d=>{
  let out=document.getElementById('commandoOut');
  out.textContent+='[নতুন] '+esc(d.ip)+' '+esc(d.mac)+'\n';
  toast('নতুন ডিভাইস: '+d.ip);
});

// Auto-refresh logs when visible
setInterval(()=>{
  if(document.getElementById('view-logs').classList.contains('active')){refreshLogs();}
},10000);
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

    layout["header"].update(
        Panel(
            Text("APEX OMNI AGENT v22.1", style="bold cyan", justify="center"),
            border_style="cyan",
        )
    )

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

    cpu, ram = cpu_ram()
    batt_pct, batt_status = get_battery()
    stats_table = Table(expand=True, box=box.SIMPLE)
    stats_table.add_column("Item", style="cyan", width=14)
    stats_table.add_column("Value", style="white")
    stats_table.add_row("CPU", f"{cpu}%")
    stats_table.add_row("RAM", f"{ram}%")
    if batt_pct >= 0:
        batt_color = "green" if batt_pct > 50 else ("yellow" if batt_pct > 20 else "red")
        stats_table.add_row("Battery", f"[{batt_color}]{batt_pct}% ({batt_status})[/]")
    ai_state = is_ollama_running()
    if ai_state:
        stats_table.add_row("AI", "[green]Online[/]")
    elif OLLAMA_BIN.exists():
        stats_table.add_row("AI", "[yellow]Starting...[/]")
    else:
        stats_table.add_row("AI", "[red]N/A[/]")
    stats_table.add_row("Web", f"http://{DIR_IP}:8080")
    stats_table.add_row("Password", "[green]Not required[/]")
    stats_table.add_row("Officers", str(get_officer_count()))
    top_layout["stats"].update(
        Panel(stats_table, title="[bold green]System[/]", border_style="green")
    )

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
                line += "\u2588"
            elif top_cell:
                line += "\u2580"
            elif bot_cell:
                line += "\u2584"
            else:
                line += " "
        qr_lines.append(line)
    qr_text = "\n".join(qr_lines) + f"\n\n{url}"
    top_layout["qr"].update(
        Panel(
            Text(qr_text, style="white on black", justify="center"),
            title="[bold cyan]QR Scan / URL[/]",
            subtitle=f"[dim]{url}[/]",
            border_style="cyan",
        )
    )

    body_layout["top"].update(top_layout)

    log_items = get_log_entries(15)
    logs_text = "\n".join(log_items) if log_items else "Waiting for events..."
    body_layout["bottom"].update(
        Panel(
            Text(logs_text, style="green"),
            title="[bold magenta]Live Activity[/]",
            border_style="magenta",
        )
    )

    layout["body"].update(body_layout)

    layout["footer"].update(
        Panel(
            Text(
                f"Browser: http://{DIR_IP}:8080 | SMS: !!LOC !!PHOTO !!WIPE !!SCAN !!PING !!RECORD",
                style="yellow",
                justify="center",
            ),
            border_style="red",
        )
    )

    return layout

def get_officer_count():
    row = db_execute("SELECT COUNT(*) FROM officers", fetch=True)
    return row[0] if row else 0

def tui_thread():
    time.sleep(2)
    try:
        with Live(build_tui(), refresh_per_second=1, screen=True) as live:
            while True:
                live.update(build_tui())
                time.sleep(2)
    except Exception as e:
        print(f"\n[TUI] Stopped: {e}. Flask continues at http://{DIR_IP}:8080")

# ======================== MAIN ========================
if __name__ == "__main__":
    run_cmd(["termux-wake-lock"])

    print(f"\033[1;36m")
    print(f"  ╔══════════════════════════════════════════════════════╗")
    print(f"  ║     APEX OMNI AGENT v22.1 চালু হয়েছে!              ║")
    print(f"  ║     Web: http://{DIR_IP}:8080{' '*(34-len(DIR_IP))}║")
    print(f"  ║     পাসওয়ার্ড: লাগবে না                              ║")
    print(f"  ║     QR: একই WiFi তে অন্য ডিভাইস দিয়ে ব্রাউজারে      ║")
    print(f"  ║          http://{DIR_IP}:8080 খুলুন{' '*(22-len(DIR_IP))}║")
    print(f"  ╚══════════════════════════════════════════════════════╝")
    print(f"\033[0m")

    def signal_handler(sig, frame):
        print("\n\033[1;33mসিস্টেম বন্ধ হচ্ছে...\033[0m")
        run_cmd(["termux-wake-unlock"])
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    threading.Thread(target=tui_thread, daemon=True).start()

    socketio.run(app, host="0.0.0.0", port=8080, debug=False, use_reloader=False)
