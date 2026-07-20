import re
import urllib.request
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


def haal_titel(html):
    m = re.search(r"<title>(.*?)</title>", html, re.S | re.I)
    if not m:
        return ""
    t = re.sub(r"\s+", " ", m.group(1)).strip()
    return re.split(r"(?i)\s*[-|]\s*iBabs", t)[0].strip()


def titel_bij_link(html, pos):
    # laatste zinvolle tekst vlak vóór de link
    stuk = html[max(0, pos - 600):pos].replace("&amp;", "&")
    for frag in reversed(re.split(r"<[^>]+>", stuk)):
        frag = re.sub(r"\s+", " ", frag).strip()
        if len(frag) >= 5 and not re.fullmatch(r"[\d.,]+\s?[kKmMgG]?B", frag):
            return frag
    return None


def vind_documenten(html):
    # BEWEZEN manier: alleen op href zoeken (niet op volledige <a>...</a>)
    resultaat, gezien = [], set()
    for m in re.finditer(r'href=["\']([^"\']+)["\']', html):
        url = m.group(1)
        if "/Agenda/Document/" not in url:
            continue
        vol = volledige_url(url)
        if vol in gezien:
            continue
        gezien.add(vol)
        naam = titel_bij_link(html, m.start()) or "Document"
        resultaat.append((vol, naam))
    return resultaat


regels = [f"# Vergaderstukken Laren - opgehaald op {date.today()}", ""]
diagnose = ""

for onderdeel, pad in CATEGORIEEN.items():
    try:
        eind_url, pagina = haal_pagina(BASIS + pad)
    except Exception as fout:
        regels += [f"## {onderdeel}", f"Kon niet ophalen: {fout}", ""]
        continue

    titel = haal_titel(pagina)
    kop = f"{onderdeel} - {titel}" if titel else f"{onderdeel} - eerstvolgende vergadering"
    regels += [f"## {kop}", f"[Agenda openen]({eind_url})", ""]

    documenten = vind_documenten(pagina)
    if not documenten:
        regels += ["Nog geen documenten gepubliceerd.", ""]
        continue
    for doc_url, doc_naam in documenten:
        regels.append(f"- [{doc_naam}]({doc_url})")
    regels.append("")

    # bewaar eenmalig een stukje ruwe HTML rond de eerste documentlink
    if not diagnose:
        p = pagina.find("/Agenda/Document/")
        if p != -1:
            diagnose = pagina[max(0, p - 700):p + 200]

if diagnose:
    regels += [
        "---",
        "### technische info (negeer dit tenzij de titels niet kloppen)",
        "",
        diagnose,
        "",
    ]

Path("overzicht.md").write_text("\n".join(regels), encoding="utf-8")
print("Klaar.")
