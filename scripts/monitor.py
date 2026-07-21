import re
import urllib.request
from datetime import date
from pathlib import Path

BASIS = "https://laren.bestuurlijkeinformatie.nl"

# TEST: vaste set junivergaderingen 2026 (echte, gevulde agenda's).
VERGADERINGEN = {
    "Raadsvergadering 3 juni 2026":
        "/Agenda/Index/e367e587-f980-496a-b166-857485b55527",
    "Commissie R&I 10 juni 2026":
        "/Agenda/Index/7901ac75-d0fc-410f-ad19-3ab7595d4c64",
    "Commissie M&F 17 juni 2026":
        "/Agenda/Index/ad4efda1-447c-492a-9e83-aa6246d576f6",
    "Raadsvergadering 24 juni 2026":
        "/Agenda/Index/60e6e881-d2b4-424c-97b7-dfbc6f3221ac",
}

KOP = {"User-Agent": "Mozilla/5.0 (monitor vergaderstukken Laren)"}


def haal_pagina(url):
    verzoek = urllib.request.Request(url, headers=KOP)
    with urllib.request.urlopen(verzoek, timeout=60) as antwoord:
        return antwoord.read().decode("utf-8", errors="replace")


def schoon_tekst(tekst):
    tekst = re.sub(r"<[^>]+>", "", tekst)
    tekst = tekst.replace("&amp;", "&").replace("&nbsp;", " ").replace("\xa0", " ")
    return re.sub(r"\s+", " ", tekst).strip()


def zonder_bestandsgrootte(titel):
    return re.sub(r"\s+\d+(?:[.,]\d+)?\s*(?:bytes?|[kKmMgG]B)\s*$", "", titel).strip()


def titel_voor_link(html, pos):
    stuk = html[max(0, pos - 600):pos]
    for frag in reversed(re.split(r"<[^>]+>", stuk)):
        frag = schoon_tekst(frag)
        if len(frag) >= 5 and not re.fullmatch(r"[\d.,]+\s?[kKmMgG]?B", frag):
            return zonder_bestandsgrootte(frag)
    return None


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
        resultaat.append((titel, f"{BASIS}/Document/View/{docid}"))
    return resultaat


regels = [f"# TEST juni 2026 - Vergaderstukken Laren ({date.today()})", ""]

for naam, pad in VERGADERINGEN.items():
    regels += [f"## {naam}", f"[Agenda op het portaal]({BASIS + pad})", ""]
    try:
        html = haal_pagina(BASIS + pad)
    except Exception as fout:
        regels += [f"Kon niet ophalen: {fout}", ""]
        continue
    documenten = vind_documenten(html)
    if not documenten:
        regels.append("Geen documenten gevonden.")
    for titel, leeslink in documenten:
        regels.append(f"- [{titel}]({leeslink})")
    regels.append("")

Path("overzicht.md").write_text("\n".join(regels), encoding="utf-8")
print("Klaar.")
