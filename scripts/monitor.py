import re
import urllib.request
from datetime import date
from pathlib import Path

BASIS = "https://laren.bestuurlijkeinformatie.nl"
PAD = "/Agenda/Index/7901ac75-d0fc-410f-ad19-3ab7595d4c64"  # R&I 10 juni 2026
KOP = {"User-Agent": "Mozilla/5.0 (monitor Laren)"}

verzoek = urllib.request.Request(BASIS + PAD, headers=KOP)
with urllib.request.urlopen(verzoek, timeout=60) as antwoord:
    html = antwoord.read().decode("utf-8", errors="replace")

regels = [f"# Diagnose R&I 10 juni - {date.today()}", ""]
regels.append(f"Paginagrootte: {len(html)} tekens")
regels.append("")

# Hoe vaak komen bepaalde woorden voor?
for woord in ["Agenda/Document", "Agenda/Index", "documentId",
              "downloadDocument", "ashx", "Bijlage", ".pdf", ".docx"]:
    regels.append(f"'{woord}' komt {html.count(woord)} keer voor")

# Alle href-waarden verzamelen (dubbele of enkele aanhalingstekens)
hrefs = re.findall(r'href=["\']([^"\']+)["\']', html)
regels.append("")
regels.append(f"Totaal aantal href-links: {len(hrefs)}")

# Links die met documenten te maken lijken te hebben
sleutels = ["ocument", "ownload", ".pdf", ".docx", "ashx", "File", "ijlage"]
doclinks = sorted({h for h in hrefs if any(s in h for s in sleutels)})
regels.append("")
regels.append(f"Mogelijke documentlinks ({len(doclinks)}):")
for h in doclinks[:30]:
    regels.append(f"- {h}")

# Eerste 30 unieke links, om het algemene patroon te zien
regels.append("")
regels.append("Eerste 30 unieke links:")
for h in sorted(set(hrefs))[:30]:
    regels.append(f"- {h}")

Path("overzicht.md").write_text("\n".join(regels), encoding="utf-8")
print("Klaar.")
