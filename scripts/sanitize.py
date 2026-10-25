#!/usr/bin/env python3
import re
import hashlib
from pathlib import Path
import idna

# =========================
# Base paths (robusto)
# =========================
# scripts/sanitize.py  -> repo root = parents[1]
BASE = Path(__file__).resolve().parents[1]

RAW = BASE / "tmp" / "raw.txt"
BUILD = BASE / "build"
BUILD.mkdir(parents=True, exist_ok=True)

WHITELIST_FILE = BASE / "whitelist.txt"   # siempre gana
BLACKLIST_FILE = BASE / "blacklist.txt"   # se suma siempre

HOST_PREFIXES = ("0.0.0.0 ", "127.0.0.1 ", ":: ", "::1 ")

# Regex de dominio "clásico" (sin '_').
DOMAIN_RE = re.compile(
    r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)+$"
)

stats = {
    "total_lines": 0,
    "valid_domains": 0,
    "invalid_domain": 0,
    "adblock_rules_parsed": 0,
    "adblock_rules_skipped": 0,
    "urls": 0,
    "ips": 0,
    "empty_or_comment": 0,
}

def extract_from_adblock(s: str):
    """
    Soporta reglas simples:
      ||example.com^
      @@||example.com^$important
      ||example.com^$third-party
    Devuelve dominio o None si no es parseable como dominio simple.
    """
    original = s

    # allowlist simple
    if s.startswith("@@||"):
        s = s[4:]
    elif s.startswith("||"):
        s = s[2:]
    else:
        return None

    # cortar en ^ y $
    if "^" in s:
        s = s.split("^", 1)[0]
    if "$" in s:
        s = s.split("$", 1)[0]

    s = s.strip()
    # si quedó vacío o tiene cosas raras, descartamos
    if not s or "/" in s or "*" in s:
        return None

    return s

def to_domain(line: str, *, update_stats: bool = True):
    s = line.strip().lower()
    s = s.lstrip("\ufeff").replace("\r", "")

    if update_stats:
        stats["total_lines"] += 1

    if not s or s.startswith("#"):
        if update_stats:
            stats["empty_or_comment"] += 1
        return None

    # hosts format: "0.0.0.0 domain"
    for p in HOST_PREFIXES:
        if s.startswith(p):
            s = s[len(p):].strip()
            s = s.split()[0] if s else ""
            break

    # inline comments: "domain.com # comment"
    if " #" in s:
        s = s.split(" #", 1)[0].strip()

    s = s.strip(" <>")

    # wildcard "*.example.com" -> "example.com"
    if s.startswith("*."):
        s = s[2:]

    # trailing dot
    if s.endswith("."):
        s = s[:-1]

    # URLs
    if s.startswith(("http://", "https://")) or "://" in s or "/" in s:
        if update_stats:
            stats["urls"] += 1
        return None

    # Adblock/AdGuard simple -> dominio
    if s.startswith("||") or s.startswith("@@||"):
        d = extract_from_adblock(s)
        if d:
            if update_stats:
                stats["adblock_rules_parsed"] += 1
            s = d
        else:
            if update_stats:
                stats["adblock_rules_skipped"] += 1
            return None

    # reglas cosméticas u otras no soportadas
    if s.startswith(("##", "#@#", "@@")):
        if update_stats:
            stats["adblock_rules_skipped"] += 1
        return None

    if s.startswith("."):
        if update_stats:
            stats["invalid_domain"] += 1
        return None

    # IPv4 pura
    if re.fullmatch(r"\d+\.\d+\.\d+\.\d+", s):
        if update_stats:
            stats["ips"] += 1
        return None

    # IDNA
    try:
        s = idna.encode(s).decode("ascii")
    except Exception:
        if update_stats:
            stats["invalid_domain"] += 1
        return None

    if not DOMAIN_RE.fullmatch(s) or len(s) > 253:
        if update_stats:
            stats["invalid_domain"] += 1
        return None

    if update_stats:
        stats["valid_domains"] += 1
    return s

def is_subdomain_or_same(domain: str, root: str) -> bool:
    return domain == root or domain.endswith("." + root)

def sha256sum(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

# =========================
# Load allow/deny
# =========================
whitelist = set()
if WHITELIST_FILE.exists():
    with WHITELIST_FILE.open(encoding="utf-8", errors="ignore") as wf:
        for line in wf:
            d = to_domain(line, update_stats=False)
            if d:
                whitelist.add(d)

blacklist = set()
if BLACKLIST_FILE.exists():
    with BLACKLIST_FILE.open(encoding="utf-8", errors="ignore") as bf:
        for line in bf:
            d = to_domain(line, update_stats=False)
            if d:
                blacklist.add(d)

# =========================
# Main processing
# =========================
if not RAW.exists():
    raise SystemExit(f"ERROR: missing {RAW}")

domains = set()
with RAW.open(encoding="utf-8", errors="ignore") as fh:
    for line in fh:
        d = to_domain(line, update_stats=True)
        if d:
            domains.add(d)

# sumar blacklist propia
domains |= blacklist

# aplicar whitelist (quita w y subdominios)
if whitelist:
    wl = sorted(whitelist, key=len, reverse=True)
    domains = {d for d in domains if not any(is_subdomain_or_same(d, w) for w in wl)}

dom_sorted = sorted(domains)

# =========================
# Outputs
# =========================
(BUILD / "domains.txt").write_text("\n".join(dom_sorted) + ("\n" if dom_sorted else ""), encoding="utf-8")
(BUILD / "technitium-domains.txt").write_text("\n".join(dom_sorted) + ("\n" if dom_sorted else ""), encoding="utf-8")

with open(BUILD / "pihole-hosts.txt", "w", encoding="utf-8", newline="\n") as f:
    for d in dom_sorted:
        f.write(f"0.0.0.0 {d}\n")

with open(BUILD / "technitium-hosts.txt", "w", encoding="utf-8", newline="\n") as f:
    for d in dom_sorted:
        f.write(f"0.0.0.0 {d}\n")

with open(BUILD / "unified-adblock.txt", "w", encoding="utf-8", newline="\n") as f:
    for d in dom_sorted:
        f.write(f"||{d}^\n")

with open(BUILD / "unified-adguard.txt", "w", encoding="utf-8", newline="\n") as f:
    for d in dom_sorted:
        f.write(f"||{d}^\n")

with open(BUILD / "dnsmasq.conf", "w", encoding="utf-8", newline="\n") as f:
    for d in dom_sorted:
        f.write(f"address=/{d}/0.0.0.0\n")

with open(BUILD / "unbound.conf", "w", encoding="utf-8", newline="\n") as f:
    f.write("server:\n")
    for d in dom_sorted:
        f.write(f'  local-zone: "{d}" always_nxdomain\n')

targets = [
    "domains.txt",
    "unified-adblock.txt",
    "unified-adguard.txt",
    "technitium-domains.txt",
    "technitium-hosts.txt",
    "pihole-hosts.txt",
    "dnsmasq.conf",
    "unbound.conf",
]

with open(BUILD / "SHA256SUMS", "w", encoding="utf-8", newline="\n") as sums:
    for name in targets:
        p = BUILD / name
        if p.exists():
            sums.write(f"{sha256sum(p)}  {name}\n")

print(f"Repo base: {BASE}")
print(f"Domains (final): {len(dom_sorted)}")
print(f"Whitelisted (rules): {len(whitelist)}")
print(f"Blacklisted extra (rules): {len(blacklist)}")
print("Stats:")
for k, v in stats.items():
    print(f"  {k}: {v}")
