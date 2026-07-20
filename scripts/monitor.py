import re
import urllib.request
from datetime import date
from pathlib import Path

BASIS = "https://laren.bestuurlijkeinformatie.nl"

# Alleen vergaderingen waarvan de titel een van deze woorden bevat:
GEWENST = ["R&I", "M&F", "Raadsvergadering"]

KOP = {"User-Agent": "Mozilla/5.0 (monitor vergaderstukken Laren)"}


def haal_pagina(url):
    verzoek = urllib.request.Request(url, headers=KOP)
    with urllib.request.urlopen(verzoek, timeout=60) as antwoord:
        return antwoord.read().decode("utf-8", errors="replace")


def volledige_url(url):
    return url if url.startswith("http") else BASIS + url


def vind_links(html, patroon):
    resultaat = []
    for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]>(.?)</a>', html, re.S):
        url, tekst = m.group(1), m.group(2)
        if patroon in url:
            tekst = re.sub(r"<[^>]+>", "", tekst)      # html-code weghalen
            tekst = re.sub(r"\s+", " ", tekst).strip()  # witruimte opschonen
            resultaat.append((volledige_url(url), tekst))
    return resultaat


# 1. Kalender ophalen: welke vergaderingen zijn er?
kalender = haal_pagina(BASIS + "/Calendar")
vergaderingen = vind_links(kalender, "/Agenda/Index/")

# dubbele eruit, volgorde houden
gezien, uniek = set(), []
for url, tekst in vergaderingen:
    if url not in gezien:
        gezien.add(url)
        uniek.append((url, tekst))

regels = [f"# Vergaderstukken Laren - opgehaald op {date.today()}", ""]
aantal = 0

for url, tekst in uniek:
    if not any(w in tekst for w in GEWENST):
        continue
    aantal += 1
    regels += [f"## {tekst}", f"[Agenda openen]({url})", ""]
    try:
        agenda = haal_pagina(url)
    except Exception as fout:
        regels += [f"Kon agenda niet ophalen: {fout}", ""]
        continue
    documenten = vind_links(agenda, "/Agenda/Document/")
    if documenten:
        for doc_url, doc_tekst in documenten:
            regels.append(f"- [{doc_tekst}]({doc_url})")
    else:
        regels.append("Nog geen documenten gevonden.")
    regels.append("")

Path("overzicht.md").write_text("\n".join(regels), encoding="utf-8")
print("Klaar. Aantal relevante vergaderingen:", aantal)
