import re
import urllib.request
from datetime import date, timedelta
from pathlib import Path

BASIS = "https://laren.bestuurlijkeinformatie.nl"

CATEGORIEEN = {
    "Raadsvergadering": "/Calendar/OpenCategory/10002003",
    "Commissie R&I": "/Calendar/OpenCategory/10002008",
    "Commissie M&F": "/Calendar/OpenCategory/10002007",
}

# Tijdvenster: afgelopen 75 dagen t/m komende 90 dagen.
VANAF = date.today() - timedelta(days=75)
TOT = date.today() + timedelta(days=90)

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


def volledige_url(url):
    url = url.replace("&amp;", "&")
    return url if url.startswith("http") else BASIS + url


def vind_links(html, patroon):
    resultaat, gezien = [], set()
    # Pas 1: link mét bijbehorende tekst (mooie bestandsnamen).
    for m in re.finditer(r'href=["\']([^"\']+)["\'][^>]>(.?)</a>', html, re.S):
        url = m.group(1)
        if patroon in url and url not in gezien:
            tekst = re.sub(r"<[^>]+>", "", m.group(2))
            tekst = re.sub(r"\s+", " ", tekst).strip()
            resultaat.append((volledige_url(url), tekst or url))
            gezien.add(url)
    # Pas 2: vangnet - alle overige links met dit patroon (url als naam).
    for m in re.finditer(r'href=["\']([^"\']+)["\']', html):
        url = m.group(1)
        if patroon in url and url not in gezien:
            resultaat.append((volledige_url(url), url))
            gezien.add(url)
    return resultaat


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


regels = [f"# Vergaderstukken Laren - opgehaald op {date.today()}", ""]
aantal = 0

for naam, pad in CATEGORIEEN.items():
    try:
        eind_url, pagina = haal_pagina(BASIS + pad)
    except Exception as fout:
        regels += [f"## {naam}", f"Kon onderdeel niet ophalen: {fout}", ""]
        continue

    te_doen = {}
    for url, tekst in vind_links(pagina, "/Agenda/Index/"):
        d = lees_datum(tekst)
        if d and VANAF <= d <= TOT:
            te_doen[url] = f"{naam} - {tekst}"
    if eind_url not in te_doen:
        te_doen[eind_url] = f"{naam} - eerstvolgende vergadering"

    for url, label in te_doen.items():
        aantal += 1
        regels += [f"## {label}", f"[Agenda openen]({url})", ""]
        try:
            _, agenda = haal_pagina(url)
        except Exception as fout:
            regels += [f"Kon agenda niet ophalen: {fout}", ""]
            continue
        documenten = vind_links(agenda, "/Agenda/Document/")
        if documenten:
            for doc_url, doc_tekst in documenten:
                regels.append(f"- [{doc_tekst}]({doc_url})")
        else:
            regels.append("Nog geen documenten gepubliceerd.")
        regels.append("")

if aantal == 0:
    regels.append("Geen vergaderingen gevonden in het tijdvenster.")

Path("overzicht.md").write_text("\n".join(regels), encoding="utf-8")
print("Klaar. Aantal vergaderingen verwerkt:", aantal)
