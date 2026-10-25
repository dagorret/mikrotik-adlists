# 🧱 mikrotik-adlists — Blocklists unificadas para múltiples sistemas

[![Build Status](https://github.com/dagorret/mikrotik-adlists/actions/workflows/build.yml/badge.svg)](https://github.com/dagorret/mikrotik-adlists/actions)
[![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-online-brightgreen)](https://dagorret.github.io/mikrotik-adlists/)
[![Release](https://img.shields.io/github/v/release/dagorret/mikrotik-adlists?label=Última%20versión)](https://github.com/dagorret/mikrotik-adlists/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Maintainer](https://img.shields.io/badge/Maintainer-Carlos%20Dagorret-blue)](https://Dagorret.com.ar)

Listas de dominios y hosts generadas automáticamente cada 12 horas a partir de múltiples fuentes públicas.  
Compatibles con **AdBlock / uBlock Origin**, **AdGuard**, **Technitium DNS Server**, **Pi-hole / dnsmasq**, y **Unbound / BIND**.

> Proyecto mantenido por **[Carlos Dagorret](https://Dagorret.com.ar)**  
> Actualización automática mediante GitHub Actions y distribución vía GitHub Pages y Releases.

---

## 📦 Formatos generados

| Sistema / Software | Archivo | Formato | Ejemplo de línea |
|--------------------|----------|----------|------------------|
| AdBlock / uBlock | `unified-adblock.txt` | `||dominio^` | `||tracking.example.com^` |
| AdGuard | `unified-adguard.txt` | `||dominio^` | `||ads.example.net^` |
| Technitium DNS | `technitium-domains.txt` | `dominio` | `tracking.example.com` |
| Technitium DNS (hosts) | `technitium-hosts.txt` | `0.0.0.0 dominio` | `0.0.0.0 ads.example.net` |
| Pi-hole / dnsmasq | `pihole-hosts.txt` o `dnsmasq.conf` | `0.0.0.0 dominio` / `address=/dominio/0.0.0.0` | `address=/metrics.site.net/0.0.0.0` |
| Unbound / BIND RPZ | `unbound.conf` | `local-zone: "dominio" always_nxdomain` | `local-zone: "ads.example.org" always_nxdomain` |
| Base limpia | `domains.txt` | dominio simple | `example.com` |

---

## 🔄 Actualización automática

- Frecuencia: **cada 12 horas**
- Pipeline: GitHub Actions
- Validación: limpieza de dominios inválidos, aplicación de whitelist/blacklist, deduplicado
- Publicación:
  - **GitHub Releases** → URLs permanentes por tag (`daily-YYYYMMDD`)
  - **GitHub Pages** → Última versión accesible desde navegador o bloqueadores

---

## 🌐 Acceso rápido (GitHub Pages)

> URL base:  
> [https://dagorret.github.io/mikrotik-adlists/](https://dagorret.github.io/mikrotik-adlists/)

| Sistema | Enlace directo |
|----------|----------------|
| AdBlock / uBlock | [unified-adblock.txt](https://dagorret.github.io/mikrotik-adlists/unified-adblock.txt) |
| AdGuard | [unified-adguard.txt](https://dagorret.github.io/mikrotik-adlists/unified-adguard.txt) |
| Technitium DNS (simple) | [technitium-domains.txt](https://dagorret.github.io/mikrotik-adlists/technitium-domains.txt) |
| Technitium DNS (hosts) | [technitium-hosts.txt](https://dagorret.github.io/mikrotik-adlists/technitium-hosts.txt) |
| Pi-hole | [pihole-hosts.txt](https://dagorret.github.io/mikrotik-adlists/pihole-hosts.txt) |
| dnsmasq | [dnsmasq.conf](https://dagorret.github.io/mikrotik-adlists/dnsmasq.conf) |
| Unbound / BIND | [unbound.conf](https://dagorret.github.io/mikrotik-adlists/unbound.conf) |

---

## ⚙️ Ejemplos de uso por sistema

### 🧩 AdBlock / uBlock Origin
1. En la extensión: *Dashboard → My Filters → Import → Add a filter list*
2. URL:
   ```
   https://dagorret.github.io/mikrotik-adlists/unified-adblock.txt
   ```

### 🛡️ AdGuard Home
1. *Settings → Filters → DNS Blocklists → Add blocklist*
2. URL:
   ```
   https://dagorret.github.io/mikrotik-adlists/unified-adguard.txt
   ```

### 🧠 Technitium DNS Server
1. *Settings → Blocking → Block List URLs → Add*
2. URLs recomendadas:
   ```
   https://dagorret.github.io/mikrotik-adlists/technitium-domains.txt
   ```
   o
   ```
   https://dagorret.github.io/mikrotik-adlists/technitium-hosts.txt
   ```
3. Guardar y presionar “Update Block Lists”.

### 💡 Pi-hole
1. *Admin → Group Management → Adlists → Add*
2. Pegar la URL:
   ```
   https://dagorret.github.io/mikrotik-adlists/pihole-hosts.txt
   ```
3. Actualizar con:
   ```
   pihole -g
   ```

### ⚙️ dnsmasq / OpenWRT
1. Editá `/etc/dnsmasq.conf`:
   ```
   conf-file=/etc/dnsmasq.d/blocklist.conf
   ```
2. Descargá la lista:
   ```
   curl -o /etc/dnsmasq.d/blocklist.conf https://dagorret.github.io/mikrotik-adlists/dnsmasq.conf
   ```

### 🔒 Unbound / BIND
1. Agregá al final de `unbound.conf`:
   ```
   include: /etc/unbound/blocklist.conf
   ```
2. Descargá la lista:
   ```
   curl -o /etc/unbound/blocklist.conf https://dagorret.github.io/mikrotik-adlists/unbound.conf
   ```
3. Reiniciá Unbound.

---

## 🧾 Verificación de integridad

```
curl -s https://dagorret.github.io/mikrotik-adlists/SHA256SUMS | sha256sum -c -
```

---

## 🧰 Cómo funciona el sistema de build

- El repositorio usa **GitHub Actions** para construir automáticamente las listas cada 12 horas.
- Las fuentes están definidas en `sources.txt` (una por línea).
- Durante el build:
  1. Se descargan todas las listas desde las URLs indicadas.
  2. Se limpian entradas inválidas y duplicadas.
  3. Se aplica `whitelist.txt` y `blacklist.txt` (si existen).
  4. Se generan los archivos específicos para cada ecosistema.
  5. Se publica automáticamente en **GitHub Pages** y en un **Release** con tag diario (`daily-YYYYMMDD`).
- Todos los artefactos se validan con **SHA256SUMS**.

---

## 📘 Cómo usar los Releases diarios

También podés usar versiones fijas (inmutables) de cada lista desde los *Releases*:

```
https://github.com/dagorret/mikrotik-adlists/releases/download/daily-YYYYMMDD/technitium-domains.txt
```

> Sustituí `YYYYMMDD` por la fecha del release más reciente.

---

## 🧑‍💻 Autor

**Carlos Dagorret**  
🌐 [https://Dagorret.com.ar](https://Dagorret.com.ar)  
📬 [https://github.com/dagorret](https://github.com/dagorret)

---

## ⚖️ Licencia

Distribuido bajo licencia **MIT**.  
Las fuentes externas mantienen sus licencias originales.  
El contenido se provee *tal cual*, sin garantía de exactitud ni completitud.

---

## ❤️ Contribuir

1. Fork del repositorio  
2. Editá `sources.txt` (añadí o eliminá listas)  
3. Enviá un Pull Request con una descripción clara  
4. El sistema reconstruirá automáticamente todas las variantes al aprobarse el PR.

---

## 📅 Frecuencia y monitoreo

- Construcción automática: **cada 12 horas**
- Último commit visible en [GitHub Actions](https://github.com/dagorret/mikrotik-adlists/actions)
- Publicación automática en:
  - [GitHub Pages](https://dagorret.github.io/mikrotik-adlists/)
  - [GitHub Releases](https://github.com/dagorret/mikrotik-adlists/releases)

---

**Última actualización:** generada automáticamente cada 12 horas mediante GitHub Actions  
© 2025 [Carlos Dagorret](https://Dagorret.com.ar)
