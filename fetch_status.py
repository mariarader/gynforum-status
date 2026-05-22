"""
GynForum – Tilgjengelighetssjekk v4
=====================================
Henter DMP-mangelstatus ved å søke Google med site:felleskatalogen.no.
Google-indeksen inneholder JS-rendret innhold inkl. "Status pr. DD.MM.ÅÅÅÅ: Pågående".
Ingen headless browser nødvendig – fungerer med ren urllib.
"""

import json
import re
import urllib.request
import urllib.parse
import time
from datetime import datetime
from zoneinfo import ZoneInfo

DMP_BASE = "https://www.dmp.no/forsyningssikkerhet/legemiddelmangel/oversikt-over-legemiddelmangel---for-pasienter-og-helsepersonell"

PREPARATIONS = [
    {"id": "estradot",        "name": "Estradot",        "form": "Plaster",         "type": "systemisk",
     "fk_url": "https://www.felleskatalogen.no/medisin/estradot-sandoz-558818",
     "packages": [{"label":"25 µg/24t"},{"label":"37,5 µg/24t"},{"label":"50 µg/24t"},{"label":"75 µg/24t"},{"label":"100 µg/24t"}],
     "dmp_search": "Estradot",
     "apotek_links": {"Apotek 1":"https://www.apotek1.no/search?q=Estradot","Vitusapotek":"https://www.vitusapotek.no/sok?term=Estradot","Boots":"https://www.bootsapotek.no/search?q=Estradot","Farmasiet":"https://www.farmasiet.no/search?query=Estradot"}},
    {"id": "estradiol_hexal", "name": "Estradiol Hexal", "form": "Plaster",         "type": "systemisk",
     "fk_url": "https://www.felleskatalogen.no/medisin/estradiol-hexal-hexal-566040",
     "packages": [{"label":"25 µg/24t"},{"label":"37,5 µg/24t"},{"label":"50 µg/24t"},{"label":"75 µg/24t"},{"label":"100 µg/24t"}],
     "dmp_search": "Estradiol+Hexal",
     "apotek_links": {"Apotek 1":"https://www.apotek1.no/search?q=Estradiol+Hexal","Vitusapotek":"https://www.vitusapotek.no/sok?term=Estradiol+Hexal","Boots":"https://www.bootsapotek.no/search?q=Estradiol+Hexal","Farmasiet":"https://www.farmasiet.no/search?query=Estradiol+Hexal"}},
    {"id": "estrogel",        "name": "Estrogel",        "form": "Gel",             "type": "systemisk",
     "fk_url": "https://www.felleskatalogen.no/medisin/estrogel-besins-healthcare-norway-559089",
     "packages": [{"label":"0,06% gel pumpe"}],
     "dmp_search": "Estrogel",
     "apotek_links": {"Apotek 1":"https://www.apotek1.no/search?q=Estrogel","Vitusapotek":"https://www.vitusapotek.no/sok?term=Estrogel","Boots":"https://www.bootsapotek.no/search?q=Estrogel","Farmasiet":"https://www.farmasiet.no/search?query=Estrogel"}},
    {"id": "lenzetto",        "name": "Lenzetto",        "form": "Spray",           "type": "systemisk",
     "fk_url": "https://www.felleskatalogen.no/medisin/lenzetto-gedeon-richter-647011",
     "packages": [{"label":"1,53 mg/spray"}],
     "dmp_search": "Lenzetto",
     "apotek_links": {"Apotek 1":"https://www.apotek1.no/search?q=Lenzetto","Vitusapotek":"https://www.vitusapotek.no/sok?term=Lenzetto","Boots":"https://www.bootsapotek.no/search?q=Lenzetto","Farmasiet":"https://www.farmasiet.no/search?query=Lenzetto"}},
    {"id": "progynova",       "name": "Progynova",       "form": "Tablett",         "type": "systemisk",
     "fk_url": "https://www.felleskatalogen.no/medisin/progynova-bayer-559276",
     "packages": [{"label":"1 mg"},{"label":"2 mg"}],
     "dmp_search": "Progynova",
     "apotek_links": {"Apotek 1":"https://www.apotek1.no/search?q=Progynova","Vitusapotek":"https://www.vitusapotek.no/sok?term=Progynova","Boots":"https://www.bootsapotek.no/search?q=Progynova","Farmasiet":"https://www.farmasiet.no/search?query=Progynova"}},
    {"id": "vagifem",         "name": "Vagifem",         "form": "Vaginaltablett",  "type": "vaginal",
     "fk_url": "https://www.felleskatalogen.no/medisin/vagifem-novo-nordisk-559494",
     "packages": [{"label":"10 µg"}],
     "dmp_search": "Vagifem",
     "apotek_links": {"Apotek 1":"https://www.apotek1.no/search?q=Vagifem","Vitusapotek":"https://www.vitusapotek.no/sok?term=Vagifem","Boots":"https://www.bootsapotek.no/search?q=Vagifem","Farmasiet":"https://www.farmasiet.no/search?query=Vagifem"}},
    {"id": "vagidonna",       "name": "Vagidonna",       "form": "Vaginaltablett",  "type": "vaginal",
     "fk_url": "https://www.felleskatalogen.no/medisin/vagidonna-gedeon-richter-562743",
     "packages": [{"label":"10 µg"}],
     "dmp_search": "Vagidonna",
     "apotek_links": {"Apotek 1":"https://www.apotek1.no/search?q=Vagidonna","Vitusapotek":"https://www.vitusapotek.no/sok?term=Vagidonna","Boots":"https://www.bootsapotek.no/search?q=Vagidonna","Farmasiet":"https://www.farmasiet.no/search?query=Vagidonna"}},
    {"id": "ovesterin",       "name": "Ovesterin",       "form": "Vagitorier/krem", "type": "vaginal",
     "fk_url": "https://www.felleskatalogen.no/medisin/ovesterin-aspen-558989",
     "packages": [{"label":"0,5 mg vagitorier"},{"label":"0,1 mg/g krem"}],
     "dmp_search": "Ovesterin",
     "apotek_links": {"Apotek 1":"https://www.apotek1.no/search?q=Ovesterin","Vitusapotek":"https://www.vitusapotek.no/sok?term=Ovesterin","Boots":"https://www.bootsapotek.no/search?q=Ovesterin","Farmasiet":"https://www.farmasiet.no/search?query=Ovesterin"}},
    {"id": "gelisse",         "name": "Gelisse",         "form": "Vaginalgel",      "type": "vaginal",
     "fk_url": "https://www.felleskatalogen.no/medisin/gelisse-italfarmaco-562400",
     "packages": [{"label":"50 µg/g gel"}],
     "dmp_search": "Gelisse",
     "apotek_links": {"Apotek 1":"https://www.apotek1.no/search?q=Gelisse","Vitusapotek":"https://www.vitusapotek.no/sok?term=Gelisse","Boots":"https://www.bootsapotek.no/search?q=Gelisse","Farmasiet":"https://www.farmasiet.no/search?query=Gelisse"}},
    {"id": "gynoflor",        "name": "Gynoflor",        "form": "Vaginaltablett",  "type": "vaginal",
     "fk_url": "https://www.felleskatalogen.no/medisin/gynoflor-medinova-558914",
     "packages": [{"label":"0,03 mg + Lactobacillus"}],
     "dmp_search": "Gynoflor",
     "apotek_links": {"Apotek 1":"https://www.apotek1.no/search?q=Gynoflor","Vitusapotek":"https://www.vitusapotek.no/sok?term=Gynoflor","Boots":"https://www.bootsapotek.no/search?q=Gynoflor","Farmasiet":"https://www.farmasiet.no/search?query=Gynoflor"}},
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "no-NO,no;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def search_status(prep_name: str, fk_slug: str) -> dict:
    """
    Søker Google etter preparatets side på Felleskatalogen.
    Google-snippets inneholder JS-rendret DMP-status.
    """
    # Use site-specific Google search for the exact FK page
    query = urllib.parse.quote_plus(
        f'"{prep_name}" "Status pr." felleskatalogen.no'
    )
    url = f"https://www.google.com/search?q={query}&hl=no&num=5&gl=no"

    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"    Nettverksfeil: {e}")
        return {}

    # Parse status from snippets
    m = re.search(
        r"Status\s+pr\.\s+(\d{2}\.\d{2}\.\d{4}):\s*(P[åa]g[åa]ende|Avsluttet)",
        html, re.IGNORECASE
    )
    if not m:
        return {}

    date = m.group(1).strip()
    status = m.group(2).strip()
    has_shortage = "p" in status.lower()

    result = {
        "has_shortage": has_shortage,
        "dmp_status": status,
        "dmp_status_date": date,
        "shortage_period": None,
        "shortage_reason": None,
    }

    m2 = re.search(r"[Mm]angelperiode:\s*(\d{2}\.\d{2}\.\d{4}\s+til\s+\d{2}\.\d{2}\.\d{4})", html)
    if m2:
        result["shortage_period"] = m2.group(1).strip()

    m3 = re.search(r"[ÅA]rsak:\s*([^\n<]{5,80})", html)
    if m3:
        result["shortage_reason"] = m3.group(1).strip()

    return result


def check_prep(prep: dict) -> dict:
    print(f"  {prep['name']:20s}", end=" ", flush=True)

    live = search_status(prep["name"], prep["fk_url"])

    if live:
        indicator = "⚠ MANGEL" if live["has_shortage"] else "✓ OK"
        print(f"{indicator:10s} (live, pr. {live.get('dmp_status_date', '?')})")
        status = live
    else:
        # No live data found – mark as unknown
        print("? (ikke funnet i søk)")
        status = {
            "has_shortage": None,
            "dmp_status": "Ikke funnet",
            "dmp_status_date": None,
            "shortage_period": None,
            "shortage_reason": None,
        }

    time.sleep(2)  # Be polite to Google

    return {
        "id": prep["id"], "name": prep["name"],
        "form": prep["form"], "type": prep["type"],
        "fk_url": prep["fk_url"], "packages": prep["packages"],
        "dmp_search_url": f"{DMP_BASE}?q={prep['dmp_search']}",
        "apotek_links": prep["apotek_links"],
        **status,
    }


def main():
    oslo = ZoneInfo("Europe/Oslo")
    now = datetime.now(oslo)
    print(f"\nGynForum tilgjengelighetssjekk v4 – {now.strftime('%d.%m.%Y %H:%M')}\n")

    results = [check_prep(p) for p in PREPARATIONS]

    with_shortage = [r for r in results if r["has_shortage"] is True]
    ok = [r for r in results if r["has_shortage"] is False]
    unknown = [r for r in results if r["has_shortage"] is None]

    output = {
        "generated": now.isoformat(),
        "generated_display": now.strftime("%d.%m.%Y kl. %H:%M"),
        "source": "Felleskatalogen/DMP via Google-søk – ukentlig automatisk sjekk",
        "dmp_overview_url": DMP_BASE,
        "summary": {
            "total": len(results),
            "with_shortage": len(with_shortage),
            "ok": len(ok),
            "unknown": len(unknown),
        },
        "preparations": results,
    }

    with open("data/status.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✓ status.json oppdatert")
    print(f"  {len(with_shortage)} med mangel · {len(ok)} OK · {len(unknown)} ikke funnet")


if __name__ == "__main__":
    main()
