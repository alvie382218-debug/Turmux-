# APEX OMNI AGENT v22.0

> **সম্পূর্ণ ফিল্ড ইন্টেলিজেন্স ও AI কমান্ড সেন্টার — Termux এ একটি কমান্ডে**

---

## 🚀 ইনস্টল / Install

Termux অ্যাপ খুলুন এবং নিচের **যেকোনো একটি** কমান্ড কপি-পেস্ট করে **Enter** দিন:

**Option 1 — সরাসরি (curl):**
```bash
curl -sL https://raw.githubusercontent.com/alvie382218-debug/Turmux-/main/setup.sh | bash
```

**Option 2 — Git clone:**
```bash
pkg install -y git && git clone https://github.com/alvie382218-debug/Turmux-.git && bash Turmux-/setup.sh
```

সেটআপ স্বয়ংক্রিয়ভাবে সব প্যাকেজ ইন্সটল করবে, তারপর সিস্টেম চালু হবে।

---

## 📋 47+ ফিচার তালিকা / Feature List

### Core Infrastructure
| # | Feature | Status |
|---|---------|--------|
| 1 | Zero-touch bootstrap (এক কমান্ডে সব ইন্সটল) | ✅ |
| 2 | Wake-lock (স্ক্রীন বন্ধ হলেও চলবে) | ✅ |
| 3 | Auto-start | ✅ |
| 4 | Process cleanup | ✅ |
| 5 | Self-healing (ক্র্যাশ থেকে পুনরুদ্ধার) | ✅ |
| 6 | Log rotation (লগ ফাইল ম্যানেজমেন্ট) | ✅ |

### Web UI
| # | Feature | Status |
|---|---------|--------|
| 7 | Glassmorphism UI (ব্লার ইফেক্ট সহ সুন্দর ডিজাইন) | ✅ |
| 8 | Real-time health bar (CPU, RAM, AI status) | ✅ |
| 9 | QR Code generation (পাসওয়ার্ড ছাড়া যোগদান) | ✅ |
| 10 | Network map (ARP table) | ✅ |
| 11 | Geofencing indicator | ✅ |
| 12 | Tabbed interface (Commando, AI, Tools, Network, Logs, Settings) | ✅ |
| 13 | PWA support (manifest.json) | ✅ |
| 14 | Password-free access | ✅ |

### Terminal TUI (Rich Live Dashboard)
| # | Feature | Status |
|---|---------|--------|
| 15 | Live system stats (ছোট ছোট বক্সে CPU/RAM) | ✅ |
| 16 | QR code LED box (টার্মিনালেই QR দেখাবে) | ✅ |
| 17 | Live activity log | ✅ |
| 18 | SMS commands panel | ✅ |

### Security
| # | Feature | Status |
|---|---------|--------|
| 19 | Hash-chain audit log (SHA-256) | ✅ |
| 20 | Panic wipe (সব ডেটা মুছে ফেলা) | ✅ |
| 21 | AES encryption support (PyCryptodome) | ✅ |
| 22 | Client fingerprinting | ✅ |

### OSINT / Tactical
| # | Feature | Status |
|---|---------|--------|
| 23 | Nmap network scan | ✅ |
| 24 | Bettercap integration | ✅ |
| 25 | Passive ARP monitor (নতুন ডিভাইস ডিটেকশন) | ✅ |
| 26 | Auto-SMS alert (অজানা MAC এ) | ✅ |
| 27 | Silent camera capture | ✅ |
| 28 | GPS location tracking | ✅ |
| 29 | Geofencing alert (এরিয়া ছেড়ে গেলে SMS) | ✅ |
| 30 | SMS command interface | ✅ |
| 31 | Microphone recording (10s) | ✅ |

### SMS Commands
| Command | কাজ |
|---------|-----|
| `!!LOC` | GPS লোকেশন পাঠায় |
| `!!PHOTO` | সাইলেন্ট ক্যামেরা ছবি |
| `!!WIPE` | রিমোট ডেটা মুছে ফেলা |
| `!!SCAN` | নেটওয়ার্ক স্ক্যান |
| `!!PING` | সিস্টেম চেক |
| `!!RECORD` | 10 সেকেন্ড মাইক্রোফোন রেকর্ড |

### AI (Offline)
| # | Feature | Status |
|---|---------|--------|
| 32 | Ollama LLM integration | ✅ |
| 33 | Qwen 2.5 0.5B model (lightweight) | ✅ |
| 34 | AI Chat (web UI থেকে) | ✅ |
| 35 | Voice input (speech-to-text) | ✅ |
| 36 | Text-to-speech output | ✅ |
| 37 | Auto model download | ✅ |

### Officer Management
| # | Feature | Status |
|---|---------|--------|
| 38 | Officer deploy via QR code | ✅ |
| 39 | Headless officer node script | ✅ |
| 40 | Officer list & tracking | ✅ |
| 41 | Cloud webhook data upload | ✅ |

### Security Tools
| # | Feature | Status |
|---|---------|--------|
| 42 | Metasploit install | ✅ |
| 43 | SQLMap install | ✅ |
| 44 | Hydra install | ✅ |
| 45 | Aircrack-ng install | ✅ |
| 46 | Kali Linux (proot) install | ✅ |
| 47 | WAScan install | ✅ |
| 48 | Nikto install | ✅ |
| 49 | theHarvester install | ✅ |

### API Endpoints
| Endpoint | Method | কাজ |
|----------|--------|-----|
| `/` | GET | Web UI |
| `/api/health` | GET | System health |
| `/api/deploy` | GET | Officer deploy + QR |
| `/api/scan` | GET | Nmap scan |
| `/api/bettercap` | GET | Bettercap |
| `/api/wipe` | GET | Panic wipe |
| `/api/officers` | GET | Officer list |
| `/api/arp` | GET | ARP table |
| `/api/qr` | GET | QR image |
| `/api/ai` | POST | AI chat |
| `/api/voice` | POST | Voice input |
| `/api/speak` | POST | TTS output |
| `/api/record` | GET | Mic record |
| `/api/camera` | GET | Camera capture |
| `/api/gps` | GET | GPS location |
| `/api/config` | POST | Settings update |
| `/api/logs` | GET | Live logs |
| `/api/audit` | GET | Audit chain |
| `/api/tools/install/<name>` | GET | Tool install |
| `/api/tools/list` | GET | Available tools |
| `/install` | GET | Officer node script |

---

## 🖥️ ব্যবহার / Usage

সেটআপ শেষ হলে:

1. **টার্মিনাল TUI** — স্বয়ংক্রিয়ভাবে Rich live dashboard চালু হবে
2. **Web UI** — ব্রাউজারে `http://<your-ip>:8080` খুলুন (পাসওয়ার্ড লাগবে না)
3. **QR Code** — টার্মিনালের QR স্ক্যান করে যেকেউ যোগ দিতে পারবে

---

## ⚠️ প্রয়োজনীয়তা / Requirements

- **Termux** (Android)
- **Termux:API** app (Play Store / F-Droid)
- ইন্টারনেট সংযোগ (প্রথমবার ইন্সটলের জন্য)

---

## 📝 License

[Mozilla Public License 2.0](LICENSE)
