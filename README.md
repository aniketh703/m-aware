# Prescription Assistant API

A lightweight FastAPI service that powers the Prescription Assistant chat bot.
Takes a medicine name (exact, partial, or even with typos) and returns full
details — uses, side effects, composition, alternates, and more.

**Data source:** `medicines.xlsx` — 194 prescription drugs + 120 OTC products = **314 records**.

---

## Quick start

```bash
# 1. Install
pip install -r requirements.txt

# 2. Run
uvicorn main:app --reload --port 8000

# 3. Open auto-generated interactive docs
open http://localhost:8000/docs
```

That's it. Swagger UI lets you try every endpoint without writing a single line of frontend code.

---

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Liveness check |
| `GET` | `/medicine?name={q}` | **Primary bot endpoint.** Exact + fuzzy fallback |
| `GET` | `/medicine/{name}` | Strict exact lookup, 404 on miss |
| `GET` | `/search?q={q}&limit=5` | Top-N fuzzy matches (autocomplete) |
| `GET` | `/medicines?category={prescription\|otc}` | Full name list |

---

## The endpoint your bot will use most

### `GET /medicine?name={query}`

This is the one to wire into the chat input. It always returns a structured
response — never a 404 — so the bot logic stays simple.

**Three response shapes:**

```jsonc
// Exact match
{ "matched": true, "match_type": "exact", "score": 100, "medicine": {...}, "suggestions": [] }

// Fuzzy match (≥ 80 confidence) — bot can show this directly
{ "matched": true, "match_type": "fuzzy", "score": 90, "medicine": {...}, "suggestions": [...] }

// Low confidence — bot should ask "Did you mean...?"
{ "matched": false, "match_type": "none", "score": 40, "medicine": null, "suggestions": [...] }
```

**Example — typo handled gracefully:**

```bash
curl "http://localhost:8000/medicine?name=Dilcorr%2060"
```

```json
{
  "matched": true,
  "match_type": "fuzzy",
  "score": 85,
  "medicine": {
    "name": "Dilcor 60mg Tablet",
    "category": "prescription",
    "prescription_required": true,
    "composition": "Diltiazem (60mg)",
    "mrp": 34.41,
    "uses": ["Hypertension (high blood pressure)", "Angina (heart-related chest pain)", "Treatment of Arrhythmia"],
    "side_effects": ["Headache", "Dizziness", "Nausea", "Edema (swelling)"],
    "alternate_medicines": ["Dilcardia 60mg Tablet", "Cardem 60mg Tablet", "..."],
    "how_to_use": "Take this medicine in the dose and duration as advised...",
    "how_it_works": "Dilcor 60mg Tablet is used to treat angina...",
    "manufacturer": "Mano Pharma Pvt Ltd"
  },
  "suggestions": [...]
}
```

---

## Response schema (unified for prescription + OTC)

| Field | Type | Notes |
|---|---|---|
| `name` | string | Canonical medicine name |
| `category` | `"prescription"` \| `"otc"` | Which sheet it came from |
| `prescription_required` | bool | |
| `composition` | string \| null | Salt / active ingredients |
| `mrp` | number \| null | INR |
| `uses` | string[] \| null | Pre-split into array |
| `side_effects` | string[] \| null | Pre-split into array |
| `alternate_medicines` | string[] \| null | |
| `how_to_use` | string \| null | |
| `how_it_works` | string \| null | |
| `chemical_class` / `therapeutic_class` / `action_class` | string \| null | |
| `habit_forming` | bool | |
| `manufacturer` | string \| null | |
| `packaging` | string \| null | e.g. "10 tablets in 1 strip" |
| `availability` | string \| null | |
| `highlights` / `product_info` / `otc_category` | OTC-only | null for prescription |

Comma-separated cells (uses, side effects, alternates) are **already parsed into
arrays** so the bot can render them as bullet lists with no extra work.
`"Not Listed"` and `"Limited data available"` placeholders are normalized to `null`.

---

## Frontend integration (your bot)

Drop this into the bot's send handler:

```js
async function lookupMedicine(userInput) {
  const r = await fetch(
    `${API_BASE}/medicine?name=${encodeURIComponent(userInput)}`
  );
  const data = await r.json();

  if (!data.matched) {
    // Show "Did you mean...?" with data.suggestions
    return { type: "suggest", suggestions: data.suggestions };
  }

  // Render full medicine card from data.medicine
  return { type: "result", medicine: data.medicine, fuzzy: data.match_type === "fuzzy" };
}
```

If you're using the API to format a chat-ready string:

```js
function toBotMessage(med) {
  const lines = [`💊 **${med.name}**`];
  if (med.composition)  lines.push(`Composition: ${med.composition}`);
  if (med.uses)         lines.push(`Uses: ${med.uses.join(", ")}`);
  if (med.side_effects) lines.push(`⚠️ Side Effects: ${med.side_effects.join(", ")}`);
  if (med.how_to_use)   lines.push(`How to use: ${med.how_to_use}`);
  return lines.join("\n\n");
}
```

---

## CORS

Currently `allow_origins=["*"]` for local development.
**Before deploying, lock this down** to your bot's domain in `main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-bot.example.com"],
    allow_methods=["GET"],
)
```

---

## Deployment

The whole service is one folder + `requirements.txt`. Drop-in deploy targets:

- **Render** — point at this repo, build = `pip install -r requirements.txt`, start = `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Railway / Fly.io** — same start command
- **Docker** — 5-line Dockerfile (FROM python → COPY → pip install → CMD uvicorn)

---

## Safety note for the bot UI

This dataset is informational — **the bot should disclose that it is not a
substitute for professional medical advice** and recommend consulting a doctor
for prescription decisions. Worth surfacing in the bot's system message and
near any "side effects" rendering.

---

## Project files

```
prescription-api/
├── main.py            # FastAPI app + endpoints
├── data_loader.py     # Excel → normalized in-memory list
├── medicines.xlsx     # Source data (Drugs + OTC sheets)
├── test_api.py        # Smoke test covering all endpoints
├── requirements.txt
└── README.md
```
