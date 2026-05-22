"""
GynForum – Tilgjengelighetssjekk v3
=====================================
Bruker Playwright (headless Chromium) til å hente JS-rendret innhold
fra Felleskatalogen og parse DMP-mangelstatus.

Installasjon i GitHub Actions:
  pip install playwright
  playwright install chromium --with-deps
"""

import json
import re
import asyncio
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


def parse_status(text: str) -> dict:
    """Parse DMP status from rendered page text."""
    result = {"has_shortage": False, "dmp_status": "Ingen meldt mangel",
              "dmp_status_date": None, "shortage_period": None, "shortage_reason": None}

    m = re.search(r"Status\s+pr\.\s+(\d{2}\.\d{2}\.\d{4}):\s*(P[åa]g[åa]ende|Avsluttet)", text, re.IGNORECASE)
    if m:
        result["dmp_status_date"] = m.group(1).strip()
        result["dmp_status"] = m.group(2).strip()
        result["has_shortage"] = "p" in result["dmp_status"].lower()

    m2 = re.search(r"[Mm]angelperiode:\s*(\d{2}\.\d{2}\.\d{4}\s+til\s+\d{2}\.\d{2}\.\d{4})", text)
    if m2:
        result["shortage_period"] = m2.group(1).strip()

    m3 = re.search(r"[ÅA]rsak:\s*([^\n]{5,80})", text)
    if m3:
        result["shortage_reason"] = m3.group(1).strip()

    return result


async def fetch_prep(browser, prep: dict) -> dict:
    page = await browser.new_page()
    try:
        await page.goto(prep["fk_url"], wait_until="networkidle", timeout=30000)
        # Wait for status text to appear
        try:
            await page.wait_for_selector("text=Status pr.", timeout=8000)
        except Exception:
            pass
        text = await page.inner_text("body")
        status = parse_status(text)
        indicator = "⚠ MANGEL" if status["has_shortage"] else "✓ OK"
        print(f"  {prep['name']:20s} {indicator:12s} {status.get('dmp_status_date') or ''}")
    except Exception as e:
        print(f"  {prep['name']:20s} FEIL: {e}")
        status = {"has_shortage": None, "dmp_status": "Feil ved henting",
                  "dmp_status_date": None, "shortage_period": None, "shortage_reason": None}
    finally:
        await page.close()

    return {
        "id": prep["id"], "name": prep["name"], "form": prep["form"],
        "type": prep["type"], "fk_url": prep["fk_url"],
        "packages": prep["packages"],
        "dmp_search_url": f"{DMP_BASE}?q={prep['dmp_search']}",
        "apotek_links": prep["apotek_links"],
        **status,
    }


async def main_async():
    from playwright.async_api import async_playwright

    oslo = ZoneInfo("Europe/Oslo")
    now = datetime.now(oslo)
    print(f"\nGynForum tilgjengelighetssjekk v3 (Playwright) – {now.strftime('%d.%m.%Y %H:%M')}\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        results = []
        for prep in PREPARATIONS:
            result = await fetch_prep(browser, prep)
            results.append(result)
        await browser.close()

    with_shortage = [r for r in results if r["has_shortage"] is True]
    unknown = [r for r in results if r["has_shortage"] is None]

    output = {
        "generated": now.isoformat(),
        "generated_display": now.strftime("%d.%m.%Y kl. %H:%M"),
        "source": "Felleskatalogen/DMP – automatisk ukentlig Playwright-sjekk",
        "dmp_overview_url": DMP_BASE,
        "summary": {
            "total": len(results),
            "with_shortage": len(with_shortage),
            "ok": len(results) - len(with_shortage) - len(unknown),
            "unknown": len(unknown),
        },
        "preparations": results,
    }

    with open("data/status.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✓ data/status.json skrevet – {len(with_shortage)} med mangel, {len(unknown)} ukjent")


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
