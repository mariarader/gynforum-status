"""
GynForum – Tilgjengelighetssjekk for østrogenpreparater
========================================================
Henter mangel-status fra DMP (Direktoratet for medisinske produkter)
for hver pakningsvariant av relevante østrogenpreparater.

Kilde: DMP pakningssider via FEST-ID-lenker på Felleskatalogen.
Kjøres ukentlig via GitHub Actions og skriver til data/status.json.
"""

import json
import re
import urllib.request
import urllib.error
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# ── Preparater med DMP FEST-ID per pakning ────────────────────────────────────
# FEST-ID hentes fra Felleskatalogen pakning-URL:
#   https://www.felleskatalogen.no/medisin/navnformstyrkemerkevare/id-{FEST_ID}
# DMP-mangel-URL følger samme ID på:
#   https://www.felleskatalogen.no/medisin/navnformstyrkemerkevare/id-{FEST_ID}
# Status-teksten "Status pr. DD.MM.ÅÅÅÅ:" og "Mangelperiode:" hentes herfra.

PREPARATIONS = [
    {
        "id": "estradot",
        "name": "Estradot",
        "form": "Plaster",
        "type": "systemisk",
        "fk_url": "https://www.felleskatalogen.no/medisin/estradot-sandoz-558818",
        "packages": [
            {"label": "25 µg/24t", "fest_id": "ID_B2A1C3D4-0001-0001-0001-000000000001"},
            {"label": "37,5 µg/24t", "fest_id": "ID_B2A1C3D4-0001-0001-0001-000000000002"},
            {"label": "50 µg/24t", "fest_id": "ID_B2A1C3D4-0001-0001-0001-000000000003"},
            {"label": "75 µg/24t", "fest_id": "ID_B2A1C3D4-0001-0001-0001-000000000004"},
            {"label": "100 µg/24t", "fest_id": "ID_B2A1C3D4-0001-0001-0001-000000000005"},
        ],
        "dmp_search": "Estradot",
        "apotek_links": {
            "Apotek 1":    "https://www.apotek1.no/search?q=Estradot",
            "Vitusapotek": "https://www.vitusapotek.no/sok?term=Estradot",
            "Boots":       "https://www.bootsapotek.no/search?q=Estradot",
            "Farmasiet":   "https://www.farmasiet.no/search?query=Estradot",
        },
    },
    {
        "id": "estradiol_hexal",
        "name": "Estradiol Hexal",
        "form": "Plaster",
        "type": "systemisk",
        "fk_url": "https://www.felleskatalogen.no/medisin/estradiol-hexal-hexal-566040",
        "packages": [
            {"label": "25 µg/24t"},
            {"label": "37,5 µg/24t"},
            {"label": "50 µg/24t"},
            {"label": "75 µg/24t"},
            {"label": "100 µg/24t"},
        ],
        "dmp_search": "Estradiol+Hexal",
        "apotek_links": {
            "Apotek 1":    "https://www.apotek1.no/search?q=Estradiol+Hexal",
            "Vitusapotek": "https://www.vitusapotek.no/sok?term=Estradiol+Hexal",
            "Boots":       "https://www.bootsapotek.no/search?q=Estradiol+Hexal",
            "Farmasiet":   "https://www.farmasiet.no/search?query=Estradiol+Hexal",
        },
    },
    {
        "id": "estrogel",
        "name": "Estrogel",
        "form": "Gel",
        "type": "systemisk",
        "fk_url": "https://www.felleskatalogen.no/medisin/estrogel-besins-healthcare-norway-559089",
        "packages": [
            {"label": "0,06% gel pumpe"},
        ],
        "dmp_search": "Estrogel",
        "apotek_links": {
            "Apotek 1":    "https://www.apotek1.no/search?q=Estrogel",
            "Vitusapotek": "https://www.vitusapotek.no/sok?term=Estrogel",
            "Boots":       "https://www.bootsapotek.no/search?q=Estrogel",
            "Farmasiet":   "https://www.farmasiet.no/search?query=Estrogel",
        },
    },
    {
        "id": "lenzetto",
        "name": "Lenzetto",
        "form": "Spray",
        "type": "systemisk",
        "fk_url": "https://www.felleskatalogen.no/medisin/lenzetto-gedeon-richter-647011",
        "packages": [
            {"label": "1,53 mg/spray"},
        ],
        "dmp_search": "Lenzetto",
        "apotek_links": {
            "Apotek 1":    "https://www.apotek1.no/search?q=Lenzetto",
            "Vitusapotek": "https://www.vitusapotek.no/sok?term=Lenzetto",
            "Boots":       "https://www.bootsapotek.no/search?q=Lenzetto",
            "Farmasiet":   "https://www.farmasiet.no/search?query=Lenzetto",
        },
    },
    {
        "id": "progynova",
        "name": "Progynova",
        "form": "Tablett",
        "type": "systemisk",
        "fk_url": "https://www.felleskatalogen.no/medisin/progynova-bayer-559276",
        "packages": [
            {"label": "1 mg"},
            {"label": "2 mg"},
        ],
        "dmp_search": "Progynova",
        "apotek_links": {
            "Apotek 1":    "https://www.apotek1.no/search?q=Progynova",
            "Vitusapotek": "https://www.vitusapotek.no/sok?term=Progynova",
            "Boots":       "https://www.bootsapotek.no/search?q=Progynova",
            "Farmasiet":   "https://www.farmasiet.no/search?query=Progynova",
        },
    },
    {
        "id": "vagifem",
        "name": "Vagifem",
        "form": "Vaginaltablett",
        "type": "vaginal",
        "fk_url": "https://www.felleskatalogen.no/medisin/vagifem-novo-nordisk-559494",
        "packages": [
            {"label": "10 µg"},
        ],
        "dmp_search": "Vagifem",
        "apotek_links": {
            "Apotek 1":    "https://www.apotek1.no/search?q=Vagifem",
            "Vitusapotek": "https://www.vitusapotek.no/sok?term=Vagifem",
            "Boots":       "https://www.bootsapotek.no/search?q=Vagifem",
            "Farmasiet":   "https://www.farmasiet.no/search?query=Vagifem",
        },
    },
    {
        "id": "vagidonna",
        "name": "Vagidonna",
        "form": "Vaginaltablett",
        "type": "vaginal",
        "fk_url": "https://www.felleskatalogen.no/medisin/vagidonna-gedeon-richter-562743",
        "packages": [
            {"label": "10 µg"},
        ],
        "dmp_search": "Vagidonna",
        "apotek_links": {
            "Apotek 1":    "https://www.apotek1.no/search?q=Vagidonna",
            "Vitusapotek": "https://www.vitusapotek.no/sok?term=Vagidonna",
            "Boots":       "https://www.bootsapotek.no/search?q=Vagidonna",
            "Farmasiet":   "https://www.farmasiet.no/search?query=Vagidonna",
        },
    },
    {
        "id": "ovesterin",
        "name": "Ovesterin",
        "form": "Vagitorier/krem",
        "type": "vaginal",
        "fk_url": "https://www.felleskatalogen.no/medisin/ovesterin-aspen-558989",
        "packages": [
            {"label": "0,5 mg vagitorier"},
            {"label": "0,1 mg/g krem"},
        ],
        "dmp_search": "Ovesterin",
        "apotek_links": {
            "Apotek 1":    "https://www.apotek1.no/search?q=Ovesterin",
            "Vitusapotek": "https://www.vitusapotek.no/sok?term=Ovesterin",
            "Boots":       "https://www.bootsapotek.no/search?q=Ovesterin",
            "Farmasiet":   "https://www.farmasiet.no/search?query=Ovesterin",
        },
    },
    {
        "id": "gelisse",
        "name": "Gelisse",
        "form": "Vaginalgel",
        "type": "vaginal",
        "fk_url": "https://www.felleskatalogen.no/medisin/gelisse-italfarmaco-562400",
        "packages": [
            {"label": "50 µg/g gel"},
        ],
        "dmp_search": "Gelisse",
        "apotek_links": {
            "Apotek 1":    "https://www.apotek1.no/search?q=Gelisse",
            "Vitusapotek": "https://www.vitusapotek.no/sok?term=Gelisse",
            "Boots":       "https://www.bootsapotek.no/search?q=Gelisse",
            "Farmasiet":   "https://www.farmasiet.no/search?query=Gelisse",
        },
    },
    {
        "id": "gynoflor",
        "name": "Gynoflor",
        "form": "Vaginaltablett",
        "type": "vaginal",
        "fk_url": "https://www.felleskatalogen.no/medisin/gynoflor-medinova-558914",
        "packages": [
            {"label": "0,03 mg + Lactobacillus"},
        ],
        "dmp_search": "Gynoflor",
        "apotek_links": {
            "Apotek 1":    "https://www.apotek1.no/search?q=Gynoflor",
            "Vitusapotek": "https://www.vitusapotek.no/sok?term=Gynoflor",
            "Boots":       "https://www.bootsapotek.no/search?q=Gynoflor",
            "Farmasiet":   "https://www.farmasiet.no/search?query=Gynoflor",
        },
    },
]

# ── DMP mangel-søk URL ────────────────────────────────────────────────────────
DMP_BASE = "https://www.dmp.no/forsyningssikkerhet/legemiddelmangel/oversikt-over-legemiddelmangel---for-pasienter-og-helsepersonell"

def fetch_html(url: str) -> str:
    """Fetch HTML from URL with a browser-like User-Agent."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (compatible; GynForum-StatusBot/1.0; "
                "+https://gynforum.com/tilgjengelighet)"
            ),
            "Accept-Language": "no,nb;q=0.9",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_fk_status(html: str, prep_name: str) -> dict:
    """
    Parse shortage status from a Felleskatalog product page.
    Looks for patterns like:
      'Status pr. 18.05.2026: Pågående'
      'Mangelperiode: 10.04.2026 til 01.06.2026'
      'Årsak: Produksjonsproblemer'
    """
    result = {
        "dmp_status": None,       # "Pågående" | "Avsluttet" | null
        "dmp_status_date": None,  # "18.05.2026"
        "shortage_period": None,  # "10.04.2026 til 01.06.2026"
        "shortage_reason": None,  # "Produksjonsproblemer"
        "has_shortage": False,
    }

    # Status line: "Status pr. DD.MM.ÅÅÅÅ: <verdi>"
    m = re.search(
        r"Status\s+pr\.\s+(\d{2}\.\d{2}\.\d{4}):\s*([^\n<]+)",
        html, re.IGNORECASE
    )
    if m:
        result["dmp_status_date"] = m.group(1).strip()
        result["dmp_status"] = m.group(2).strip()
        if "pågående" in result["dmp_status"].lower():
            result["has_shortage"] = True

    # Mangelperiode: "DD.MM.ÅÅÅÅ til DD.MM.ÅÅÅÅ"
    m2 = re.search(
        r"[Mm]angelperiode:\s*(\d{2}\.\d{2}\.\d{4}\s+til\s+\d{2}\.\d{2}\.\d{4})",
        html
    )
    if m2:
        result["shortage_period"] = m2.group(1).strip()

    # Årsak
    m3 = re.search(r"[ÅÅ]rsak:\s*([^\n<]{5,80})", html)
    if m3:
        result["shortage_reason"] = m3.group(1).strip()

    return result


def check_preparation(prep: dict) -> dict:
    """Fetch FK page and parse DMP status for a preparation."""
    print(f"  Sjekker {prep['name']} …", end=" ")
    try:
        html = fetch_html(prep["fk_url"])
        status = parse_fk_status(html, prep["name"])
        print("OK" if not status["has_shortage"] else "⚠ MANGEL FUNNET")
    except urllib.error.URLError as e:
        print(f"FEIL: {e}")
        status = {
            "dmp_status": "Ukjent (nettverksfeil)",
            "dmp_status_date": None,
            "shortage_period": None,
            "shortage_reason": None,
            "has_shortage": None,
        }

    return {
        "id": prep["id"],
        "name": prep["name"],
        "form": prep["form"],
        "type": prep["type"],
        "fk_url": prep["fk_url"],
        "packages": prep["packages"],
        "dmp_search_url": f"{DMP_BASE}?q={prep['dmp_search']}",
        "apotek_links": prep["apotek_links"],
        **status,
    }


def main():
    oslo = ZoneInfo("Europe/Oslo")
    now = datetime.now(oslo)

    print(f"\nGynForum tilgjengelighetssjekk – {now.strftime('%d.%m.%Y %H:%M')} (Oslo)\n")
    print("Henter status fra Felleskatalogen/DMP …\n")

    results = []
    for prep in PREPARATIONS:
        results.append(check_preparation(prep))

    # Summary
    with_shortage = [r for r in results if r["has_shortage"] is True]
    unknown = [r for r in results if r["has_shortage"] is None]

    output = {
        "generated": now.isoformat(),
        "generated_display": now.strftime("%d.%m.%Y kl. %H:%M"),
        "source": "Felleskatalogen / DMP – automatisk ukentlig sjekk",
        "dmp_overview_url": DMP_BASE,
        "summary": {
            "total": len(results),
            "with_shortage": len(with_shortage),
            "ok": len(results) - len(with_shortage) - len(unknown),
            "unknown": len(unknown),
        },
        "preparations": results,
    }

    out_path = "data/status.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Skrev {out_path}")
    print(f"  {len(with_shortage)} preparater med aktiv mangel")
    print(f"  {len(unknown)} preparater med ukjent status (nettverksfeil)")


if __name__ == "__main__":
    main()
