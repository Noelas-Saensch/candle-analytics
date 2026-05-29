#!/bin/bash
# analyze-external-source.sh — Security analysis for untrusted external sources
#
# Analyzes any script, skill, tool, or directory for:
#   - Malicious patterns (eval, exec, obfuscation)
#   - Dangerous imports (os, subprocess, shutil, socket, crypto)
#   - Network calls (requests, urllib, curl, wget, sockets)
#   - File system access (read/write outside expected paths)
#   - Obfuscation (base64, hex, minification)
#   - Persistence mechanisms (cron, startup, screen, service)
#   - Data exfiltration patterns
#
# Usage:
#   ./scripts/analyze-external-source.sh [path|url|file] [...]
#
# Exit code: 0 if low risk, 1 if medium risk, 2 if high risk
#
# Examples:
#   ./scripts/analyze-external-source.sh /tmp/untrusted-script.sh
#   ./scripts/analyze-external-source.sh ~/Downloads/some-repo/
#   ./scripts/analyze-external-source.sh /path/to/skill/SKILL.md

set -o pipefail
cd "$(dirname "$0")/.." || exit 1

RED=$'\033[0;31m'; YELLOW=$'\033[1;33m'; GREEN=$'\033[0;32m'; CYAN=$'\033[0;36m'; NC=$'\033[0m'
pass=0; warn=0; fail=0; info=0
TOTAL_SCORE=0
SCORE_PER_HIGH=25
SCORE_PER_MED=10
SCORE_PER_LOW=3

header()   { printf "\n${CYAN}═══ %s ═══${NC}\n" "$1"; }
subheader(){ printf "${CYAN}  ── %s ──${NC}\n" "$1"; }
pass_msg() { printf "  ${GREEN}✓${NC}  %s\n" "$1"; ((pass++)); }
warn_msg() { printf "  ${YELLOW}⚠${NC}  %s\n" "$1"; ((warn++)); ((TOTAL_SCORE += SCORE_PER_MED)); }
fail_msg() { printf "  ${RED}✗${NC}  %s\n" "$1"; ((fail++)); ((TOTAL_SCORE += SCORE_PER_HIGH)); }
info_msg() { printf "  ${CYAN}ℹ${NC}  %s\n" "$1"; ((info++)); ((TOTAL_SCORE += SCORE_PER_LOW)); }

risk_color() {
  if ((TOTAL_SCORE >= 50)); then echo "${RED}HIGH${NC} (score: $TOTAL_SCORE)"; return 2
  elif ((TOTAL_SCORE >= 20)); then echo "${YELLOW}MEDIUM${NC} (score: $TOTAL_SCORE)"; return 1
  else echo "${GREEN}LOW${NC} (score: $TOTAL_SCORE)"; return 0; fi
}

check_file_readable() {
  local f="$1"
  if [[ -z "$f" ]]; then return 1; fi
  if [[ -f "$f" ]] && [[ -r "$f" ]]; then return 0; fi
  if [[ -d "$f" ]] && [[ -r "$f" ]]; then return 0; fi
  return 1
}

flatten_sources() {
  local src="$1"
  if [[ -d "$src" ]]; then
    find "$src" -type f \( -name '*.py' -o -name '*.sh' -o -name '*.js' -o -name '*.ts' -o -name '*.pl' -o -name '*.rb' -o -name '*.php' -o -name '*.lua' -o -name '*.ps1' -o -name '*.bat' -o -name '*.cmd' -o -name '*.exe' -o -name '*.bin' -o -name '*.so' -o -name '*.dll' -o -name '*.dylib' -o -name '*.elf' -o -name '*.wasm' -o -name 'Makefile' -o -name 'Dockerfile' -o -name 'docker-compose*' -o -name '*.service' -o -name '*.timer' -o -name '*.cron' -o -name '*.plist' -o -name '*.yml' -o -name '*.yaml' -o -name '*.json' -o -name '*.toml' -o -name 'SKILL.md' -o -name '*.md' \) \
      -not -path '*/node_modules/*' -not -path '*/.venv/*' -not -path '*/target/*' -not -path '*/.git/*' -not -path '*/__pycache__/*' -not -path '*/.opencode/node_modules/*' \
      2>/dev/null | sort
  elif [[ -f "$src" ]]; then
    echo "$src"
  fi
}

check_obfuscation() {
  local f="$1" name="$2"
  local ext="${f##*.}"
  local base64_count=0 hex_count=0 minified=0
  local content

  content=$(head -c 50000 "$f" 2>/dev/null) || return

  if echo "$content" | grep -ci 'base64' >/dev/null 2>&1; then
    base64_count=$(echo "$content" | grep -coE '[A-Za-z0-9+/]{40,}={0,2}' 2>/dev/null)
  fi
  if echo "$content" | grep -ci '0x[0-9a-fA-F]' >/dev/null 2>&1; then
    hex_count=$(echo "$content" | grep -coE '0x[0-9a-fA-F]{8,}' 2>/dev/null)
  fi

  minified=$(awk 'BEGIN{m=0} {l=length($0)} l>400 && l<2000 {m++} END{print m+0}' "$f" 2>/dev/null)

  if ((base64_count > 3)); then
    fail_msg "$name: Suspicious base64 strings found ($base64_count) — possible obfuscation"
  fi
  if ((hex_count > 3)); then
    warn_msg "$name: Large hex constants found ($hex_count) — possible obfuscation"
  fi
  if ((minified > 5)); then
    warn_msg "$name: Lines unusually long ($minified lines >400 chars) — possible minified/obfuscated code"
  fi
}

check_dangerous_patterns_py() {
  local f="$1" name="$2"
  local content
  content=$(cat "$f" 2>/dev/null) || return

  echo "$content" | grep -n '\beval(' | head -3 | while IFS=: read -r ln _; do
    fail_msg "$name:$ln — eval() execution of arbitrary code"
  done
  echo "$content" | grep -n '\bexec(' | grep -v '__import__\|executable' | head -3 | while IFS=: read -r ln _; do
    fail_msg "$name:$ln — exec() dynamic code execution"
  done
  echo "$content" | grep -n '\b__import__' | head -3 | while IFS=: read -r ln _; do
    fail_msg "$name:$ln — __import__ dynamic module loading"
  done
  echo "$content" | grep -n '\bcompile(' | head -2 | while IFS=: read -r ln _; do
    fail_msg "$name:$ln — compile() dynamic code compilation"
  done
  echo "$content" | grep -nE '\bos\.(system|popen|fork|exec[lp]*)\s*\(' | head -3 | while IFS=: read -r ln _; do
    fail_msg "$name:$ln — os.system/popen/fork — shell execution"
  done
  echo "$content" | grep -nE '\bsubprocess\.(call|run|Popen|check_call|check_output)\s*\(' | head -3 | while IFS=: read -r ln _; do
    fail_msg "$name:$ln — subprocess execution"
  done
  echo "$content" | grep -nE '\bshutil\.(rmtree|move|copy|chown|chmod)' | head -3 | while IFS=: read -r ln _; do
    warn_msg "$name:$ln — shutil file system modification"
  done
  echo "$content" | grep -nE '\bopen\s*\(' | grep -vE 'open\([^)]*(/tmp|/var|/dev|null|\.json|\.txt|\.csv|\.log|\.yaml|\.yml|\.md)' | head -3 | while IFS=: read -r ln _; do
    warn_msg "$name:$ln — file open (may access arbitrary paths)"
  done
  echo "$content" | grep -nE '\brequests\.(get|post|put|delete)\b' | head -3 | while IFS=: read -r ln _; do
    warn_msg "$name:$ln — HTTP request via requests"
  done
  echo "$content" | grep -nE '\burllib\.(request|urlopen|urlretrieve)' | head -3 | while IFS=: read -r ln _; do
    warn_msg "$name:$ln — URL access via urllib"
  done
  echo "$content" | grep -nE '\bsocket\.(socket|create_connection)' | head -3 | while IFS=: read -r ln _; do
    fail_msg "$name:$ln — raw socket operation"
  done
  echo "$content" | grep -nE '\bctypes\.(CDLL|cdll|windll|create_string_buffer|POINTER)' | head -3 | while IFS=: read -r ln _; do
    fail_msg "$name:$ln — ctypes native code loading"
  done
  echo "$content" | grep -nE '\b(cryptography|Crypto|hashlib\.(md5|sha1))\b' | grep -v 'sha256\|sha512' | head -2 | while IFS=: read -r ln _; do
    warn_msg "$name:$ln — crypto library (ransomware/c2 pattern)"
  done
  echo "$content" | grep -nE '\b(pickle|shelve|dill|joblib)\.(load|loads)\b' | head -2 | while IFS=: read -r ln _; do
    fail_msg "$name:$ln — insecure deserialization (pickle)"
  done
  echo "$content" | grep -nE '\btempfile\.(mkdtemp|mkstemp|NamedTemporaryFile)\b' | head -2 | while IFS=: read -r ln _; do
    info_msg "$name:$ln — tempfile creation (note: check cleanup)"
  done
  echo "$content" | grep -nE 'os\.environ|os\.getenv' | head -2 | while IFS=: read -r ln _; do
    info_msg "$name:$ln — environment variable access"
  done
}

check_dangerous_patterns_sh() {
  local f="$1" name="$2"
  local content
  content=$(cat "$f" 2>/dev/null) || return

  echo "$content" | grep -nE '\b(curl|wget)\s+' | head -3 | while IFS=: read -r ln _; do
    fail_msg "$name:$ln — downloads external content (curl/wget)"
  done
  echo "$content" | grep -nE '>\s*/dev/(tcp|udp)' | head -3 | while IFS=: read -r ln _; do
    fail_msg "$name:$ln — bash /dev/tcp network access"
  done
  echo "$content" | grep -nE '\beval\b' | head -3 | while IFS=: read -r ln _; do
    fail_msg "$name:$ln — eval dynamic execution"
  done
  echo "$content" | grep -nE 'exec\s+' | head -2 | while IFS=: read -r ln _; do
    fail_msg "$name:$ln — exec replacement of current process"
  done
  echo "$content" | grep -nE '(sudo|chmod\s+4[4-7][0-9]|chmod\s+[0-7]*777|chown)' | head -3 | while IFS=: read -r ln _; do
    warn_msg "$name:$ln — privilege escalation or permission change"
  done
  echo "$content" | grep -nE '(iptables|ufw|firewall-cmd|nft)' | head -2 | while IFS=: read -r ln _; do
    warn_msg "$name:$ln — firewall modification"
  done
  echo "$content" | grep -nE '(crontab|systemctl|service\s+|update-rc\.d|rc\.local|~/.bashrc|~/.profile|~/.zshrc)' | head -3 | while IFS=: read -r ln _; do
    fail_msg "$name:$ln — persistence mechanism (cron/service/startup)"
  done
  echo "$content" | grep -nE '(ssh|scp|rsync)\s' | head -2 | while IFS=: read -r ln _; do
    warn_msg "$name:$ln — SSH/remote connection"
  done
  echo "$content" | grep -nE '(passwd|shadow|/etc/|/var/log|/var/spool)' | head -2 | while IFS=: read -r ln _; do
    warn_msg "$name:$ln — system file access (/etc/ /var/)"
  done
  echo "$content" | grep -nE '(dd\s+if=|mkfs|fdisk|parted|mkswap)' | head -2 | while IFS=: read -r ln _; do
    fail_msg "$name:$ln — raw disk/block device access"
  done
  echo "$content" | grep -nE '(2>&1\s*&|>/dev/null\s*2>&1\s*&|setsid|disown|nohup)' | head -3 | while IFS=: read -r ln _; do
    info_msg "$name:$ln — background/daemon process"
  done
}

check_dangerous_patterns_js() {
  local f="$1" name="$2"
  local content
  content=$(cat "$f" 2>/dev/null) || return

  echo "$content" | grep -nE '\beval\s*\(' | head -3 | while IFS=: read -r ln _; do
    fail_msg "$name:$ln — eval() dynamic execution"
  done
  echo "$content" | grep -nE '\bFunction\s*\(' | head -2 | while IFS=: read -r ln _; do
    fail_msg "$name:$ln — Function() constructor (eval alternative)"
  done
  echo "$content" | grep -nE '(document\.write|innerHTML\s*=)' | head -3 | while IFS=: read -r ln _; do
    warn_msg "$name:$ln — DOM injection (XSS risk)"
  done
  echo "$content" | grep -nE '(localStorage|sessionStorage|indexedDB)' | head -2 | while IFS=: read -r ln _; do
    info_msg "$name:$ln — browser storage access"
  done
  echo "$content" | grep -nE '(fetch\s*\(|XMLHttpRequest|WebSocket\s*\()' | head -3 | while IFS=: read -r ln _; do
    warn_msg "$name:$ln — network request (fetch/XHR/WebSocket)"
  done
  echo "$content" | grep -nE '(require\s*\(\s*["\x27]child_process|require\s*\(\s*["\x27]fs|require\s*\(\s*["\x27]net|require\s*\(\s*["\x27]http)' | head -3 | while IFS=: read -r ln _; do
    fail_msg "$name:$ln — Node.js system module import"
  done
  echo "$content" | grep -nE '(process\.env|__dirname|__filename|process\.exit)' | head -2 | while IFS=: read -r ln _; do
    info_msg "$name:$ln — Node.js process/FS access"
  done
  echo "$content" | grep -nE '(atob|btoa|Buffer\.from|Buffer\.alloc)' | head -2 | while IFS=: read -r ln _; do
    info_msg "$name:$ln — base64 encode/decode"
  done
}

check_skill_file() {
  local f="$1" name="$2"
  local content
  content=$(cat "$f" 2>/dev/null) || return

  echo "$content" | grep -nE '(curl|wget)\s' | head -3 | while IFS=: read -r ln _; do
    warn_msg "$name:$ln — network download in skill"
  done
  echo "$content" | grep -nE '(chmod|sudo|chown)' | head -3 | while IFS=: read -r ln _; do
    warn_msg "$name:$ln — privileged operation in skill"
  done
  echo "$content" | grep -nE '(rm\s+-rf|rmdir|rm\s+--no-preserve-root)' | head -3 | while IFS=: read -r ln _; do
    fail_msg "$name:$ln — destructive deletion in skill"
  done
  echo "$content" | grep -nE '>\s*/tmp/|>\s*/var/|>\s*/etc/|>\s*/usr/' | head -3 | while IFS=: read -r ln _; do
    warn_msg "$name:$ln — writes to system directory"
  done
  echo "$content" | grep -nE '(git\s+clone|pip\s+install|npm\s+install|apt-get|yum\s+install)' | head -3 | while IFS=: read -r ln _; do
    info_msg "$name:$ln — external dependency installation"
  done
}

check_binary() {
  local f="$1" name="$2"
  local ext="${f##*.}"
  local size
  size=$(stat -c%s "$f" 2>/dev/null || echo 0)

  local mime
  mime=$(file -b --mime-type "$f" 2>/dev/null || echo "unknown")

  info_msg "$name: binary file — $mime, ${size} bytes"

  local strings_danger
  strings_danger=$(strings "$f" 2>/dev/null | grep -ciE '(eval|exec|system|socket|connect|sendto|recvfrom|password|secret|token|key)' 2>/dev/null || echo 0)
  if ((strings_danger > 5)); then
    warn_msg "$name: binary contains $strings_danger suspicious strings (eval/exec/socket/secret references)"
  fi
}

check_yaml_docker() {
  local f="$1" name="$2"
  local content
  content=$(cat "$f" 2>/dev/null) || return

  echo "$content" | grep -nE 'privileged:\s*true' | head -2 | while IFS=: read -r ln _; do
    fail_msg "$name:$ln — privileged container (full host access)"
  done
  echo "$content" | grep -nE 'network_mode:\s*"host"|network_mode:\s*host' | head -2 | while IFS=: read -r ln _; do
    warn_msg "$name:$ln — host network mode"
  done
  echo "$content" | grep -nE 'volumes:\s*-\s*/:|volumes:\s*-\s*/etc' | head -2 | while IFS=: read -r ln _; do
    warn_msg "$name:$ln — binds host system directory"
  done
  echo "$content" | grep -nE 'ports:\s*-\s*"[0-9]+:[0-9]+"' | head -2 | while IFS=: read -r ln _; do
    info_msg "$name:$ln — exposes container port"
  done
  echo "$content" | grep -nE 'image:\s*(latest|nightly|dev)' | head -2 | while IFS=: read -r ln _; do
    warn_msg "$name:$ln — uses unstable/latest image tag"
  done
}

analyze_file() {
  local f="$1"
  local name
  name=$(echo "$f" | sed "s|$(pwd)/||")
  local ext="${f##*.}"

  check_obfuscation "$f" "$name"

  case "$ext" in
    py)
      check_dangerous_patterns_py "$f" "$name"
      ;;
    sh|bash|zsh|ksh)
      check_dangerous_patterns_sh "$f" "$name"
      ;;
    js|ts|mjs|cjs)
      check_dangerous_patterns_js "$f" "$name"
      ;;
    pl|rb|php|lua|ps1|bat|cmd)
      check_dangerous_patterns_sh "$f" "$name"
      ;;
    yml|yaml)
      check_yaml_docker "$f" "$name"
      ;;
    md)
      if echo "$name" | grep -qi 'skill'; then
        check_skill_file "$f" "$name"
      fi
      ;;
    service|timer|cron|plist)
      warn_msg "$name: system service/daemon configuration"
      ;;
    exe|bin|so|dll|dylib|elf|wasm)
      check_binary "$f" "$name"
      ;;
    *)
      local mime
      mime=$(file -b --mime-type "$f" 2>/dev/null || echo "")
      case "$mime" in
        application/x-executable|application/x-sharedlib|application/x-mach-binary|application/vnd.microsoft.portable-executable)
          check_binary "$f" "$name"
          ;;
      esac
      ;;
  esac
}

# ─── OVERALL CHECK: look for known malware signatures ───
check_known_malware() {
  local src="$1"
  header "Known Malware Signatures"

  local found=0
  local exclude_dirs='--exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=target --exclude-dir=__pycache__'
  # Coin miners
  if grep -rlsI $exclude_dirs 'cryptonight\|minerd\|stratum\+tcp\|xmrig\|cpuminer\|coinhive\|miner\.\?js' "$src" 2>/dev/null | head -5 | while IFS= read -r f; do
    local fn
    fn=$(echo "$f" | sed "s|$(pwd)/||")
    fail_msg "$fn — cryptocurrency miner reference"
    found=1
  done; then :; fi

  # Ransomware
  if grep -rlsI $exclude_dirs 'encrypt_file\|decrypt_file\|ransomware\|wannacry\|locky\|cryptolocker\|petya\|notpetya' "$src" 2>/dev/null | head -5 | while IFS= read -r f; do
    local fn
    fn=$(echo "$f" | sed "s|$(pwd)/||")
    fail_msg "$fn — ransomware/keyword reference"
    found=1
  done; then :; fi

  # Backdoor
  if grep -rlsI $exclude_dirs 'backdoor\|reverse_shell\|bind_shell\|meterpreter\|beacon\|c2server\|command.and.control' "$src" 2>/dev/null | head -5 | while IFS= read -r f; do
    local fn
    fn=$(echo "$f" | sed "s|$(pwd)/||")
    fail_msg "$fn — backdoor/C2 reference"
    found=1
  done; then :; fi

  # Keylogger
  if grep -rnI $exclude_dirs 'keyboard.*hook\|keylogger\|GetAsyncKeyState\|GetForegroundWindow\|keypress.*log' "$src" 2>/dev/null | head -3 | while IFS=: read -r fn _; do
    local fn2
    fn2=$(echo "$fn" | sed "s|$(pwd)/||")
    fail_msg "$fn2 — keylogger pattern"
    found=1
  done; then :; fi

  # Process injection
  if grep -rlsI $exclude_dirs 'CreateRemoteThread\|WriteProcessMemory\|VirtualAllocEx\|ptrace\|process.*inject' "$src" 2>/dev/null | head -5 | while IFS= read -r f; do
    local fn
    fn=$(echo "$f" | sed "s|$(pwd)/||")
    fail_msg "$fn — process injection pattern"
    found=1
  done; then :; fi

  if ((found == 0)); then
    pass_msg "No known malware signatures detected"
  fi
}

# ─── OVERALL CHECK: check for obfuscated filenames ───
check_hidden_files() {
  local src="$1"
  header "Hidden & Suspicious Files"

  local found=0

  while IFS= read -r -d '' f; do
    local fn
    fn=$(echo "$f" | sed "s|$(pwd)/||")
    if echo "$f" | grep -q '/\.[^/]'; then
      warn_msg "$fn — hidden file/directory"
      found=1
    fi
  done < <(find "$src" -name '.*' -not -name '.' -not -name '..' -not -name '.git' -not -name '.env' -not -name '.gitignore' -not -name '.dockerignore' -print0 2>/dev/null)

  while IFS= read -r -d '' f; do
    local fn
    fn=$(echo "$f" | sed "s|$(pwd)/||")
    warn_msg "$fn — executable file in source"
    found=1
  done < <(find "$src" -type f -executable -not -path '*/\.git/*' -not -name '*.sh' -not -name '*.py' 2>/dev/null | head -5)

  if ((found == 0)); then
    pass_msg "No hidden or suspicious files found"
  fi
}

# ─── OVERALL STRUCTURE ───
check_source_structure() {
  local src="$1"
  header "Source Structure"

  local total_files
  total_files=$(find "$src" -type f -not -path '*/\.git/*' -not -path '*/node_modules/*' -not -path '*/.venv/*' -not -path '*/target/*' -not -path '*/__pycache__/*' 2>/dev/null | wc -l)
  local total_dirs
  total_dirs=$(find "$src" -type d -not -path '*/\.git/*' -not -path '*/node_modules/*' -not -path '*/.venv/*' -not -path '*/target/*' -not -path '*/__pycache__/*' 2>/dev/null | wc -l)
  local total_size
  total_size=$(du -sh "$src" 2>/dev/null | cut -f1)

  info_msg "Total files: $total_files"
  info_msg "Total directories: $total_dirs"
  info_msg "Total size: $total_size"

  local py_files sh_files js_files bin_files
  local find_excl='! -path "*/node_modules/*" ! -path "*/.venv/*" ! -path "*/target/*" ! -path "*/__pycache__/*"'
  py_files=$(find "$src" -name '*.py' -not -path '*/\.git/*' -not -path '*/node_modules/*' -not -path '*/.venv/*' -not -path '*/target/*' 2>/dev/null | wc -l)
  sh_files=$(find "$src" -name '*.sh' -not -path '*/\.git/*' -not -path '*/node_modules/*' -not -path '*/.venv/*' -not -path '*/target/*' 2>/dev/null | wc -l)
  js_files=$(find "$src" -name '*.js' -not -path '*/\.git/*' -not -path '*/node_modules/*' -not -path '*/.venv/*' -not -path '*/target/*' 2>/dev/null | wc -l)
  bin_files=$(find "$src" -type f \( -name '*.exe' -o -name '*.bin' -o -name '*.so' -o -name '*.dll' -o -name '*.dylib' -o -name '*.elf' -o -name '*.wasm' \) -not -path '*/\.git/*' -not -path '*/node_modules/*' -not -path '*/.venv/*' -not -path '*/target/*' 2>/dev/null | wc -l)

  info_msg "Python files: $py_files"
  info_msg "Shell scripts: $sh_files"
  info_msg "JavaScript files: $js_files"
  [[ $bin_files -gt 0 ]] && warn_msg "Pre-compiled binaries: $bin_files"

  local readme_present=0 license_present=0
  for f in README.md README readme; do
    [[ -f "$src/$f" ]] && { readme_present=1; break; }
  done
  for f in LICENSE license LICENSE.txt COPYING; do
    [[ -f "$src/$f" ]] && { license_present=1; break; }
  done
  [[ $readme_present -eq 1 ]] && pass_msg "README found" || info_msg "No README found"
  [[ $license_present -eq 1 ]] && pass_msg "License found" || info_msg "No license found"

  local empty_dirs
  empty_dirs=$(find "$src" -type d -empty -not -path '*/\.git/*' 2>/dev/null | wc -l)
  [[ $empty_dirs -gt 0 ]] && info_msg "Empty directories: $empty_dirs"
}

# ═══════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════

main() {
  local targets=("$@")
  if [[ ${#targets[@]} -eq 0 ]]; then
    echo "Usage: $0 <path|file> [file2 ...]"
    echo "  Analyze external scripts, skills, tools, or repos for security risks"
    echo ""
    echo "  Exit codes: 0 = LOW risk, 1 = MEDIUM risk, 2 = HIGH risk"
    exit 1
  fi

  local any_high=0 any_medium=0
  local global_exit=0

  for src in "${targets[@]}"; do
    if [[ ! -e "$src" ]]; then
      echo "Error: '$src' not found" >&2
      continue
    fi

    local src_name
    src_name=$(echo "$src" | sed "s|$(pwd)/||" | sed "s|$HOME|~|")

    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║  SECURITY ANALYSIS: $src_name"
    echo "╚══════════════════════════════════════════════════════════════╝"

    TOTAL_SCORE=0; pass=0; warn=0; fail=0; info=0

    check_source_structure "$src"
    check_hidden_files "$src"
    check_known_malware "$src"

    header "File-by-File Analysis"
    local analyzed=0
    while IFS= read -r f; do
      if [[ -f "$f" ]] && [[ -r "$f" ]]; then
        analyze_file "$f"
        ((analyzed++))
      fi
    done < <(flatten_sources "$src")

    if ((analyzed == 0)); then
      info_msg "No analyzable source files found — only binary/unknown data"
    fi

    echo ""
    header "Summary"
    printf "  ${GREEN}✓${NC} Pass: %-3d  ${YELLOW}⚠${NC} Warn: %-3d  ${RED}✗${NC} Fail: %-3d  ${CYAN}ℹ${NC} Info: %-3d\n" "$pass" "$warn" "$fail" "$info"
    printf "  Overall risk: "
    risk_color; risk_exit=$?
    [[ $risk_exit -gt $global_exit ]] && global_exit=$risk_exit
  done

  exit "$global_exit"
}

main "$@"
