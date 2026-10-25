#!/usr/bin/env python3
import re
import hashlib
from pathlib import Path
import idna

# =========================
# Base paths
# =========================
BASE = Path(__file__).resolve().parents[1]

RAW = BASE / "tmp" / "raw.txt"
BUILD = BASE / "build"
BUILD.mkdir(parents=True, exist_ok=True)

WHITELIST_FILE = BASE / "whitelist.txt"
BLACKLIST_FILE = BASE / "blacklist.txt"

HOST_PREFIXES = ("0.0.0.0 ", "127.0.0.1 ", ":: ", "::1 ")
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
    if s.startswith("@@||"):
        s = s[4:]
    elif s.startswith("||"):
        s = s[2:]
    else:
        return None

    if "^" in s:
        s = s.split("^", 1)[0]
    if "$" in s:
        s = s.split("$", 1)[0]

    s = s.strip()
    if not s or "/" in s or "*" in s:
        return None

    return s

def to_domain(line: str, *, update_stats: bool = True):
    s = line.strip().lower()
    s = s.lstrip("\ufeff").replace("\r", "")

    if update_stats:
        stats["total_lines"] += 1

    if not s or s.startswith("#") or s.startswith("!"):
        if update_stats:
            stats["empty_or_comment"] += 1
        return None

    for p in HOST_PREFIXES:
        if s.startswith(p):
            s = s[len(p):].strip()
            s = s.split()[0] if s else ""
            break

    if " #" in s:
        s = s.split(" #", 1)[0].strip()

    s = s.strip(" <>")

    if s.startswith("*."):
        s = s[2:]

    if s.endswith("."):
        s = s[:-1]

    if s.startswith(("http://", "https://")) or "://" in s or "/" in s:
        if update_stats:
            stats["urls"] += 1
        return None

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

    if s.startswith(("##", "#@#", "@@")):
        if update_stats:
            stats["adblock_rules_skipped"] += 1
        return None

    if s.startswith("."):
        if update_stats:
            stats["invalid_domain"] += 1
        return None

    if re.fullmatch(r"\d+\.\d+\.\d+\.\d+", s):
        if update_stats:
            stats["ips"] += 1
        return None

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

def is_whitelisted(domain: str, whitelist_set: set) -> bool:
    """Comprobación de subdominios en O(k) basada en jerarquía de etiquetas."""
    if domain in whitelist_set:
        return True
    parts = domain.split(".")
    for i in range(1, len(parts) - 1):
        parent = ".".join(parts[i:])
        if parent in whitelist_set:
            return True
    return False

def sha256sum(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

# =========================
# Carga de Whitelist y Blacklist
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
# Procesamiento Principal
# =========================
if not RAW.exists():
    raise SystemExit(f"ERROR: No se encontró el archivo de origen {RAW}")

domains = set()
with RAW.open(encoding="utf-8", errors="ignore") as fh:
    for line in fh:
        d = to_domain(line, update_stats=True)
        if d:
            domains.add(d)

domains |= blacklist

if whitelist:
    domains = {d for d in domains if not is_whitelisted(d, whitelist)}

dom_sorted = sorted(domains)

# =========================
# Escritura Eficiente de Salidas
# =========================
out_files = [
    "domains.txt",
    "technitium-domains.txt",
    "pihole-hosts.txt",
    "technitium-hosts.txt",
    "unified-adblock.txt",
    "unified-adguard.txt",
    "dnsmasq.conf",
    "unbound.conf",
]

handles = {name: open(BUILD / name, "w", encoding="utf-8", newline="\n") for name in out_files}
handles["unbound.conf"].write("server:\n")

for d in dom_sorted:
    handles["domains.txt"].write(f"{d}\n")
    handles["technitium-domains.txt"].write(f"{d}\n")
    handles["pihole-hosts.txt"].write(f"0.0.0.0 {d}\n")
    handles["technitium-hosts.txt"].write(f"0.0.0.0 {d}\n")
    handles["unified-adblock.txt"].write(f"||{d}^\n")
    handles["unified-adguard.txt"].write(f"||{d}^\n")
    handles["dnsmasq.conf"].write(f"address=/{d}/0.0.0.0\n")
    handles["unbound.conf"].write(f'  local-zone: "{d}" always_nxdomain\n')

for h in handles.values():
    h.close()

with open(BUILD / "SHA256SUMS", "w", encoding="utf-8", newline="\n") as sums:
    for name in out_files:
        p = BUILD / name
        if p.exists():
            sums.write(f"{sha256sum(p)}  {name}\n")

print(f"Repo base: {BASE}")
print(f"Dominios finales: {len(dom_sorted)}")
print(f"Reglas en Whitelist: {len(whitelist)}")
print(f"Reglas en Blacklist extra: {len(blacklist)}")
print("Estadísticas:")
for k, v in stats.items():
    print(f"  {k}: {v}")
