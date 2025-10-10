# mikrotik-adlists

Lista de bloqueo unificado para DNS de MikroTik  
(Repositorio por dagorret) 0

## Descripción

Este proyecto centraliza listas de dominios (blacklist, whitelist, fuentes) y las prepara para uso con MikroTik mediante su funcionalidad **DNS AdList** o mediante importación a `static-regexp` DNS.  
Puede servir como fuente confiable de dominios maliciosos, de publicidad o indeseados que quieras bloquear desde tu router MikroTik.

## Estructura del repositorio

- `blacklist.txt` — lista principal de dominios que se pretende bloquear.  
- `whitelist.txt` — dominios permitidos (“excepciones”) que no deben bloquearse.  
- `sources.txt` — URLs / fuentes originales desde donde se recopilan dominios.  
- `.github/workflows/...` — scripts o acciones automatizadas (CI/CD) para renovar las listas o verificar su estado.  
- `README.md` — este documento.  
- `LICENSE` — licencia bajo BSL-1.0 (Business Source License) 1  

## Características / ventajas

- Listas ya limpias (duplica, comentarios, formato) listas para usar en MikroTik.  
- Separación entre lista negra (“blacklist”) y lista blanca (“whitelist”) para facilitar excepciones.  
- Origen centralizado: las fuentes están documentadas y pueden actualizarse.  
- Compatible con la funcionalidad DNS AdList desde RouterOS 7+.  
- Puede ser importada mediante script a `dns static` en routers que no soporten AdList.

## Uso recomendado / ejemplos

### 1. Usarlo directamente como AdList (RouterOS 7+)

```shell
/ip dns set cache-size=40000  # aumentar cache según el tamaño de las listas

/ip dns adlist add url=https://raw.githubusercontent.com/dagorret/mikrotik-adlists/refs/heads/main/build/unified-domains.txt ssl-verify=no
