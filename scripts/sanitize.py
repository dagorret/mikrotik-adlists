# scripts/sanitize.py
import re, hashlib
from pathlib import Path
import idna

RAW = Path("tmp/raw.txt")
BUILD = Path("build")
BUILD.mkdir(parents=True, exist_ok=True)

HOST_PREFIXES = ("0.0.0.0 ", "127.0.0.1 ", ":: ", "::1 ")
ADBLOCK_TOKENS = ("||", "^", "*", "@@", "[", "]", "/", "##", "#@#")
DOMAIN_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)+$")

def to_domain(line: str):
    s = line.strip().lower()
    s = s.lstrip("\ufeff").replace("\r", "")
    if not s or s.startswith("#"):
        return None

    # hosts -> drop leading address
    for p in HOST_PREFIXES:
        if s.startswith(p):
            s = s[len(p):].strip()
            s = s.split()[0] if s else ""
            break

    # inline comment
    if " #" in s:
        s = s.split(" #", 1)[0].strip()

    # reject URLs/paths
    if s.startswith(("http://", "https://")) or "://" in s or "/" in s:
        return None

    # reject adblock/regex tokens
    if any(tok in s for tok in ADBLOCK_TOKENS):
        return None

    # reject wildcards or leading/trailing dots
    if s.startswith((".", "*")) or s.endswith((".", "*")):
        return None

    s = s.strip(" <>")

    # reject IPv4
    if re.fullmatch(r"\d+\.\d+\.\d+\.\d+", s):
        return None

    # IDN -> punycode
    try:
        s = idna.encode(s).decode("ascii")
    except Exception:
        return None

    # conservative FQDN check
    if not DOMAIN_RE.fullmatch(s) or len(s) > 253:
        return None

    return s

raw_lines = RAW.read_text(encoding="utf-8", errors="ignore").splitlines()
domains = set()
for line in raw_lines:
    d = to_domain(line)
    if d:
        domains.add(d)

dom_sorted = sorted(domains)

# domain-only outputs
Path(BUILD / "domains.txt").write_text(
    "\n".join(dom_sorted) + ("\n" if dom_sorted else ""),
    encoding="utf-8"
)
Path(BUILD / "technitium-domains.txt").write_text(
    "\n".join(dom_sorted) + ("\n" if dom_sorted else ""),
    encoding="utf-8"
)

# hosts format
with open(BUILD / "pihole-hosts.txt", "w", encoding="utf-8", newline="\n") as f:
    for d in dom_sorted:
        f.write(f"0.0.0.0 {d}\n")
with open(BUILD / "technitium-hosts.txt", "w", encoding="utf-8", newline="\n") as f:
    for d in dom_sorted:
        f.write(f"0.0.0.0 {d}\n")

# adblock/adguard (not for MikroTik/Technitium)
with open(BUILD / "unified-adblock.txt", "w", encoding="utf-8", newline="\n") as f:
    for d in dom_sorted:
        f.write(f"||{d}^\n")
with open(BUILD / "unified-adguard.txt", "w", encoding="utf-8", newline="\n") as f:
    for d in dom_sorted:
        f.write(f"||{d}^\n")

# dns resolvers
with open(BUILD / "dnsmasq.conf", "w", encoding="utf-8", newline="\n") as f:
    for d in dom_sorted:
        f.write(f"address=/{d}/0.0.0.0\n")
with open(BUILD / "unbound.conf", "w", encoding="utf-8", newline="\n") as f:
    for d in dom_sorted:
        f.write(f'local-zone: "{d}" always_nxdomain\n')

# checksums
def sha256sum(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

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

print(f"Domains: {len(dom_sorted)}")
