# Turmux- ★

> **Termux ওয়ান-কমান্ড সেটআপ সিস্টেম**
> একটি কমান্ড দিয়ে Termux-এ সম্পূর্ণ ডেভেলপমেন্ট এনভায়রনমেন্ট তৈরি করুন।

---

## 🚀 ইনস্টল / Install

Termux অ্যাপ খুলুন এবং নিচের কমান্ডটি কপি-পেস্ট করে **Enter** দিন:

```bash
curl -sL https://raw.githubusercontent.com/alvie382218-debug/Turmux-/main/setup.sh | bash
```

অথবা, git ব্যবহার করে:

```bash
pkg install -y git && git clone https://github.com/alvie382218-debug/Turmux-.git && bash Turmux-/setup.sh
```

---

## 📦 কী কী ইনস্টল হবে / What Gets Installed

| ক্যাটাগরি | প্যাকেজ |
|---|---|
| **Essential Tools** | git, curl, wget, ssh, nano, vim, tmux, htop, neofetch, jq |
| **Languages** | Python, Node.js, C/C++ (clang), Ruby, PHP, Go, Rust |
| **Python Packages** | requests, flask, beautifulsoup4, rich, colorama, pyfiglet |
| **Network Tools** | nmap, hydra, netcat, dnsutils, whois |
| **Fun Tools** | cmatrix, figlet, toilet, sl, ffmpeg, imagemagick |

---

## 🎮 ব্যবহার / Usage

সেটআপ শেষ হলে এই কমান্ডগুলো ব্যবহার করতে পারবেন:

| কমান্ড | কাজ |
|---|---|
| `turmux-menu` | ইন্টার‍্যাক্টিভ মেনু খোলে |
| `sysinfo` | সিস্টেম তথ্য দেখায় |
| `myip` | পাবলিক IP দেখায় |
| `serve` | ওয়েব সার্ভার চালু করে (port 8080) |
| `update` | সব প্যাকেজ আপডেট করে |
| `speedtest` | ইন্টারনেট স্পিড টেস্ট |
| `py` / `py3` | Python চালু করে |

---

## 📁 ফোল্ডার স্ট্রাকচার / Directory Structure

সেটআপের পরে তৈরি হওয়া ফোল্ডারগুলো:

```
~/
├── projects/
│   ├── python/
│   ├── web/
│   └── scripts/
├── downloads/
└── backups/
```

---

## 📸 Screenshots

সেটআপের পর `turmux-menu` কমান্ড দিলে এই মেনু আসবে:

```
  ╔════════════════════════════════════════╗
  ║          ★ TURMUX MENU ★               ║
  ╚════════════════════════════════════════╝

  [1] System Info          [6] Python Shell
  [2] Network Info         [7] Node.js Shell
  [3] Speed Test           [8] File Manager
  [4] Port Scanner         [9] Update System
  [5] Web Server           [0] Exit
```

---

## 📝 License

[Mozilla Public License 2.0](LICENSE)
