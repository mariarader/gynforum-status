#!/usr/bin/env python3
"""
GynForum – lokal DMP-tilgjengelighetssjekk (v2, robust parsing)
================================================================
Kjører på din egen Mac. Bruker Playwright (headless Chromium) til å
hente JS-rendret mangelstatus fra DMP, bygger status.json, og pusher
den til GitHub via API.

Sikkerhetsmekanismer:
  - Nedgraderer ALDRI en kjent verdi til "ukjent". Ved tvil beholdes
    forrige verdi fra status.json som ligger på GitHub.
  - Logger nøyaktig hva som ble lest for hvert preparat, så du kan
    verifisere parsingen.
  - Krever en viss minimumskvalitet før push (avbryter hvis alt ble ukjent).
"""

import json
import re
import base64
import urllib.request
import urllib.parse
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

GITHUB_OWNER = "mariarader"
GITHUB_REPO = "gynforum-status"
TOKEN_FILE = os.path.expanduser("~/.gynforum_token")
DMP_BASE = "https://www.dmp.no/forsyningssikkerhet/legemiddelmangel/oversikt-over-legemiddelmangel---for-pasienter-og-helsepersonell"

LINKS = {
    "estradot": {
        "Apotek 1": "https://www.apotek1.no/soek/estradot?searchTerm=estradot&sortMethod=0&pageSize=20&pageNumber=1&categoryId=&facets=&previousCategoryId=#load-more-potential",
        "Vitusapotek": "https://www.vitusapotek.no/search?text=estradot%20dep%20plast",
        "Boots": "https://www.boots.no/search/result/?q=estradot",
        "Farmasiet": "https://www.farmasiet.no/search?searchPhrase=estradot&orderBy=0",
    },
    "estradiol_hexal": {
        "Apotek 1": "https://www.apotek1.no/soek/Estradiol%20Hex%20?searchTerm=Estradiol%20Hex%20&sortMethod=0&pageSize=20&pageNumber=1&categoryId=&facets=&previousCategoryId=#load-more-potential",
        "Vitusapotek": "https://www.vitusapotek.no/search?text=estradiol%20hex",
        "Boots": "https://www.boots.no/search/result/?q=estradiol+hexal",
        "Farmasiet": "https://www.farmasiet.no/search?searchPhrase=estradiol+hexal&orderBy=0",
    },
    "estrogel": {
        "Apotek 1": "https://www.apotek1.no/produkter/estrogel-transdermalgel-0-75mg-95339p",
        "Vitusapotek": "https://www.vitusapotek.no/reseptbelagte-legemidler/g-urogenitalsystem-og-kjonnshormoner/g03-kjonnshormoner-og-midler-med-effekt-pa-g/g03ca-naturlige-og-halvsyntetiske-ostrogeneru/estrogel-transdermalgel-075mg-1-x-80-g-095339",
        "Boots": "https://www.boots.no/search/result/?q=estrogel",
        "Farmasiet": "https://www.farmasiet.no/catalog/reseptvarer/g03-kjonnshormoner-og-midler-med-effekt-pa-genitalia2/estrogel-transdermalgel-075mgdos-1-x-80-g.-flaske-av-plast-med-dosepumpe,5024071",
    },
    "lenzetto": {
        "Apotek 1": "https://www.apotek1.no/soek/lenzetto?searchTerm=lenzetto&sortMethod=0&pageSize=20&pageNumber=1&categoryId=&facets=&previousCategoryId=#load-more-potential",
        "Vitusapotek": "https://www.vitusapotek.no/search?text=lenzetto",
        "Boots": "https://www.boots.no/search/result/?q=lenzetto",
        "Farmasiet": "https://www.farmasiet.no/search?searchPhrase=lenzetto&orderBy=0",
    },
    "progynova": {
        "Apotek 1": "https://www.apotek1.no/soek/progynova?searchTerm=progynova&sortMethod=0&pageSize=20&pageNumber=1&categoryId=&facets=&previousCategoryId=#load-more-potential",
        "Vitusapotek": "https://www.vitusapotek.no/search?text=Progynova",
        "Boots": "https://www.boots.no/search/result/?q=progynova",
        "Farmasiet": "https://www.farmasiet.no/search?searchPhrase=progynova",
    },
}

PREPARATIONS = [
    {"key": "estradot", "name": "Estradot", "form": "Plaster", "type": "systemisk",
     "dmp_search": "Estradot", "doses": ["25 µg/24t","37,5 µg/24t","50 µg/24t","75 µg/24t","100 µg/24t"]},
    {"key": "estradiol_hexal", "name": "Estradiol Hexal", "form": "Plaster", "type": "systemisk",
     "dmp_search": "Estradiol Hexal", "doses": ["25 µg/24t","37,5 µg/24t","50 µg/24t","75 µg/24t","100 µg/24t"]},
    {"key": "estrogel", "name": "Estrogel", "form": "Gel", "type": "systemisk",
     "dmp_search": "Estrogel", "doses": ["0,75 mg/trykk"]},
    {"key": "lenzetto", "name": "Lenzetto", "form": "Spray", "type": "systemisk",
     "dmp_search": "Lenzetto", "doses": ["1,53 mg/spray"]},
    {"key": "progynova", "name": "Progynova", "form": "Tablett", "type": "systemisk",
     "dmp_search": "Progynova", "doses": ["1 mg","2 mg"]},
]


def les_token():
    if not os.path.exists(TOKEN_FILE):
        print(f"FEIL: Fant ikke {TOKEN_FILE}. Kjør installasjonsscriptet først.")
        sys.exit(1)
    return open(TOKEN_FILE).read().strip()


def hent_forrige_status(token: str) -> dict:
    """Henter eksisterende status.json fra GitHub – brukes som fallback."""
    api = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/data/status.json"
    req = urllib.request.Request(api, headers={"Authorization": f"token {token}", "User-Agent": "gynforum-mac"})
    try:
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read())
            innhold = base64.b64decode(data["content"]).decode()
            forrige = json.loads(innhold)
        # Bygg oppslag per key på preparatnivå
        per_key = {}
        for p in forrige.get("preparations", []):
            # Utled key fra id (f.eks. "estradot_25" -> "estradot")
            for prep in PREPARATIONS:
                if p["id"].startswith(prep["key"]):
                    per_key[prep["key"]] = {
                        "has_shortage": p.get("has_shortage"),
                        "dmp_status": p.get("dmp_status"),
                        "dmp_status_date": p.get("dmp_status_date"),
                        "shortage_reason": p.get("shortage_reason"),
                    }
                    break
        return per_key
    except Exception as e:
        print(f"  (Kunne ikke hente forrige status: {e})")
        return {}


def hent_dmp_status(page, prep: dict, logg: list) -> dict:
    """
    Søker DMP-oversikten og leser mangelstatus.
    Returnerer dict med 'sikker' (bool) som angir om parsingen var pålitelig.
    """
    sok = prep["dmp_search"]
    navn = prep["name"]
    url = f"{DMP_BASE}?q={urllib.parse.quote(sok)}"

    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(3000)
        tekst = page.inner_text("body")
    except Exception as e:
        logg.append(f"{navn}: FEIL ved henting – {e}")
        return {"sikker": False}

    # Sjekk at siden faktisk inneholder preparatnavnet (ellers er søket tomt/feil)
    if navn.lower() not in tekst.lower() and sok.lower() not in tekst.lower():
        logg.append(f"{navn}: preparatnavn IKKE funnet på siden – usikkert resultat")
        return {"sikker": False}

    # Finn statusord nær preparatnavnet
    # DMP bruker "Pågående" for aktiv mangel, "Avsluttet" for løst
    har_pagaende = bool(re.search(r"[Pp]ågående", tekst))
    har_avsluttet = bool(re.search(r"[Aa]vsluttet", tekst))
    har_status_kolonne = "Status" in tekst or "status" in tekst

    # Finn dato hvis tilgjengelig
    dato = None
    m = re.search(r"(\d{2}\.\d{2}\.\d{4})", tekst)
    if m:
        dato = m.group(1)

    # Tolkning
    if har_pagaende and not har_avsluttet:
        logg.append(f"{navn}: 'Pågående' funnet → MANGEL (dato: {dato})")
        return {"sikker": True, "has_shortage": True, "dmp_status": "Pågående",
                "dmp_status_date": dato, "shortage_reason": None}
    elif har_avsluttet and not har_pagaende:
        logg.append(f"{navn}: kun 'Avsluttet' → ingen aktiv mangel")
        return {"sikker": True, "has_shortage": False, "dmp_status": "Ingen meldt mangel",
                "dmp_status_date": None, "shortage_reason": None}
    elif not har_pagaende and not har_avsluttet and har_status_kolonne:
        # Siden lastet, ingen mangelmelding funnet → trygt å si "ingen mangel"
        logg.append(f"{navn}: ingen mangelmelding funnet → ingen mangel")
        return {"sikker": True, "has_shortage": False, "dmp_status": "Ingen meldt mangel",
                "dmp_status_date": None, "shortage_reason": None}
    else:
        # Tvetydig (både pågående og avsluttet, eller uklart) → usikkert
        logg.append(f"{navn}: TVETYDIG (pågående={har_pagaende}, avsluttet={har_avsluttet}) – beholder forrige verdi")
        return {"sikker": False}


def bygg_status(status_map: dict, forrige: dict, logg: list) -> dict:
    preps = []
    antall_sikre = 0

    for p in PREPARATIONS:
        ny = status_map.get(p["key"], {})
        gammel = forrige.get(p["key"], {})

        if ny.get("sikker"):
            # Bruk ny, sikker verdi
            s = {k: ny.get(k) for k in ["has_shortage","dmp_status","dmp_status_date","shortage_reason"]}
            antall_sikre += 1
        elif gammel:
            # Behold forrige verdi (sikkerhetsmekanisme)
            s = gammel
            logg.append(f"{p['name']}: BEHOLDT forrige verdi ({gammel.get('dmp_status')})")
        else:
            # Ingen tidligere verdi heller
            s = {"has_shortage": None, "dmp_status": "Ukjent", "dmp_status_date": None, "shortage_reason": None}

        for dose in p["doses"]:
            preps.append({
                "id": f"{p['key']}_{dose.split()[0].replace(',','')}",
                "name": p["name"], "dose": dose, "form": p["form"], "type": p["type"],
                "has_shortage": s.get("has_shortage"),
                "dmp_status": s.get("dmp_status", "Ukjent"),
                "dmp_status_date": s.get("dmp_status_date"),
                "shortage_reason": s.get("shortage_reason"),
                "shortage_period": None,
                "dmp_search_url": f"{DMP_BASE}?q={urllib.parse.quote(p['dmp_search'])}",
                "apotek_links": LINKS[p["key"]],
            })

    with_shortage = sum(1 for x in preps if x["has_shortage"] is True)
    unknown = sum(1 for x in preps if x["has_shortage"] is None)
    now = datetime.now(ZoneInfo("Europe/Oslo"))
    status = {
        "generated": now.isoformat(),
        "generated_display": now.strftime("%d.%m.%Y kl. %H:%M"),
        "source": "DMP / Felleskatalogen – automatisk ukentlig sjekk (lokal Mac)",
        "dmp_overview_url": DMP_BASE,
        "apotek_note": "Lenkene åpner søkeresultatet for preparatet hos hvert apotek. Klikk videre på pakningen for å se lagerstatus per apotek.",
        "summary": {"total": len(preps), "with_shortage": with_shortage,
                    "ok": len(preps) - with_shortage - unknown, "unknown": unknown},
        "preparations": preps,
    }
    return status, antall_sikre


def push_til_github(path: str, innhold: str, token: str):
    api = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{path}"
    req = urllib.request.Request(api, headers={"Authorization": f"token {token}", "User-Agent": "gynforum-mac"})
    try:
        with urllib.request.urlopen(req) as r:
            sha = json.loads(r.read())["sha"]
    except Exception:
        sha = None
    body = {"message": f"🔄 Automatisk DMP-sjekk {datetime.now().strftime('%d.%m.%Y')}",
            "content": base64.b64encode(innhold.encode()).decode()}
    if sha:
        body["sha"] = sha
    req = urllib.request.Request(api, data=json.dumps(body).encode(), method="PUT",
        headers={"Authorization": f"token {token}", "User-Agent": "gynforum-mac", "Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        if r.status not in (200, 201):
            raise RuntimeError(f"GitHub-feil {path}: {r.status}")


def main():
    from playwright.sync_api import sync_playwright

    token = les_token()
    now = datetime.now(ZoneInfo("Europe/Oslo"))
    print(f"\n{'='*52}")
    print(f"  GynForum DMP-sjekk – {now.strftime('%d.%m.%Y %H:%M')}")
    print(f"{'='*52}\n")

    print("→ Henter forrige status fra GitHub (for sikkerhet)...")
    forrige = hent_forrige_status(token)
    print(f"  Fant {len(forrige)} preparater i forrige versjon\n")

    logg = []
    status_map = {}
    print("→ Sjekker DMP for hvert preparat...\n")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        for p in PREPARATIONS:
            s = hent_dmp_status(page, p, logg)
            status_map[p["key"]] = s
            if s.get("sikker"):
                ikon = "⚠ MANGEL" if s.get("has_shortage") else "✓ OK"
            else:
                ikon = "? usikker (beholder forrige)"
            print(f"  {p['name']:18s} {ikon}")
        browser.close()

    # Bygg ny status med fallback
    status, antall_sikre = bygg_status(status_map, forrige, logg)

    # Detaljert logg
    print(f"\n{'─'*52}")
    print("  DETALJERT PARSING-LOGG:")
    for linje in logg:
        print(f"    {linje}")
    print(f"{'─'*52}\n")

    # Sikkerhetssjekk: avbryt hvis nesten ingenting ble lest sikkert
    if antall_sikre == 0:
        print("⚠ ADVARSEL: Ingen preparater kunne leses sikkert fra DMP.")
        print("  Pusher IKKE til GitHub – beholder eksisterende fil uendret.")
        print("  (DMP kan ha endret nettsiden, eller nettverket var nede.)\n")
        sys.exit(1)

    print(f"→ {antall_sikre} av {len(PREPARATIONS)} preparater lest sikkert.")
    print("→ Pusher til GitHub...")
    js = json.dumps(status, ensure_ascii=False, indent=2)
    push_til_github("data/status.json", js, token)
    push_til_github("docs/status.json", js, token)

    print(f"\n✓ FERDIG – {status['summary']['total']} rader, "
          f"{status['summary']['with_shortage']} med mangel, "
          f"{status['summary']['unknown']} ukjent\n")


if __name__ == "__main__":
    main()
