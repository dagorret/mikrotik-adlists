import re
import hashlib
from pathlib import Path
import idna

# Archivos de entrada / salida
RAW = Path("tmp/raw.txt")
BUILD = Path("build")
BUILD.mkdir(parents=True, exist_ok=True)

# Whitelist opcional (uno por línea, mismo formato que las listas de entrada)
WHITELIST_FILE = Path("whitelist.txt")

# Prefijos de formato hosts
HOST_PREFIXES = ("0.0.0.0 ", "127.0.0.1 ", ":: ", "::1 ")

# Tokens típicos de reglas Adblock/AdGuard que NO queremos tratar como dominios
ADBLOCK_TOKENS = ("||", "^", "*", "@@", "[", "]", "/", "##", "#@#")

# Regex de dominio "clásico" (sin '_').
# Si alguna vez querés permitir '_' en los labels, podés cambiar:
#   [a-z0-9-]  -->  [a-z0-9_-]
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
    Si update_stats es False, no modifica el contador de stats (útil para whitelist).
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

    # URLs completas o con paths no las queremos
    if s.startswith(("http://", "https://")) or "://" in s or "/" in s:
        if update_stats:
            stats["urls"] += 1
        return None

    # Descarta líneas que claramente son reglas Adblock/AdGuard
    if any(tok in s for tok in ADBLOCK_TOKENS):
        if update_stats:
            stats["adblock_rules"] += 1
        return None

    # No queremos dominios que empiecen o terminen con '.' o '*'
    if s.startswith((".", "*")) or s.endswith((".", "*")):
        if update_stats:
            stats["invalid_domain"] += 1
        return None

    # Quita posible basura de extremos
    s = s.strip(" <>")

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


def sha256sum(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------- Carga de whitelist ----------
whitelist = set()
if WHITELIST_FILE.exists():
    with WHITELIST_FILE.open(encoding="utf-8", errors="ignore") as wf:
        for line in wf:
            d = to_domain(line, update_stats=False)
            if d:
                whitelist.add(d)

# ---------- Procesamiento principal ----------
domains = set()

# Lectura en streaming (mejor para listas grandes)
with RAW.open(encoding="utf-8", errors="ignore") as fh:
    for line in fh:
        d = to_domain(line, update_stats=True)
        if d:
            domains.add(d)

# Aplica whitelist (dominios que NO queremos bloquear)
if whitelist:
    domains -= whitelist

dom_sorted = sorted(domains)

# ---------- Salidas ----------
# Listas de dominios
Path(BUILD / "domains.txt").write_text(
    "\n".join(dom_sorted) + ("\n" if dom_sorted else ""),
    encoding="utf-8",
)

Path(BUILD / "technitium-domains.txt").write_text(
    "\n".join(dom_sorted) + ("\n" if dom_sorted else ""),
    encoding="utf-8",
)

# Formato hosts (Pi-hole, Technitium, etc.)
with open(BUILD / "pihole-hosts.txt", "w", encoding="utf-8", newline="\n") as f:
    for d in dom_sorted:
        f.write(f"0.0.0.0 {d}\n")

with open(BUILD / "technitium-hosts.txt", "w", encoding="utf-8", newline="\n") as f:
    for d in dom_sorted:
        f.write(f"0.0.0.0 {d}\n")

# Formato Adblock / AdGuard
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
# Nota: estás usando always_nxdomain, que está bien.
# Si en algún momento querés diferenciar "bloqueado" de "no existe",
# podrías evaluar always_refuse, pero eso ya es una decisión de diseño.
with open(BUILD / "unbound.conf", "w", encoding="utf-8", newline="\n") as f:
    for d in dom_sorted:
        f.write(f'local-zone: "{d}" always_nxdomain\n')

# ---------- SHA256SUMS ----------
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

# ---------- Logs finales ----------
print(f"Domains (final, after whitelist): {len(dom_sorted)}")
print(f"Whitelisted domains: {len(whitelist)}")
print("Stats:")
for k, v in stats.items():
    print(f"  {k}: {v}")
