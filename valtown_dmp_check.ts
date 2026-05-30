// ============================================================
// GynForum – Ukentlig DMP-tilgjengelighetssjekk
// Kjører på Val.town (gratis), oppdaterer status.json på GitHub
// ============================================================
//
// OPPSETT (gjøres én gang, se instruksjoner nederst):
//   1. Lim inn denne koden i en ny "Cron Val" på val.town
//   2. Sett to Environment Variables under Settings:
//        GITHUB_TOKEN  = ditt GitHub PAT (repo-scope)
//        ANTHROPIC_KEY = din Anthropic API-nøkkel (sk-ant-...)
//   3. Sett cron-schedule til:  0 7 * * 1   (mandag kl. 07 UTC)
//
// ============================================================

const GITHUB_OWNER = "mariarader";
const GITHUB_REPO = "gynforum-status";
const DMP_BASE =
  "https://www.dmp.no/forsyningssikkerhet/legemiddelmangel/oversikt-over-legemiddelmangel---for-pasienter-og-helsepersonell";

// Faste apoteklenker per preparat (de ekte lenkene du fant)
const LINKS = {
  estradot: {
    "Apotek 1": "https://www.apotek1.no/soek/estradot?searchTerm=estradot&sortMethod=0&pageSize=20&pageNumber=1&categoryId=&facets=&previousCategoryId=#load-more-potential",
    "Vitusapotek": "https://www.vitusapotek.no/search?text=estradot%20dep%20plast",
    "Boots": "https://www.boots.no/search/result/?q=estradot",
    "Farmasiet": "https://www.farmasiet.no/search?searchPhrase=estradot&orderBy=0",
  },
  estradiol_hexal: {
    "Apotek 1": "https://www.apotek1.no/soek/Estradiol%20Hex%20?searchTerm=Estradiol%20Hex%20&sortMethod=0&pageSize=20&pageNumber=1&categoryId=&facets=&previousCategoryId=#load-more-potential",
    "Vitusapotek": "https://www.vitusapotek.no/search?text=estradiol%20hex",
    "Boots": "https://www.boots.no/search/result/?q=estradiol+hexal",
    "Farmasiet": "https://www.farmasiet.no/search?searchPhrase=estradiol+hexal&orderBy=0",
  },
  estrogel: {
    "Apotek 1": "https://www.apotek1.no/produkter/estrogel-transdermalgel-0-75mg-95339p",
    "Vitusapotek": "https://www.vitusapotek.no/reseptbelagte-legemidler/g-urogenitalsystem-og-kjonnshormoner/g03-kjonnshormoner-og-midler-med-effekt-pa-g/g03ca-naturlige-og-halvsyntetiske-ostrogeneru/estrogel-transdermalgel-075mg-1-x-80-g-095339",
    "Boots": "https://www.boots.no/search/result/?q=estrogel",
    "Farmasiet": "https://www.farmasiet.no/catalog/reseptvarer/g03-kjonnshormoner-og-midler-med-effekt-pa-genitalia2/estrogel-transdermalgel-075mgdos-1-x-80-g.-flaske-av-plast-med-dosepumpe,5024071",
  },
  lenzetto: {
    "Apotek 1": "https://www.apotek1.no/soek/lenzetto?searchTerm=lenzetto&sortMethod=0&pageSize=20&pageNumber=1&categoryId=&facets=&previousCategoryId=#load-more-potential",
    "Vitusapotek": "https://www.vitusapotek.no/search?text=lenzetto",
    "Boots": "https://www.boots.no/search/result/?q=lenzetto",
    "Farmasiet": "https://www.farmasiet.no/search?searchPhrase=lenzetto&orderBy=0",
  },
  progynova: {
    "Apotek 1": "https://www.apotek1.no/soek/progynova?searchTerm=progynova&sortMethod=0&pageSize=20&pageNumber=1&categoryId=&facets=&previousCategoryId=#load-more-potential",
    "Vitusapotek": "https://www.vitusapotek.no/search?text=Progynova",
    "Boots": "https://www.boots.no/search/result/?q=progynova",
    "Farmasiet": "https://www.farmasiet.no/search?searchPhrase=progynova",
  },
};

// Preparater og doser (struktur er fast, status hentes live)
const PREPARATIONS = [
  { key: "estradot", name: "Estradot", form: "Plaster", type: "systemisk", dmpSearch: "Estradot",
    doses: ["25 µg/24t", "37,5 µg/24t", "50 µg/24t", "75 µg/24t", "100 µg/24t"] },
  { key: "estradiol_hexal", name: "Estradiol Hexal", form: "Plaster", type: "systemisk", dmpSearch: "Estradiol Hexal",
    doses: ["25 µg/24t", "37,5 µg/24t", "50 µg/24t", "75 µg/24t", "100 µg/24t"] },
  { key: "estrogel", name: "Estrogel", form: "Gel", type: "systemisk", dmpSearch: "Estrogel",
    doses: ["0,75 mg/trykk"] },
  { key: "lenzetto", name: "Lenzetto", form: "Spray", type: "systemisk", dmpSearch: "Lenzetto",
    doses: ["1,53 mg/spray"] },
  { key: "progynova", name: "Progynova", form: "Tablett", type: "systemisk", dmpSearch: "Progynova",
    doses: ["1 mg", "2 mg"] },
];

// ---- Spør Claude (med web_search) om aktuell DMP-status ----
async function fetchShortageStatus(): Promise<Record<string, any>> {
  const apiKey = Deno.env.get("ANTHROPIC_KEY");
  const names = PREPARATIONS.map((p) => p.name).join(", ");

  const prompt = `Sjekk DMP (Direktoratet for medisinske produkter, dmp.no) sin oversikt over legemiddelmangel for disse norske østrogenpreparatene: ${names}.

Søk på nett for hvert preparat. Returner KUN en JSON-array, ingen annen tekst:
[{"key":"estradot","has_shortage":true,"dmp_status":"Pågående","dmp_status_date":"DD.MM.ÅÅÅÅ","shortage_reason":"kort årsak"}, ...]

Bruk disse nøklene: estradot, estradiol_hexal, estrogel, lenzetto, progynova.
has_shortage=true kun hvis DMP melder pågående mangel. Hvis ingen mangel: has_shortage=false, dmp_status="Ingen meldt mangel", dmp_status_date=null, shortage_reason=null.`;

  const res = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "x-api-key": apiKey!,
      "anthropic-version": "2023-06-01",
      "content-type": "application/json",
    },
    body: JSON.stringify({
      model: "claude-sonnet-4-20250514",
      max_tokens: 1500,
      tools: [{ type: "web_search_20250305", name: "web_search" }],
      messages: [{ role: "user", content: prompt }],
    }),
  });

  const data = await res.json();
  const text = (data.content || [])
    .filter((b: any) => b.type === "text")
    .map((b: any) => b.text)
    .join("");

  const match = text.match(/\[[\s\S]*\]/);
  if (!match) throw new Error("Fant ikke JSON i Claude-svar");
  const arr = JSON.parse(match[0]);
  const map: Record<string, any> = {};
  for (const item of arr) map[item.key] = item;
  return map;
}

// ---- Bygg status.json ----
function buildStatus(statusMap: Record<string, any>) {
  const preps: any[] = [];
  for (const p of PREPARATIONS) {
    const s = statusMap[p.key] || {};
    const hasShortage = s.has_shortage ?? null;
    for (const dose of p.doses) {
      preps.push({
        id: `${p.key}_${dose.split(" ")[0].replace(",", "")}`,
        name: p.name, dose, form: p.form, type: p.type,
        has_shortage: hasShortage,
        dmp_status: s.dmp_status ?? "Ukjent",
        dmp_status_date: s.dmp_status_date ?? null,
        shortage_reason: s.shortage_reason ?? null,
        shortage_period: null,
        dmp_search_url: `${DMP_BASE}?q=${encodeURIComponent(p.dmpSearch)}`,
        apotek_links: LINKS[p.key as keyof typeof LINKS],
      });
    }
  }
  const withShortage = preps.filter((x) => x.has_shortage === true).length;
  const unknown = preps.filter((x) => x.has_shortage === null).length;
  const now = new Date();
  const display = now.toLocaleString("no-NO", {
    timeZone: "Europe/Oslo", day: "2-digit", month: "2-digit",
    year: "numeric", hour: "2-digit", minute: "2-digit",
  });
  return {
    generated: now.toISOString(),
    generated_display: display.replace(",", " kl."),
    source: "DMP / Felleskatalogen via Claude web_search – automatisk ukentlig (Val.town)",
    dmp_overview_url: DMP_BASE,
    apotek_note: "Lenkene åpner søkeresultatet for preparatet hos hvert apotek. Klikk videre på pakningen for å se lagerstatus per apotek.",
    summary: { total: preps.length, with_shortage: withShortage, ok: preps.length - withShortage - unknown, unknown },
    preparations: preps,
  };
}

// ---- Push til GitHub (begge filer) ----
async function pushToGitHub(path: string, content: string) {
  const token = Deno.env.get("GITHUB_TOKEN");
  const apiUrl = `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/contents/${path}`;

  // Hent eksisterende SHA
  const getRes = await fetch(apiUrl, {
    headers: { Authorization: `token ${token}`, "User-Agent": "gynforum-bot" },
  });
  const existing = await getRes.json();
  const sha = existing.sha;

  const body: any = {
    message: `🔄 Automatisk DMP-sjekk ${new Date().toLocaleDateString("no-NO")}`,
    content: btoa(unescape(encodeURIComponent(content))),
  };
  if (sha) body.sha = sha;

  const putRes = await fetch(apiUrl, {
    method: "PUT",
    headers: {
      Authorization: `token ${token}`,
      "User-Agent": "gynforum-bot",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!putRes.ok) throw new Error(`GitHub-feil ${path}: ${putRes.status}`);
}

// ---- Hovedfunksjon (kjøres av cron) ----
export default async function () {
  const statusMap = await fetchShortageStatus();
  const status = buildStatus(statusMap);
  const json = JSON.stringify(status, null, 2);

  await pushToGitHub("data/status.json", json);
  await pushToGitHub("docs/status.json", json);

  console.log(`✓ Oppdatert ${status.summary.total} rader, ${status.summary.with_shortage} med mangel`);
  return status.summary;
}
