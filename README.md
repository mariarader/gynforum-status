# GynForum – Tilgjengelighetsovervåkning

Automatisk ukentlig sjekk av DMP-mangelmeldinger for østrogenpreparater i Norge.

## Hvordan det fungerer

```
GitHub Actions (hver mandag kl. 07:00 UTC)
    ↓
fetch_status.py henter Felleskatalog-sider per preparat
    ↓
Parser DMP-status ("Status pr. DD.MM.ÅÅÅÅ: Pågående/Avsluttet")
    ↓
Skriver data/status.json til repo
    ↓
docs/index.html leser status.json og viser tabellen
```

## Oppsett (én gang)

### 1. Opprett GitHub-repo

```bash
git init gynforum-status
cd gynforum-status
# Kopier alle filer hit
git add .
git commit -m "Første oppsett"
git remote add origin https://github.com/DITTBRUKERNAVN/gynforum-status.git
git push -u origin main
```

### 2. Aktiver GitHub Pages

Gå til **Settings → Pages** i repoet ditt og velg:
- Source: `Deploy from a branch`
- Branch: `main`
- Folder: `/docs`

Siden blir da tilgjengelig på:
`https://DITTBRUKERNAVN.github.io/gynforum-status/`

### 3. Gi Actions skriverettigheter

Gå til **Settings → Actions → General → Workflow permissions**  
og velg **Read and write permissions**.

### 4. Test manuelt

Gå til **Actions → Ukentlig tilgjengelighetssjekk → Run workflow**  
for å kjøre sjekken med en gang uten å vente til mandag.

## Filer

| Fil | Beskrivelse |
|-----|-------------|
| `fetch_status.py` | Python-skript som henter og parser status fra Felleskatalogen |
| `.github/workflows/weekly_check.yml` | GitHub Actions workflow – kjører hver mandag |
| `data/status.json` | Generert statusdata – oppdateres automatisk |
| `docs/index.html` | Statussiden som vises til brukerne |

## Integrere på GynForum (Webflow)

Legg inn en iframe på Webflow-siden din:

```html
<iframe
  src="https://DITTBRUKERNAVN.github.io/gynforum-status/"
  width="100%"
  height="700"
  frameborder="0"
  style="border-radius:12px;">
</iframe>
```

Eller lenk direkte til siden fra preparatoversikten.

## Oppdatere preparatlisten

Legg til eller endre preparater i `PREPARATIONS`-listen i `fetch_status.py`.  
Kjør `python fetch_status.py` lokalt for å teste, deretter push til GitHub.

## Kilde og ansvarsfraskrivelse

Data hentes fra [Felleskatalogen](https://www.felleskatalogen.no) og  
[Direktoratet for medisinske produkter (DMP)](https://www.dmp.no).  
Siden er faglig informasjon og erstatter ikke individuell medisinsk rådgivning.
