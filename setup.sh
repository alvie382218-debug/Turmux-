#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
#  Turmux- : Termux One-Command Setup Script
#  কপি-পেস্ট করে Enter দিলেই সম্পূর্ণ সিস্টেম তৈরি হবে
# ============================================================

set -e

# ---------- Colors ----------
R='\033[1;31m'
G='\033[1;32m'
Y='\033[1;33m'
B='\033[1;34m'
C='\033[1;36m'
W='\033[1;37m'
N='\033[0m'

banner() {
    clear
    echo -e "${C}"
    echo "  ╔════════════════════════════════════════╗"
    echo "  ║          ★ TURMUX SETUP ★              ║"
    echo "  ║   Termux Full Development Environment  ║"
    echo "  ╚════════════════════════════════════════╝"
    echo -e "${N}"
}

info()    { echo -e "${G}[✔] $1${N}"; }
warn()    { echo -e "${Y}[!] $1${N}"; }
error()   { echo -e "${R}[✘] $1${N}"; }
section() { echo -e "\n${B}━━━ $1 ━━━${N}"; }

# ---------- 1. Storage Permission ----------
banner
section "Storage Permission / স্টোরেজ পারমিশন"
if [ ! -d "$HOME/storage" ]; then
    warn "Termux Storage permission চাইবে — Allow দিন"
    termux-setup-storage
    sleep 3
fi
info "Storage permission OK"

# ---------- 2. Update & Upgrade ----------
section "Updating packages / প্যাকেজ আপডেট"
yes | pkg update -y && pkg upgrade -y
info "Packages updated"

# ---------- 3. Essential Packages ----------
section "Installing essential packages / প্রয়োজনীয় প্যাকেজ ইনস্টল"

ESSENTIALS=(
    git
    curl
    wget
    openssl
    openssh
    tar
    zip
    unzip
    which
    tree
    nano
    vim
    neofetch
    htop
    man
    bc
    jq
    tmux
    screen
)

for pkg_name in "${ESSENTIALS[@]}"; do
    echo -e "${W}  → Installing ${pkg_name}...${N}"
    pkg install -y "$pkg_name" 2>/dev/null || true
done
info "Essential packages installed"

# ---------- 4. Programming Languages ----------
section "Installing programming languages / প্রোগ্রামিং ল্যাঙ্গুয়েজ"

LANGUAGES=(
    python
    nodejs
    clang
    ruby
    php
    golang
    rust
)

for lang in "${LANGUAGES[@]}"; do
    echo -e "${W}  → Installing ${lang}...${N}"
    pkg install -y "$lang" 2>/dev/null || true
done

# Upgrade pip
pip install --upgrade pip 2>/dev/null || true
info "Programming languages installed"

# ---------- 5. Python Packages ----------
section "Installing Python packages / পাইথন প্যাকেজ"

PYTHON_PKGS=(
    requests
    flask
    beautifulsoup4
    rich
    colorama
    pyfiglet
)

for pypkg in "${PYTHON_PKGS[@]}"; do
    echo -e "${W}  → pip install ${pypkg}...${N}"
    pip install "$pypkg" 2>/dev/null || true
done
info "Python packages installed"

# ---------- 6. Networking & Security Tools ----------
section "Installing network tools / নেটওয়ার্ক টুলস"

NET_TOOLS=(
    nmap
    hydra
    netcat-openbsd
    dnsutils
    iproute2
    tracepath
    whois
)

for ntool in "${NET_TOOLS[@]}"; do
    echo -e "${W}  → Installing ${ntool}...${N}"
    pkg install -y "$ntool" 2>/dev/null || true
done
info "Network tools installed"

# ---------- 7. File & Text Tools ----------
section "Installing file tools / ফাইল টুলস"

FILE_TOOLS=(
    ffmpeg
    imagemagick
    figlet
    toilet
    cmatrix
    sl
)

for ftool in "${FILE_TOOLS[@]}"; do
    echo -e "${W}  → Installing ${ftool}...${N}"
    pkg install -y "$ftool" 2>/dev/null || true
done
info "File tools installed"

# ---------- 8. Shell Configuration ----------
section "Configuring shell / শেল কনফিগারেশন"

# .bashrc
cat >> "$HOME/.bashrc" << 'BASHRC'

# ── Turmux- Custom Config ──
export PS1="\[\e[1;36m\]┌──[\[\e[1;32m\]\u\[\e[1;36m\]@\[\e[1;33m\]termux\[\e[1;36m\]]-[\[\e[1;35m\]\w\[\e[1;36m\]]\n└──╼ \[\e[1;37m\]\$ \[\e[0m\]"
export PATH="$HOME/.local/bin:$PATH"

alias ll='ls -la --color=auto'
alias la='ls -A --color=auto'
alias l='ls -CF --color=auto'
alias cls='clear'
alias py='python'
alias py3='python3'
alias serve='python -m http.server 8080'
alias myip='curl -s ifconfig.me && echo'
alias update='pkg update -y && pkg upgrade -y'
alias speedtest='curl -s https://raw.githubusercontent.com/sivel/speedtest-cli/master/speedtest.py | python'

# Color support
export TERM=xterm-256color

# Greeting
neofetch 2>/dev/null || echo "Welcome to Turmux-!"
BASHRC

info "Shell configured with custom prompt & aliases"

# ---------- 9. Create Project Directories ----------
section "Creating project folders / প্রজেক্ট ফোল্ডার তৈরি"

DIRS=(
    "$HOME/projects"
    "$HOME/projects/python"
    "$HOME/projects/web"
    "$HOME/projects/scripts"
    "$HOME/downloads"
    "$HOME/backups"
)

for dir in "${DIRS[@]}"; do
    mkdir -p "$dir"
done
info "Project directories created"

# ---------- 10. Create Helper Scripts ----------
section "Creating helper scripts / হেল্পার স্ক্রিপ্ট"

# --- sysinfo script ---
mkdir -p "$HOME/.local/bin"
cat > "$HOME/.local/bin/sysinfo" << 'SYSINFO'
#!/data/data/com.termux/files/usr/bin/bash
echo -e "\033[1;36m╔═══════════════════════════════════╗"
echo -e "║       SYSTEM INFORMATION          ║"
echo -e "╚═══════════════════════════════════╝\033[0m"
echo -e "\033[1;32m  OS      :\033[0m $(uname -o)"
echo -e "\033[1;32m  Kernel  :\033[0m $(uname -r)"
echo -e "\033[1;32m  Arch    :\033[0m $(uname -m)"
echo -e "\033[1;32m  User    :\033[0m $(whoami)"
echo -e "\033[1;32m  Shell   :\033[0m $SHELL"
echo -e "\033[1;32m  Home    :\033[0m $HOME"
echo -e "\033[1;32m  Uptime  :\033[0m $(uptime -p 2>/dev/null || uptime)"
echo -e "\033[1;32m  Memory  :\033[0m $(free -h 2>/dev/null | awk '/Mem/{print $3"/"$2}' || echo 'N/A')"
echo -e "\033[1;32m  Storage :\033[0m $(df -h $HOME | awk 'NR==2{print $3"/"$2}')"
echo -e "\033[1;32m  IP      :\033[0m $(curl -s ifconfig.me 2>/dev/null || echo 'N/A')"
echo -e "\033[1;32m  Python  :\033[0m $(python --version 2>/dev/null || echo 'N/A')"
echo -e "\033[1;32m  Node    :\033[0m $(node --version 2>/dev/null || echo 'N/A')"
echo -e "\033[1;32m  Git     :\033[0m $(git --version 2>/dev/null || echo 'N/A')"
SYSINFO
chmod +x "$HOME/.local/bin/sysinfo"

# --- menu script ---
cat > "$HOME/.local/bin/turmux-menu" << 'MENU'
#!/data/data/com.termux/files/usr/bin/bash
while true; do
    clear
    echo -e "\033[1;36m"
    echo "  ╔════════════════════════════════════════╗"
    echo "  ║          ★ TURMUX MENU ★               ║"
    echo "  ╚════════════════════════════════════════╝"
    echo -e "\033[0m"
    echo -e "\033[1;33m  [1]\033[0m System Info          \033[1;33m[6]\033[0m Python Shell"
    echo -e "\033[1;33m  [2]\033[0m Network Info         \033[1;33m[7]\033[0m Node.js Shell"
    echo -e "\033[1;33m  [3]\033[0m Speed Test           \033[1;33m[8]\033[0m File Manager"
    echo -e "\033[1;33m  [4]\033[0m Port Scanner         \033[1;33m[9]\033[0m Update System"
    echo -e "\033[1;33m  [5]\033[0m Web Server           \033[1;33m[0]\033[0m Exit"
    echo ""
    echo -ne "\033[1;32m  Select ➜ \033[0m"
    read -r choice
    case $choice in
        1) sysinfo; read -rp "  Press Enter..." ;;
        2)
            echo -e "\n\033[1;32m  Public IP:\033[0m $(curl -s ifconfig.me)"
            echo -e "\033[1;32m  Local IP:\033[0m $(ip addr show 2>/dev/null | grep 'inet ' | awk '{print $2}' | head -3)"
            echo -e "\033[1;32m  DNS:\033[0m $(getprop net.dns1 2>/dev/null || echo 'N/A')"
            read -rp "  Press Enter..."
            ;;
        3) curl -s https://raw.githubusercontent.com/sivel/speedtest-cli/master/speedtest.py | python; read -rp "  Press Enter..." ;;
        4)
            echo -ne "\033[1;32m  Target IP/Host: \033[0m"; read -r target
            echo -ne "\033[1;32m  Port range (e.g. 1-1000): \033[0m"; read -r ports
            nmap -p "$ports" "$target" 2>/dev/null || echo "nmap not available"
            read -rp "  Press Enter..."
            ;;
        5)
            echo -e "\033[1;32m  Starting web server on port 8080...\033[0m"
            echo -e "\033[1;33m  Open browser: http://localhost:8080\033[0m"
            echo -e "\033[1;31m  Press Ctrl+C to stop\033[0m"
            cd "$HOME" && python -m http.server 8080
            ;;
        6) python ;;
        7) node ;;
        8)
            echo -ne "\033[1;32m  Directory (default: $HOME): \033[0m"; read -r dir
            dir="${dir:-$HOME}"
            ls -la "$dir"
            read -rp "  Press Enter..."
            ;;
        9) pkg update -y && pkg upgrade -y; read -rp "  Press Enter..." ;;
        0) clear; echo -e "\033[1;32m  Goodbye! 👋\033[0m"; exit 0 ;;
        *) echo -e "\033[1;31m  Invalid option!\033[0m"; sleep 1 ;;
    esac
done
MENU
chmod +x "$HOME/.local/bin/turmux-menu"

info "Helper scripts created (sysinfo, turmux-menu)"

# ---------- Done ----------
echo ""
echo -e "${G}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
echo -e "${C}"
echo "  ╔════════════════════════════════════════════╗"
echo "  ║    ✅  SETUP COMPLETE / সেটআপ সম্পন্ন!    ║"
echo "  ╚════════════════════════════════════════════╝"
echo -e "${N}"
echo -e "${W}  Installed / ইনস্টল হয়েছে:${N}"
echo -e "${Y}    • Essential tools (git, curl, wget, ssh...)${N}"
echo -e "${Y}    • Languages (Python, Node.js, C/C++, Ruby, PHP, Go, Rust)${N}"
echo -e "${Y}    • Python packages (requests, flask, beautifulsoup4...)${N}"
echo -e "${Y}    • Network tools (nmap, hydra, netcat...)${N}"
echo -e "${Y}    • Fun tools (cmatrix, figlet, sl...)${N}"
echo ""
echo -e "${W}  Commands / কমান্ড:${N}"
echo -e "${G}    turmux-menu  ${W}→ Interactive menu / মেনু খুলুন${N}"
echo -e "${G}    sysinfo      ${W}→ System info / সিস্টেম তথ্য${N}"
echo -e "${G}    myip         ${W}→ Public IP address${N}"
echo -e "${G}    serve        ${W}→ Start web server (port 8080)${N}"
echo -e "${G}    update       ${W}→ Update all packages${N}"
echo -e "${G}    speedtest    ${W}→ Internet speed test${N}"
echo ""
echo -e "${C}  ★ Restart Termux for full effect / পুনরায় চালু করুন ★${N}"
echo -e "${G}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
