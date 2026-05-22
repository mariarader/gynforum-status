"""
GynForum – Tilgjengelighetssjekk v5
=====================================
Bruker Claude API (web_search tool) til å hente og tolke
DMP-mangelstatus for østrogenpreparater.
Krever ANTHROPIC_API_KEY som GitHub Actions secret.
"""

import json
import urllib.request
import urllib.error
from datetime import datetime
from zoneinfo import ZoneInfo
import os

DMP_BASE = "https://www.dmp.no/forsyningssikkerhet/legemiddelmangel/oversikt-over-legemiddelmangel---for-pasienter-og-helsepersonell"

PREPARATIONS = [
    {"id": "estradot",        "name": "Estradot",        "form": "Plaster",         "type": "systemisk",
     "packages": [{"label":"25 µg/24t"},{"label":"37,5 µg/24t"},{"label":"50 µg/24t"},{"label":"75 µg/24t"},{"label":"100 µg/24t"}],
     "dmp_search": "Estradot",
     "apotek_links": {"Apotek 1":"https://www.apotek1.no/search?q=Estradot","Vitusapotek":"https://www.vitusapotek.no/sok?term=Estradot","Boots":"https://www.bootsapotek.no/search?q=Estradot","Farmasiet":"https://www.farmasiet.no/search?query=Estradot"}},
    {"id": "estradiol_hexal", "name": "Estradiol Hexal", "form": "Plaster",         "type": "systemisk",
     "packages": [{"label":"25 µg/24t"},{"label":"37,5 µg/24t"},{"label":"50 µg/24t"},{"label":"75 µg/24t"},{"label":"100 µg/24t"}],
     "dmp_search": "Estradiol+Hexal",
     "apotek_links": {"Apotek 1":"https://www.apotek1.no/search?q=Estradiol+Hexal","Vitusapotek":"https://www.vitusapotek.no/sok?term=Estradiol+Hexal","Boots":"https://www.bootsapotek.no/search?q=Estradiol+Hexal","Farmasiet":"https://www.farmasiet.no/search?query=Estradiol+Hexal"}},
    {"id": "estrogel",        "name": "Estrogel",        "form": "Gel",             "type": "systemisk",
     "packages": [{"label":"0,06% gel pumpe"}],
     "dmp_search": "Estrogel",
     "apotek_links": {"Apotek 1":"https://www.apotek1.no/search?q=Estrogel","Vitusapotek":"https://www.vitusapotek.no/sok?term=Estrogel","Boots":"https://www.bootsapotek.no/search?q=Estrogel","Farmasiet":"https://www.farmasiet.no/search?query=Estrogel"}},
    {"id": "lenzetto",        "name": "Lenzetto",        "form": "Spray",           "type": "systemisk",
     "packages": [{"label":"1,53 mg/spray"}],
     "dmp_search": "Lenzetto",
     "apotek_links": {"Apotek 1":"https://www.apotek1.no/search?q=Lenzetto","Vitusapotek":"https://www.vitusapotek.no/sok?term=Lenzetto","Boots":"https://www.bootsapotek.no/search?q=Lenzetto","Farmasiet":"https://www.farmasiet.no/search?query=Lenzetto"}},
    {"id": "progynova",       "name": "Progynova",       "form": "Tablett",         "type": "systemisk",
     "packages": [{"label":"1 mg"},{"label":"2 mg"}],
     "dmp_search": "Progynova",
     "apotek_links": {"Apotek 1":"https://www.apotek1.no/search?q=Progynova","Vitusapotek":"https://www.vitusapotek.no/sok?term=Progynova","Boots":"https://www.bootsapotek.no/search?q=Progynova","Farmasiet":"https://www.farmasiet.no/search?query=Progynova"}},
    {"id": "vagifem",         "name": "Vagifem",         "form": "Vaginaltablett",  "type": "vaginal",
     "packages": [{"label":"10 µg"}],
     "dmp_search": "Vagifem",
     "apotek_links": {"Apotek 1":"https://www.apotek1.no/search?q=Vagifem","Vitusapotek":"https://www.vitusapotek.no/sok?term=Vagifem","Boots":"https://www.bootsapotek.no/search?q=Vagifem","Farmasiet":"https://www.farmasiet.no/search?query=Vagifem"}},
    {"id": "vagidonna",       "name": "Vagidonna",       "form": "Vaginaltablett",  "type": "vaginal",
     "packages": [{"label":"10 µg"}],
     "dmp_search": "Vagidonna",
     "apotek_links": {"Apotek 1":"https://www.apotek1.no/search?q=Vagidonna","Vitusapotek":"https://www.vitusapotek.no/sok?term=Vagidonna","Boots":"https://www.bootsapotek.no/search?q=Vagidonna","Farmasiet":"https://www.farmasiet.no/search?query=Vagidonna"}},
    {"id": "ovesterin",       "name": "Ovesterin",       "form": "Vagitorier/krem", "type": "vaginal",
     "packages": [{"label":"0,5 mg vagitorier"},{"label":"0,1 mg/g krem"}],
     "dmp_search": "Ovesterin",
     "apotek_links": {"Apotek 1":"https://www.apotek1.no/search?q=Ovesterin","Vitusapotek":"https://www.vitusapotek.no/sok?term=Ovesterin","Boots":"https://www.bootsapotek.no/search?q=Ovesterin","Farmasiet":"https://www.farmasiet.no/search?query=Ovesterin"}},
    {"id": "gelisse",         "name": "Gelisse",         "form": "Vaginalgel",      "type": "vaginal",
     "packages": [{"label":"50 µg/g gel"}],
     "dmp_search": "Gelisse",
     "apotek_links": {"Apotek 1":"https://www.apotek1.no/search?q=Gelisse","Vitusapotek":"https://www.vitusapotek.no/sok?term=Gelisse","Boots":"https://www.bootsapotek.no/search?q=Gelisse","Farmasiet":"https://www.farmasiet.no/search?query=Gelisse"}},
    {"id": "gynoflor",        "name": "Gynoflor",        "form": "Vaginaltablett",  "type": "vaginal",
     "packages": [{"label":"0,03 mg + Lactobacillus"}],
     "dmp_search": "Gynoflor",
     "apotek_links": {"Apotek 1":"https://www.apotek1.no/search?q=Gynoflor","Vitusapotek":"https://www.vitusapotek.no/sok?term=Gynoflor","Boots":"https://www.bootsapotek.no/search?q=Gynoflor","Farmasiet":"https://www.farmasiet.no/search?query=Gynoflor"}},
]


def call_claude(prompt: str) -> str:
    """Call Claude API with web_search tool to look up current DMP status."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY mangler")

    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 1000,
        "tools": [{"type": "web_search_20250305", "name": "web_search"}],
        "messages": [{"role": "user", "content": prompt}]
    }

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode(),
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode())

    # Extract text from response
    return " ".join(
        b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"
    )


def check_all_preparations() -> list:
    """Ask Claude to check all preparations in one query."""
    names = ", ".join(p["name"] for p in PREPARATIONS)

    prompt = f"""Sjekk DMP (Direktoratet for medisinske produkter) mangelloversikt for disse norske østrogenpreparatene: {names}

Søk på Felleskatalogen og DMP for hvert preparat. For hvert preparat, returner kun JSON på dette formatet:
[
  {{"id": "estradot", "has_shortage": true/false/null, "dmp_status": "Pågående/Ingen meldt mangel/Ukjent", "dmp_status_date": "DD.MM.ÅÅÅÅ eller null", "shortage_reason": "årsak eller null"}},
  ...
]

Returner KUN JSON-arrayen, ingen annen tekst."""

    response = call_claude(prompt)
    # Extract JSON array
    import re
    m = re.search(r'\[[\s\S]+\]', response)
    if m:
        return json.loads(m.group(0))
    return []


def main():
    oslo = ZoneInfo("Europe/Oslo")
    now = datetime.now(oslo)
    print(f"\nGynForum tilgjengelighetssjekk v5 (Claude API) – {now.strftime('%d.%m.%Y %H:%M')}\n")

    try:
        live_data = check_all_preparations()
        live_map = {r["id"]: r for r in live_data}
        print(f"Fikk svar for {len(live_map)} preparater fra Claude API")
    except Exception as e:
        print(f"Claude API-feil: {e}")
        live_map = {}

    results = []
    for prep in PREPARATIONS:
        live = live_map.get(prep["id"], {})
        has_shortage = live.get("has_shortage")
        icon = "⚠ MANGEL" if has_shortage is True else ("✓ OK" if has_shortage is False else "? UKJENT")
        print(f"  {prep['name']:20s} {icon}")
        results.append({
            "id": prep["id"], "name": prep["name"],
            "form": prep["form"], "type": prep["type"],
            "packages": prep["packages"],
            "dmp_search_url": f"{DMP_BASE}?q={prep['dmp_search']}",
            "apotek_links": prep["apotek_links"],
            "has_shortage": has_shortage,
            "dmp_status": live.get("dmp_status", "Ukjent"),
            "dmp_status_date": live.get("dmp_status_date"),
            "shortage_period": live.get("shortage_period"),
            "shortage_reason": live.get("shortage_reason"),
        })

    with_shortage = [r for r in results if r["has_shortage"] is True]
    ok_count = [r for r in results if r["has_shortage"] is False]
    unknown = [r for r in results if r["has_shortage"] is None]

    output = {
        "generated": now.isoformat(),
        "generated_display": now.strftime("%d.%m.%Y kl. %H:%M"),
        "source": "Felleskatalogen/DMP via Claude API med web_search – ukentlig",
        "dmp_overview_url": DMP_BASE,
        "summary": {
            "total": len(results),
            "with_shortage": len(with_shortage),
            "ok": len(ok_count),
            "unknown": len(unknown),
        },
        "preparations": results,
    }

    with open("data/status.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✓ status.json oppdatert – {len(with_shortage)} mangel · {len(ok_count)} OK · {len(unknown)} ukjent")


if __name__ == "__main__":
    main()
