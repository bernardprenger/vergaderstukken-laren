import re
import json
import urllib.request
from datetime import date
from pathlib import Path

BASIS = "https://laren.bestuurlijkeinformatie.nl"

CATEGORIEEN = {
    "Raadsvergadering": "/Calendar/OpenCategory/10002003",
    "Commissie R&I": "/Calendar/OpenCategory/10002008",
    "Commissie M&F": "/Calendar/OpenCategory/10002007",
}

MAANDEN = {
    "januari": 1, "februari": 2, "maart": 3, "april": 4, "mei": 5, "juni": 6,
    "juli": 7, "augustus": 8, "september": 9, "oktober": 10,
    "november": 11, "december": 12,
}

KOP = {"User-Agent": "Mozilla/5.0 (monitor vergaderstukken Laren)"}


def haal_pagina(url):
    verzoek = urllib.request.Request(url, headers=KOP)
    with urllib.request.urlopen(verzoek, timeout=60) as antwoord:
        return antwoord.geturl(), antwoord.read().decode("utf-8", errors="replace")


def schoon_tekst(tekst):
    tekst = re.sub(r"<[^>]+>", "", tekst)
    tekst = tekst.replace("&amp;", "&").replace("&nbsp;", " ").replace("\xa0", " ")
    return re.sub(r"\s+", " ", tekst).strip()


def zonder_bestandsgrootte(titel):
    return re.sub(r"\s+\d+(?:[.,]\d+)?\s*(?:bytes?|[kKmMgG]B)\s*$", "", titel).strip()


def lees_datum(tekst):
    m = re.search(r"(\d{1,2})\s+([a-z]+)\s+(\d{4})", tekst.lower())
    if not m:
        return None
    maand = MAANDEN.get(m.group(2))
    if not maand:
        return None
    try:
        return date(int(m.group(3)), maand, int(m.group(1)))
    except ValueError:
        return None


def haal_titel(html):
    m = re.search(r"<title>(.*?)</title>", html, re.S | re.I)
    if not m:
        return ""
    return re.split(r"(?i)\s*[-|]\s*iBabs", schoon_tekst(m.group(1)))[0].strip()


def titel_voor_link(html, pos):
    # de titel staat vlak vóór de link (de link zelf bevat alleen een icoon)
    stuk = html[max(0, pos - 600):pos]
    for frag in reversed(re.split(r"<[^>]+>", stuk)):
        frag = schoon_tekst(frag)
        if len(frag) >= 5 and not re.fullmatch(r"[\d.,]+\s?[kKmMgG]?B", frag):
            return zonder_bestandsgrootte(frag)
    return None


def kies_vergadering(start_url):
    # OpenCategory primair; ligt die in het verleden terwijl er latere staan,
    # pak dan de eerstvolgende toekomstige vergadering.
    eind_url, html = haal_pagina(start_url)
    d = lees_datum(haal_titel(html))
    if d and d >= date.today():
        return eind_url, html
    kandidaten = []
    for m in re.finditer(
        r'href=["\']([^"\']?/Agenda/Index/[^"\']+)["\'][^>]>(.*?)</a>', html, re.S
    ):
        dd = lees_datum(schoon_tekst(m.group(2)))
        if dd and dd >= date.today():
            url = m.group(1)
            kandidaten.append((dd, url if url.startswith("http") else BASIS + url))
    if kandidaten:
        return haal_pagina(sorted(kandidaten)[0][1])
    return eind_url, html


def vind_documenten(html):
    resultaat, gezien = [], set()
    for m in re.finditer(r'href=["\']([^"\']+)["\']', html):
        url = m.group(1)
        if "/Agenda/Document/" not in url:
            continue
        dm = re.search(r"documentId=([0-9a-fA-F-]+)", url)
        if not dm or dm.group(1) in gezien:
            continue
        docid = dm.group(1)
        gezien.add(docid)
        titel = titel_voor_link(html, m.start()) or "Document"
        resultaat.append((docid, titel, f"{BASIS}/Document/View/{docid}"))
    return resultaat


def leeslink_ok(url):
    # licht: alleen de eerste bytes; geeft een bestand terug, geen HTML-pagina?
    try:
        verzoek = urllib.request.Request(url, headers={**KOP, "Range": "bytes=0-1023"})
        with urllib.request.urlopen(verzoek, timeout=20) as antwoord:
            ct = (antwoord.headers.get("Content-Type") or "").lower()
            antwoord.read(16)
    except Exception:
        return None            # onbekend -> geen waarschuwing tonen
    return "text/html" not in ct


# vorige staat inlezen; alleen het nieuwe formaat (per onderdeel) overnemen
try:
    ruw = json.loads(Path("state.json").read_text(encoding="utf-8"))
    vorige = {k: v for k, v in ruw.items() if isinstance(v, dict)}
except Exception:
    vorige = {}

nieuwe_staat = dict(vorige)          # begin met de oude staat, vervang per onderdeel
regels = [f"# Vergaderstukken Laren - opgehaald op {date.today()}", ""]

for onderdeel, pad in CATEGORIEEN.items():
    try:
        eind_url, pagina = kies_vergadering(BASIS + pad)
        documenten = vind_documenten(pagina)
    except Exception as fout:
        regels += [f"## {onderdeel}",
                   f"Kon niet ophalen: {fout} (vorige stand behouden)", ""]
        continue

    titel = haal_titel(pagina)
    kop = f"{onderdeel} - {titel}" if titel else f"{onderdeel} - eerstvolgende vergadering"
    regels += [f"## {kop}", f"[Agenda op het portaal]({eind_url})", ""]

    oud = vorige.get(onderdeel, {})
    huidig = {}
    if not documenten:
        regels.append("Nog geen documenten gepubliceerd.")
    for docid, doc_titel, leeslink in documenten:
        huidig[docid] = doc_titel
        nieuw = " *(nieuw)*" if oud and docid not in oud else ""
        waarschuwing = " ⚠️ niet bereikbaar" if leeslink_ok(leeslink) is False else ""
        regels.append(f"- [{doc_titel}]({leeslink}){nieuw}{waarschuwing}")
    regels.append("")
    nieuwe_staat[onderdeel] = huidig      # alleen bij succes vervangen

Path("overzicht.md").write_text("\n".join(regels), encoding="utf-8")
Path("state.json").write_text(
    json.dumps(nieuwe_staat, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("Klaar.")
