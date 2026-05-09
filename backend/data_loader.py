"""
Loads the medicine Excel file once at startup and normalizes
both the Drugs and OTC sheets into a single in-memory list of dicts.
"""
import pandas as pd
from typing import List, Dict, Any
import math


def _clean(value: Any) -> Any:
    """Convert NaN / 'Not Listed' / empty strings to None for clean JSON output."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, str):
        v = value.strip()
        if v == "" or v.lower() in {"nan", "not listed", "limited data available"}:
            return None
        return v
    return value


def _split_list(value: Any) -> List[str] | None:
    """Many fields are comma-separated strings — split them into clean arrays."""
    cleaned = _clean(value)
    if cleaned is None or not isinstance(cleaned, str):
        return None
    parts = [p.strip() for p in cleaned.split(",") if p.strip()]
    return parts or None


def _normalize_drug(row: pd.Series) -> Dict[str, Any]:
    """Map a Drugs sheet row to a unified medicine response shape."""
    return {
        "name": _clean(row.get("Medicine Name")),
        "category": "prescription",
        "prescription_required": _clean(row.get("Prescription")) == "Yes",
        "packaging": _clean(row.get("Type of Sell")),
        "manufacturer": _clean(row.get("Manufacturer")),
        "composition": _clean(row.get("Salt")),
        "mrp": _clean(row.get("MRP")),
        "availability": _clean(row.get("Status")),
        "uses": _split_list(row.get("Uses")),
        "side_effects": _split_list(row.get("Side Effects")),
        "alternate_medicines": _split_list(row.get("Alternate Medicines")),
        "how_to_use": _clean(row.get("How to Use")),
        "how_it_works": _clean(row.get("How It Works")),
        "chemical_class": _clean(row.get("Chemical Class")),
        "therapeutic_class": _clean(row.get("Therapeutic Class")),
        "action_class": _clean(row.get("Action Class")),
        "habit_forming": _clean(row.get("Habit Forming")) == "Yes",
        # OTC-only fields kept null for shape consistency
        "highlights": None,
        "product_info": None,
        "otc_category": None,
    }


def _normalize_otc(row: pd.Series) -> Dict[str, Any]:
    """Map an OTC sheet row into the same unified shape."""
    mrp = _clean(row.get("MRP"))
    # OTC MRPs are sometimes stored as strings or '[]' — try numeric coercion
    try:
        mrp = float(mrp) if mrp not in (None, "[]") else None
    except (TypeError, ValueError):
        mrp = None

    return {
        "name": _clean(row.get("OTC Name")),
        "category": "otc",
        "prescription_required": False,
        "packaging": _clean(row.get("Type of Sell")),
        "manufacturer": _clean(row.get("Manufacturer")),
        "composition": None,
        "mrp": mrp,
        "availability": "Available",
        "uses": None,
        "side_effects": None,
        "alternate_medicines": None,
        "how_to_use": None,
        "how_it_works": None,
        "chemical_class": None,
        "therapeutic_class": None,
        "action_class": None,
        "habit_forming": False,
        "highlights": _split_list(row.get("Product Highlights")),
        "product_info": _clean(row.get("Product Info")),
        "otc_category": _clean(row.get("Category")),
    }


def load_medicines(path: str = "medicines.xlsx") -> List[Dict[str, Any]]:
    """Load both sheets, normalize, and return a single combined list."""
    sheets = pd.read_excel(path, sheet_name=None)

    drugs_df = sheets.get("Drugs")
    otc_df = sheets.get("OTC")

    medicines: List[Dict[str, Any]] = []

    if drugs_df is not None:
        for _, row in drugs_df.iterrows():
            item = _normalize_drug(row)
            if item["name"]:
                medicines.append(item)

    if otc_df is not None:
        for _, row in otc_df.iterrows():
            item = _normalize_otc(row)
            if item["name"]:
                medicines.append(item)

    return medicines
