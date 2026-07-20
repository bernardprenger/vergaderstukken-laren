import re
import urllib.request
from urllib.parse import unquote
from datetime import date
from pathlib import Path

BASIS = "https://laren.bestuurlijkeinformatie.nl"

CATEGORIEEN = {
    "Raadsvergadering": "/Calendar/OpenCategory/10002003",
    "Commissie R&I": "/Calendar/OpenCategory/10002008",
    "Commissie M&F": "/Calendar/OpenCategory/10002007",
}

KOP = {"User-Agent": "Mozilla/5.0 (monitor vergaderstukken Laren)"}


def haal_pagina(url):
    verzoek = urllib.request.Request(url, headers=KOP)
    with urllib.request.urlopen(verzoek, timeout=60) as antwoord:
        return antwoord.geturl(), antwoord.read().decode("utf-8", errors="replace")


def volledige_url(url):
    url = url.replace("&amp;", "&")
    return url if url.startswith("http") else BASIS + url


def vind_documentlinks(html):
    urls, gezien = [], set()
    for m in re.finditer(r'href=["\']([^"\']+)["\']', html):
        url = m.group(1)
        if "/Agenda/Document/" in url and url not in gezien:
            gezien.add(url)
            urls.append(volledige_url(url))
    return urls


def haal_bestandsnaam(url):
    try:
        verzoek = urllib.request.Request(url, headers=KOP)
        with urllib.request.urlopen(verzoek, timeout=60) as antwoord:
            cd = antwoord.headers.get("Content-Disposition", "") or ""
    except Exception:
        return None
    m = re.search(r"filename\*=(?:UTF-8'')?([^;]+)", cd, re.I)
    if m:
        return unquote(m.group(1).strip().strip('"'))
    m = re.search(r'filename="?([^";]+)"?', cd, re.I)
    if m:
        return m.group(1).strip()
    return None


def haal_titel(html):
    m = re.search(r"<title>(.*?)</title>", html, re.S | re.I)
    if not m:
        return ""
    t = re.sub(r"\s+", " ", m.group(1)).strip()
    return re.split(r"(?i)\s*[-|]\s*iBabs", t)[0].strip()


regels = [f"# Vergaderstukken Laren - opgehaald op {date.today()}", ""]

for naam, pad in CATEGORIEEN.items():
    try:
        eind_url, pagina = haal_pagina(BASIS + pad)
    except Exception as fout:
        regels += [f"## {naam}", f"Kon niet ophalen: {fout}", ""]
        continue

    titel = haal_titel(pagina)
    kop = f"{naam} - {titel}" if titel else f"{naam} - eerstvolgende vergadering"
    regels += [f"## {kop}", f"[Agenda openen]({eind_url})", ""]

    documenten = vind_documentlinks(pagina)
    if not documenten:
        regels += ["Nog geen documenten gepubliceerd.", ""]
        continue

    for i, doc_url in enumerate(documenten, 1):
        naam_doc = haal_bestandsnaam(doc_url) or f"Document {i}"
        regels.append(f"- [{naam_doc}]({doc_url})")
    regels.append("")

Path("overzicht.md").write_text("\n".join(regels), encoding="utf-8")
print("Klaar.")
