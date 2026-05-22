"""
GynForum – Tilgjengelighetssjekk v2
=====================================
Henter mangel-status via Google-indeksert snuttekst fra Felleskatalogen,
som viser JS-rendret DMP-mangeltekst. Faller tilbake til manuell status
ved feil.

Kjøres ukentlig via GitHub Actions.
"""

import json
import re
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime
from zoneinfo import ZoneInfo

# Kjente statuser per preparat – oppdateres manuelt ved behov
# Automatisk sjekk vil overskrive disse hvis den finner ny info
KNOWN_STATUS = {
    "estradot":        {"has_shortage": True,  "dmp_status": "Pågående",         "dmp_status_date": "18.05.2026", "shortage_reason": "Produksjonsproblemer"},
    "estradiol_hexal": {"has_shortage": False, "dmp_status": "Ingen meldt mangel", "dmp_status_date": None, "shortage_reason": None},
    "estrogel":        {"has_shortage": False, "dmp_status": "Ingen meldt mangel", "dmp_status_date": None, "shortage_reason": None},
    "lenzetto":        {"has_shortage": True,  "dmp_status": "Pågående",         "dmp_status_date": "17.03.2026", "shortage_reason": "Kapasitetsutfordringer"},
    "progynova":       {"has_shortage": False, "dmp_status": "Ingen meldt mangel", "dmp_status_date": None, "shortage_reason": None},
    "vagifem":         {"has_shortage": False, "dmp_status": "Ingen meldt mangel", "dmp_status_date": None, "shortage_reason": None},
    "vagidonna":       {"has_shortage": False, "dmp_status": "Ingen meldt mangel", "dmp_status_date": None, "shortage_reason": None},
    "ovesterin":       {"has_shortage": False, "dmp_status": "Ingen meldt mangel", "dmp_status_date": None, "shortage_reason": None},
    "gelisse":         {"has_shortage": False, "dmp_status": "Ingen meldt mangel", "dmp_status_date": None, "shortage_reason": None},
    "gynoflor":        {"has_shortage": False, "dmp_status": "Ingen meldt mangel", "dmp_status_date": None, "shortage_reason": None},
}

PREPARATIONS = [
    {"id": "estradot",        "name": "Estradot",        "form": "Plaster",         "type": "systemisk",
     "fk_url": "https://www.felleskatalogen.no/medisin/estradot-sandoz-558818",
     "packages": [{"label": "25 µg/24t"},{"label": "37,5 µg/24t"},{"label": "50 µg/24t"},{"label": "75 µg/24t"},{"label": "100 µg/24t"}],
     "dmp_search": "Estradot",
     "apotek_links": {"Apotek 1":"https://www.apotek1.no/search?q=Estradot","Vitusapotek":"https://www.vitusapotek.no/sok?term=Estradot","Boots":"https://www.bootsapotek.no/search?q=Estradot","Farmasiet":"https://www.farmasiet.no/search?query=Estradot"}},
    {"id": "estradiol_hexal", "name": "Estradiol Hexal", "form": "Plaster",         "type": "systemisk",
     "fk_url": "https://www.felleskatalogen.no/medisin/estradiol-hexal-hexal-566040",
     "packages": [{"label": "25 µg/24t"},{"label": "37,5 µg/24t"},{"label": "50 µg/24t"},{"label": "75 µg/24t"},{"label": "100 µg/24t"}],
     "dmp_search": "Estradiol+Hexal",
     "apotek_links": {"Apotek 1":"https://www.apotek1.no/search?q=Estradiol+Hexal","Vitusapotek":"https://www.vitusapotek.no/sok?term=Estradiol+Hexal","Boots":"https://www.bootsapotek.no/search?q=Estradiol+Hexal","Farmasiet":"https://www.farmasiet.no/search?query=Estradiol+Hexal"}},
    {"id": "estrogel",        "name": "Estrogel",        "form": "Gel",             "type": "systemisk",
     "fk_url": "https://www.felleskatalogen.no/medisin/estrogel-besins-healthcare-norway-559089",
     "packages": [{"label": "0,06% gel pumpe"}],
     "dmp_search": "Estrogel",
     "apotek_links": {"Apotek 1":"https://www.apotek1.no/search?q=Estrogel","Vitusapotek":"https://www.vitusapotek.no/sok?term=Estrogel","Boots":"https://www.bootsapotek.no/search?q=Estrogel","Farmasiet":"https://www.farmasiet.no/search?query=Estrogel"}},
    {"id": "lenzetto",        "name": "Lenzetto",        "form": "Spray",           "type": "systemisk",
     "fk_url": "https://www.felleskatalogen.no/medisin/lenzetto-gedeon-richter-647011",
     "packages": [{"label": "1,53 mg/spray"}],
     "dmp_search": "Lenzetto",
     "apotek_links": {"Apotek 1":"https://www.apotek1.no/search?q=Lenzetto","Vitusapotek":"https://www.vitusapotek.no/sok?term=Lenzetto","Boots":"https://www.bootsapotek.no/search?q=Lenzetto","Farmasiet":"https://www.farmasiet.no/search?query=Lenzetto"}},
    {"id": "progynova",       "name": "Progynova",       "form": "Tablett",         "type": "systemisk",
     "fk_url": "https://www.felleskatalogen.no/medisin/progynova-bayer-559276",
     "packages": [{"label": "1 mg"},{"label": "2 mg"}],
     "dmp_search": "Progynova",
     "apotek_links": {"Apotek 1":"https://www.apotek1.no/search?q=Progynova","Vitusapotek":"https://www.vitusapotek.no/sok?term=Progynova","Boots":"https://www.bootsapotek.no/search?q=Progynova","Farmasiet":"https://www.farmasiet.no/search?query=Progynova"}},
    {"id": "vagifem",         "name": "Vagifem",         "form": "Vaginaltablett",  "type": "vaginal",
     "fk_url": "https://www.felleskatalogen.no/medisin/vagifem-novo-nordisk-559494",
     "packages": [{"label": "10 µg"}],
     "dmp_search": "Vagifem",
     "apotek_links": {"Apotek 1":"https://www.apotek1.no/search?q=Vagifem","Vitusapotek":"https://www.vitusapotek.no/sok?term=Vagifem","Boots":"https://www.bootsapotek.no/search?q=Vagifem","Farmasiet":"https://www.farmasiet.no/search?query=Vagifem"}},
    {"id": "vagidonna",       "name": "Vagidonna",       "form": "Vaginaltablett",  "type": "vaginal",
     "fk_url": "https://www.felleskatalogen.no/medisin/vagidonna-gedeon-richter-562743",
     "packages": [{"label": "10 µg"}],
     "dmp_search": "Vagidonna",
     "apotek_links": {"Apotek 1":"https://www.apotek1.no/search?q=Vagidonna","Vitusapotek":"https://www.vitusapotek.no/sok?term=Vagidonna","Boots":"https://www.bootsapotek.no/search?q=Vagidonna","Farmasiet":"https://www.farmasiet.no/search?query=Vagidonna"}},
    {"id": "ovesterin",       "name": "Ovesterin",       "form": "Vagitorier/krem", "type": "vaginal",
     "fk_url": "https://www.felleskatalogen.no/medisin/ovesterin-aspen-558989",
     "packages": [{"label": "0,5 mg vagitorier"},{"label": "0,1 mg/g krem"}],
     "dmp_search": "Ovesterin",
     "apotek_links": {"Apotek 1":"https://www.apotek1.no/search?q=Ovesterin","Vitusapotek":"https://www.vitusapotek.no/sok?term=Ovesterin","Boots":"https://www.bootsapotek.no/search?q=Ovesterin","Farmasiet":"https://www.farmasiet.no/search?query=Ovesterin"}},
    {"id": "gelisse",         "name": "Gelisse",         "form": "Vaginalgel",      "type": "vaginal",
     "fk_url": "https://www.felleskatalogen.no/medisin/gelisse-italfarmaco-562400",
     "packages": [{"label": "50 µg/g gel"}],
     "dmp_search": "Gelisse",
     "apotek_links": {"Apotek 1":"https://www.apotek1.no/search?q=Gelisse","Vitusapotek":"https://www.vitusapotek.no/sok?term=Gelisse","Boots":"https://www.bootsapotek.no/search?q=Gelisse","Farmasiet":"https://www.farmasiet.no/search?query=Gelisse"}},
    {"id": "gynoflor",        "name": "Gynoflor",        "form": "Vaginaltablett",  "type": "vaginal",
     "fk_url": "https://www.felleskatalogen.no/medisin/gynoflor-medinova-558914",
     "packages": [{"label": "0,03 mg + Lactobacillus"}],
     "dmp_search": "Gynoflor",
     "apotek_links": {"Apotek 1":"https://www.apotek1.no/search?q=Gynoflor","Vitusapotek":"https://www.vitusapotek.no/sok?term=Gynoflor","Boots":"https://www.bootsapotek.no/search?q=Gynoflor","Farmasiet":"https://www.farmasiet.no/search?query=Gynoflor"}},
]

DMP_BASE = "https://www.dmp.no/forsyningssikkerhet/legemiddelmangel/oversikt-over-legemiddelmangel---for-pasienter-og-helsepersonell"


def fetch_google_snippet(prep_name: str, fk_url: str) -> dict:
    """
    Søker Google etter [preparat site:felleskatalogen.no] og
    parser statussnutteksten fra søkeresultatet.
    Felleskatalogen-sider er indeksert med rendret JS-innhold.
    """
    query = urllib.parse.quote(f'{prep_name} mangel site:felleskatalogen.no')
    search_url = f"https://www.google.com/search?q={query}&hl=no&num=3"
    req = urllib.request.Request(
        search_url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; GynForum-Bot/2.0)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        # Look for status pattern in snippets
        m = re.search(r"Status\s+pr\.\s+(\d{2}\.\d{2}\.\d{4}):\s*(Pågående|Avsluttet)", html, re.IGNORECASE)
        if m:
            date, status = m.group(1), m.group(2)
            return {
                "has_shortage": status.lower() == "pågående",
                "dmp_status": status,
                "dmp_status_date": date,
                "shortage_reason": None,
                "shortage_period": None,
                "source": "google_snippet",
            }
    except Exception:
        pass
    return {}


def main():
    oslo = ZoneInfo("Europe/Oslo")
    now = datetime.now(oslo)
    print(f"\nGynForum tilgjengelighetssjekk v2 – {now.strftime('%d.%m.%Y %H:%M')}\n")

    results = []
    for prep in PREPARATIONS:
        pid = prep["id"]
        known = KNOWN_STATUS.get(pid, {})

        # Try live fetch first
        live = fetch_google_snippet(prep["name"], prep["fk_url"])
        status = {**known, **live} if live else known

        print(f"  {prep['name']:20s} {'⚠ MANGEL' if status.get('has_shortage') else '✓ OK':10s} "
              f"({status.get('dmp_status_date','?')}) "
              f"{'[live]' if live else '[kjent]'}")

        results.append({
            "id": pid,
            "name": prep["name"],
            "form": prep["form"],
            "type": prep["type"],
            "fk_url": prep["fk_url"],
            "packages": prep["packages"],
            "dmp_search_url": f"{DMP_BASE}?q={prep['dmp_search']}",
            "apotek_links": prep["apotek_links"],
            **{k: status.get(k) for k in ["has_shortage","dmp_status","dmp_status_date","shortage_period","shortage_reason"]},
        })

    with_shortage = [r for r in results if r["has_shortage"] is True]
    output = {
        "generated": now.isoformat(),
        "generated_display": now.strftime("%d.%m.%Y kl. %H:%M"),
        "source": "GynForum automatisk sjekk – Felleskatalogen/DMP",
        "dmp_overview_url": DMP_BASE,
        "summary": {
            "total": len(results),
            "with_shortage": len(with_shortage),
            "ok": len(results) - len(with_shortage),
            "unknown": 0,
        },
        "preparations": results,
    }

    with open("data/status.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✓ data/status.json oppdatert – {len(with_shortage)} med mangel")


if __name__ == "__main__":
    main()
