import re
import urllib.request
from datetime import date
from pathlib import Path

BASIS = "https://laren.bestuurlijkeinformatie.nl"

# TEST: drie bekende vergaderingen van juni 2026 die documenten horen te hebben.
VERGADERINGEN = {
    "Raadsvergadering 3 juni 2026":
        "/Agenda/Index/e367e587-f980-496a-b166-857485b55527",
    "Commissie R&I 10 juni 2026":
        "/Agenda/Index/7901ac75-d0fc-410f-ad19-3ab7595d4c64",
    "Commissie M&F 17 juni 2026":
        "/Agenda/Index/ad4efda1-447c-492a-9e83-aa6246d576f6",
}

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
            tekst = re.sub(r"<[^>]+>", "", tekst)
            tekst = re.sub(r"\s+", " ", tekst).strip()
            resultaat.append((volledige_url(url), tekst))
    return resultaat


regels = [f"# TEST - Vergaderstukken Laren - {date.today()}", ""]

for naam, pad in VERGADERINGEN.items():
    regels += [f"## {naam}", f"[Agenda openen]({volledige_url(pad)})", ""]
    try:
        html = haal_pagina(volledige_url(pad))
    except Exception as fout:
        regels += [f"Kon pagina niet ophalen: {fout}", ""]
        continue
    documenten = vind_links(html, "/Agenda/Document/")
    regels.append(
        f"_(diagnose: pagina is {len(html)} tekens groot, "
        f"{len(documenten)} documentlinks gevonden)_"
    )
    for doc_url, doc_tekst in documenten:
        regels.append(f"- [{doc_tekst}]({doc_url})")
    regels.append("")

Path("overzicht.md").write_text("\n".join(regels), encoding="utf-8")
print("Klaar.")
