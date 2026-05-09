"""
Prescription Assistant API
--------------------------
A small FastAPI service that exposes medicine details (uses, side effects,
composition, alternates, etc.) for the Prescription Assistant frontend bot.

Run locally:
    uvicorn main:app --reload --port 8000

Interactive docs auto-generated at:
    http://localhost:8000/docs
"""
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from rapidfuzz import process, fuzz

from data_loader import load_medicines


# ---------- Pydantic response models ----------

class Medicine(BaseModel):
    """Unified medicine record — same shape for prescription drugs and OTC items."""
    name: str
    category: str = Field(..., description="'prescription' or 'otc'")
    prescription_required: bool
    packaging: Optional[str] = None
    manufacturer: Optional[str] = None
    composition: Optional[str] = None
    mrp: Optional[float] = None
    availability: Optional[str] = None
    uses: Optional[List[str]] = None
    side_effects: Optional[List[str]] = None
    alternate_medicines: Optional[List[str]] = None
    how_to_use: Optional[str] = None
    how_it_works: Optional[str] = None
    chemical_class: Optional[str] = None
    therapeutic_class: Optional[str] = None
    action_class: Optional[str] = None
    habit_forming: bool = False
    highlights: Optional[List[str]] = None
    product_info: Optional[str] = None
    otc_category: Optional[str] = None


class SearchHit(BaseModel):
    """Lightweight hit for search/autocomplete responses."""
    name: str
    category: str
    score: int = Field(..., description="Fuzzy match confidence, 0-100")
    composition: Optional[str] = None
    manufacturer: Optional[str] = None


class MedicineLookupResponse(BaseModel):
    """Response wrapper for the primary /medicine endpoint."""
    matched: bool
    match_type: str = Field(..., description="'exact', 'fuzzy', or 'none'")
    score: int = Field(..., description="0-100; 100 means exact match")
    medicine: Optional[Medicine] = None
    suggestions: List[SearchHit] = Field(default_factory=list)


# ---------- App lifecycle: load data once at startup ----------

class _State:
    medicines: List[dict] = []
    name_index: List[str] = []  # parallel list of lowercased names for fuzzy matching


@asynccontextmanager
async def lifespan(app: FastAPI):
    _State.medicines = load_medicines("medicines.xlsx")
    _State.name_index = [m["name"].lower() for m in _State.medicines]
    print(f"[startup] Loaded {len(_State.medicines)} medicines.")
    yield


app = FastAPI(
    title="Prescription Assistant API",
    description=(
        "Lookup API for medicine details — uses, side effects, composition, "
        "alternates, and more. Built for the Prescription Assistant chat bot."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Wide-open CORS so any frontend (local dev, deployed bot) can call this.
# Tighten allow_origins to your bot's domain in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ---------- Helpers ----------

def _find_exact(name: str) -> Optional[dict]:
    target = name.strip().lower()
    for m in _State.medicines:
        if m["name"].lower() == target:
            return m
    return None


def _fuzzy_search(query: str, limit: int = 5, score_cutoff: int = 50):
    """Return list of (medicine_dict, score) tuples ranked by similarity."""
    matches = process.extract(
        query.lower(),
        _State.name_index,
        scorer=fuzz.WRatio,
        limit=limit,
        score_cutoff=score_cutoff,
    )
    # process.extract returns (matched_string, score, index)
    return [(_State.medicines[idx], int(score)) for _, score, idx in matches]


# ---------- Endpoints ----------

@app.get("/health", tags=["meta"])
def health():
    """Liveness probe — also reports how many medicines are loaded."""
    return {"status": "ok", "medicines_loaded": len(_State.medicines)}


@app.get("/medicines", tags=["catalog"])
def list_medicines(
    category: Optional[str] = Query(
        None,
        description="Filter by 'prescription' or 'otc'. Omit for all.",
    ),
    limit: int = Query(500, ge=1, le=1000),
):
    """List all medicine names (for autocomplete on the frontend)."""
    items = _State.medicines
    if category:
        items = [m for m in items if m["category"] == category]
    return {
        "count": len(items[:limit]),
        "total": len(items),
        "items": [
            {"name": m["name"], "category": m["category"]}
            for m in items[:limit]
        ],
    }


@app.get("/search", response_model=List[SearchHit], tags=["lookup"])
def search(
    q: str = Query(..., min_length=1, description="Search query (name fragment)"),
    limit: int = Query(5, ge=1, le=20),
):
    """
    Fuzzy search across all medicine names. Returns top matches ranked by
    similarity. Use this for autocomplete or when the user's input is ambiguous.
    """
    hits = _fuzzy_search(q, limit=limit, score_cutoff=40)
    return [
        SearchHit(
            name=m["name"],
            category=m["category"],
            score=score,
            composition=m.get("composition"),
            manufacturer=m.get("manufacturer"),
        )
        for m, score in hits
    ]


@app.get("/medicine", response_model=MedicineLookupResponse, tags=["lookup"])
def get_medicine(
    name: str = Query(..., min_length=1, description="Medicine name (exact or partial)"),
):
    """
    PRIMARY ENDPOINT for the chat bot.

    Behavior:
      1. Tries exact (case-insensitive) match → returns full details.
      2. Falls back to fuzzy match. If the top score >= 80, returns that
         medicine plus other suggestions.
      3. If no good match, returns matched=false with up to 5 suggestions
         the bot can show as "Did you mean ...?"
    """
    # 1. Exact match
    exact = _find_exact(name)
    if exact:
        return MedicineLookupResponse(
            matched=True,
            match_type="exact",
            score=100,
            medicine=Medicine(**exact),
            suggestions=[],
        )

    # 2. Fuzzy fallback
    hits = _fuzzy_search(name, limit=5, score_cutoff=40)
    if not hits:
        return MedicineLookupResponse(
            matched=False,
            match_type="none",
            score=0,
            medicine=None,
            suggestions=[],
        )

    top_med, top_score = hits[0]
    other_suggestions = [
        SearchHit(
            name=m["name"],
            category=m["category"],
            score=score,
            composition=m.get("composition"),
            manufacturer=m.get("manufacturer"),
        )
        for m, score in hits[1:]
    ]

    if top_score >= 80:
        return MedicineLookupResponse(
            matched=True,
            match_type="fuzzy",
            score=top_score,
            medicine=Medicine(**top_med),
            suggestions=other_suggestions,
        )

    # Low confidence → don't auto-pick. Let the bot ask the user.
    all_hits = [
        SearchHit(
            name=m["name"],
            category=m["category"],
            score=score,
            composition=m.get("composition"),
            manufacturer=m.get("manufacturer"),
        )
        for m, score in hits
    ]
    return MedicineLookupResponse(
        matched=False,
        match_type="none",
        score=top_score,
        medicine=None,
        suggestions=all_hits,
    )


@app.get("/medicine/{name}", response_model=Medicine, tags=["lookup"])
def get_medicine_by_path(name: str):
    """
    Path-style exact lookup. Returns 404 if not found (no fuzzy fallback).
    Useful when the frontend already has the canonical name from /search.
    """
    exact = _find_exact(name)
    if not exact:
        raise HTTPException(status_code=404, detail=f"Medicine '{name}' not found")
    return Medicine(**exact)
