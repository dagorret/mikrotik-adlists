#!/usr/bin/env python3
import re
import hashlib
from pathlib import Path
import idna

# =========================
# Config / Paths
# =========================
RAW = Path("tmp/raw.txt")
BUILD = Path("build")
BUILD.mkdir(parents=True, exist_ok=True)

# Ajuste fino (uno por línea)
WHITELIST_FILE = Path("whitelist.txt")   # siempre gana (precedencia)
BLACKLIST_FILE = Path("blacklist.txt")   # se suma aunque no esté en fuentes

# Prefijos de formato hosts
HOST_PREFIXES = ("0.0.0.0 ", "127.0.0.1 ", ":: ", "::1 ")

# Tokens típicos de reglas Adblock/AdGuard (entrada NO soportada)
# Nota: evitamos filtrar por '*' / '[' / ']' para no tirar falsos positivos.
ADBLOCK_PREFIXES = ("||", "@@", "##", "#@#")

# Regex de dominio "clásico" (sin '_').
DOMAIN_RE = re.compile(
    r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)+$"
)

# Métricas para debug
stats = {
    "total_lines": 0,
    "valid_domains": 0,
    "invalid_domain": 0,
    "adblock_rules": 0,
    "urls": 0,
    "ips": 0,
    "empty_or_comment": 0,
}


def to_domain(line: str, *, update_stats: bool = True):
    """
    Normaliza una línea y devuelve un dominio válido o None.

    Soporta entradas:
    - "example.com"
    - "*.example.com"            (se reduce a "example.com")
    - "example.com."             (quita trailing dot)
    - "0.0.0.0 example.com"      (hosts file)
    - "::1 example.com"          (hosts file)

    Descarta entradas:
    - URLs (http/https, con paths)
    - Reglas Adblock/AdGuard como entrada (no soportadas)
    - IPs
    """
    s = line.strip().lower()
    s = s.lstrip("\ufeff").replace("\r", "")

    if update_stats:
        stats["total_lines"] += 1

    if not s or s.startswith("#"):
        if update_stats:
            stats["empty_or_comment"] += 1
        return None

    # Formato hosts (0.0.0.0 dominio.com, etc.)
    for p in HOST_PREFIXES:
        if s.startswith(p):
            s = s[len(p):].strip()
            s = s.split()[0] if s else ""
            break

    # Comentarios al final tipo: dominio.com # comentario
    if " #" in s:
        s = s.split(" #", 1)[0].strip()

    # Quita posible basura de extremos
    s = s.strip(" <>")

    # Soporta comodín simple tipo "*.example.com" tratándolo como "example.com"
    if s.startswith("*."):
        s = s[2:]

    # Normaliza FQDN con trailing dot: "example.com." -> "example.com"
    if s.endswith("."):
        s = s[:-1]

    # URLs completas o con paths no las queremos
    if s.startswith(("http://", "https://")) or "://" in s or "/" in s:
        if update_stats:
            stats["urls"] += 1
        return None

    # Descarta reglas Adblock/AdGuard (entrada NO soportada)
    if s.startswith(ADBLOCK_PREFIXES):
        if update_stats:
            stats["adblock_rules"] += 1
        return None

    # No queremos dominios que empiecen con '.'
    if s.startswith("."):
        if update_stats:
            stats["invalid_domain"] += 1
        return None

    # Ignora IPs v4 puras
    if re.fullmatch(r"\d+\.\d+\.\d+\.\d+", s):
        if update_stats:
            stats["ips"] += 1
        return None

    # Normaliza a IDNA (soporta dominios IDN)
    try:
        s = idna.encode(s).decode("ascii")
    except Exception:
        if update_stats:
            stats["invalid_domain"] += 1
        return None

    # Valida dominio y longitud máxima
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
# Load allow/deny (ajuste fino)
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
domains = set()

if not RAW.exists():
    raise SystemExit(f"ERROR: missing {RAW}")

with RAW.open(encoding="utf-8", errors="ignore") as fh:
    for line in fh:
        d = to_domain(line, update_stats=True)
        if d:
            domains.add(d)

# 1) Sumar blacklist (ajuste fino)
if blacklist:
    domains |= blacklist

# 2) Aplicar whitelist (precedencia absoluta, por sufijo)
if whitelist:
    wl = sorted(whitelist, key=len, reverse=True)
    domains = {d for d in domains if not any(is_subdomain_or_same(d, w) for w in wl)}

dom_sorted = sorted(domains)

# =========================
# Outputs
# =========================
# Base limpia de dominios
(BUILD / "domains.txt").write_text(
    "\n".join(dom_sorted) + ("\n" if dom_sorted else ""),
    encoding="utf-8",
)

# Technitium domains
(BUILD / "technitium-domains.txt").write_text(
    "\n".join(dom_sorted) + ("\n" if dom_sorted else ""),
    encoding="utf-8",
)

# Hosts (Pi-hole, Technitium, etc.)
with open(BUILD / "pihole-hosts.txt", "w", encoding="utf-8", newline="\n") as f:
    for d in dom_sorted:
        f.write(f"0.0.0.0 {d}\n")

with open(BUILD / "technitium-hosts.txt", "w", encoding="utf-8", newline="\n") as f:
    for d in dom_sorted:
        f.write(f"0.0.0.0 {d}\n")

# AdBlock / AdGuard rules (salida)
with open(BUILD / "unified-adblock.txt", "w", encoding="utf-8", newline="\n") as f:
    for d in dom_sorted:
        f.write(f"||{d}^\n")

with open(BUILD / "unified-adguard.txt", "w", encoding="utf-8", newline="\n") as f:
    for d in dom_sorted:
        f.write(f"||{d}^\n")

# dnsmasq
with open(BUILD / "dnsmasq.conf", "w", encoding="utf-8", newline="\n") as f:
    for d in dom_sorted:
        f.write(f"address=/{d}/0.0.0.0\n")

# Unbound
# IMPORTANTE:
# - Este archivo se usa como "include" desde service.conf.
# - Para que sea válido en cualquier lugar, lo emitimos como un bloque completo "server:".
# - local-zone para "example.com" afecta también subdominios (www.example.com, a.b.example.com, etc.)
with open(BUILD / "unbound.conf", "w", encoding="utf-8", newline="\n") as f:
    f.write("server:\n")
    for d in dom_sorted:
        f.write(f'  local-zone: "{d}" always_nxdomain\n')

# =========================
# SHA256SUMS
# =========================
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

# =========================
# Logs
# =========================
print(f"Domains (final): {len(dom_sorted)}")
print(f"Whitelisted (rules): {len(whitelist)}")
print(f"Blacklisted extra (rules): {len(blacklist)}")
print("Stats:")
for k, v in stats.items():
    print(f"  {k}: {v}")
