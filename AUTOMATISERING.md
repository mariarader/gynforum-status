# Helautomatisk DMP-sjekk via Val.town

GitHub Actions på denne kontoen kjører bak en nettverksproxy som blokkerer
eksterne nettsider. Derfor kjøres den automatiske ukentlige sjekken på
**Val.town** i stedet – en gratis tjeneste med full nettilgang.

## Oppsett (én gang, ca. 5 minutter)

### 1. Opprett konto
Gå til [val.town](https://www.val.town) og logg inn (gratis, bruk GitHub-innlogging).

### 2. Lag en ny Cron Val
- Klikk **New** → **Cron**
- Lim inn hele innholdet fra `valtown_dmp_check.ts`
- Sett schedule (cron-uttrykk): `0 7 * * 1`  (mandag kl. 07:00 UTC)

### 3. Legg inn to hemmeligheter
Gå til **Settings → Environment Variables** og legg til:

| Navn | Verdi |
|------|-------|
| `GITHUB_TOKEN` | Ditt GitHub PAT (samme som før, med `repo`-scope) |
| `ANTHROPIC_KEY` | Din Anthropic API-nøkkel (`sk-ant-...`) |

### 4. Test
Klikk **Run** manuelt i Val.town. Sjekk at den skriver
"✓ Oppdatert ... rader" i loggen, og at `data/status.json` på GitHub
får en ny commit fra "Automatisk DMP-sjekk".

## Hvordan det henger sammen

```
Val.town cron (mandag kl. 07)
    ↓ spør Claude API (web_search) om DMP-status
    ↓ bygger status.json
    ↓ pusher til GitHub (data/ + docs/)
GitHub Pages serverer docs/status.json
    ↓
gynforum.com/tilgjengelighet leser den og viser tabellen
```

Apoteklenkene og dosestrukturen er faste i scriptet – kun mangelstatusen
hentes live. Det gjør løsningen robust mot endringer i apotekenes nettsider.
