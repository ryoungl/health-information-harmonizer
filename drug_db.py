from __future__ import annotations

import json
import os
from typing import List, Dict, Any, Optional

# Project root and default OTC database path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OTC_DB_PATH = os.path.join(BASE_DIR, "data", "otc_db.json")


def load_otc_db() -> List[Dict[str, Any]]:
    """Load the local OTC drug database and perform minimal structural validation."""
    with open(OTC_DB_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("The top level of otc_db.json must be a list.")
    return data


def is_chinese(s: str) -> bool:
    """Heuristic check to see if a string contains Chinese characters."""
    for ch in s:
        if "\u4e00" <= ch <= "\u9fff":
            return True
    return False


# Preload database at module import time.
OTC_DB: List[Dict[str, Any]] = load_otc_db()

# In-memory indexes for fast lookups
GENERIC_INDEX: Dict[str, List[Dict[str, Any]]] = {}
BASE_INDEX: Dict[str, List[Dict[str, Any]]] = {}

# All name variants that can be used for matching:
#   key: normalized name (lowercase for non-Chinese, raw for Chinese)
#   value: list of drug records
NAME_VARIANTS: Dict[str, List[Dict[str, Any]]] = {}


def _normalize_name_for_index(name: str) -> str:
    """Normalize names: keep Chinese unchanged; lowercase all non-Chinese."""
    if not name:
        return ""
    if is_chinese(name):
        return name
    return name.lower()


def build_indexes() -> None:
    """Build in-memory indexes from OTC_DB for fast lookup and aggregation."""
    GENERIC_INDEX.clear()
    BASE_INDEX.clear()
    NAME_VARIANTS.clear()

    for drug in OTC_DB:
        generic_name = drug.get("generic_name", "")
        base_name = drug.get("base_name", "")
        aliases: List[str] = drug.get("aliases", []) or []

        # Index by generic_name
        if generic_name:
            GENERIC_INDEX.setdefault(generic_name, []).append(drug)

        # Index by base_name
        if base_name:
            BASE_INDEX.setdefault(base_name, []).append(drug)

        # All available name variants: generic_name + aliases.
        all_names = set()
        if generic_name:
            all_names.add(generic_name)
        for alias in aliases:
            if alias:
                all_names.add(alias)

        for name in all_names:
            key = _normalize_name_for_index(name)
            if not key:
                continue
            NAME_VARIANTS.setdefault(key, []).append(drug)


# Build indexes eagerly when the module is imported
build_indexes()


def find_preps_by_generic_name(name: str) -> List[Dict[str, Any]]:
    """Exact lookup by generic name, e.g. 'Ibuprofen SR tablets'."""
    return GENERIC_INDEX.get(name, [])


def find_preps_by_base_name(base_name: str) -> List[Dict[str, Any]]:
    """Lookup all preparations under a base_name, e.g. 'Ibuprofen' → tablets, SR tablets, oral suspension."""
    return BASE_INDEX.get(base_name, [])


def list_all_bases() -> List[str]:
    """Return all base_name keys, useful for debugging or feeding UI dropdowns."""
    return sorted(BASE_INDEX.keys())


def _match_single_name_in_text(text: str, name: str) -> bool:
    """Match a single name in text with language-aware case handling."""
    if not name:
        return False
    if is_chinese(name):
        return name in text
    # For non-Chinese names, match case-insensitively
    return name.lower() in text.lower()


def find_drugs_in_text_raw(text: str) -> List[Dict[str, Any]]:
    """
    Match all configured name variants in a text.

    Returns raw preparation records without grouping by base_name.
    Supports Chinese names and English/brand aliases.
    """
    text = text or ""
    if not text.strip():
        return []

    matched: List[Dict[str, Any]] = []
    seen_ids = set()

    for key_name, drugs in NAME_VARIANTS.items():
        for drug in drugs:
            generic_name = drug.get("generic_name", "")
            aliases: List[str] = drug.get("aliases", []) or []

            # Avoid adding duplicates.
            identity = id(drug)
            if identity in seen_ids:
                continue

            # Try matching using generic name and aliases one by one.
            candidates = []
            if generic_name:
                candidates.append(generic_name)
            candidates.extend(aliases)

            if any(_match_single_name_in_text(text, n) for n in candidates):
                matched.append(drug)
                seen_ids.add(identity)

    return matched


def group_by_base(drugs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Group drug records by their base_name.

    Input: list of specific preparation records.
    Output:
    [
    {
        "base_name": "Ibuprofen",
        "preparations": [ {...}, ... ]
    }
    ]
    """

    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for drug in drugs:
        base = drug.get("base_name") or drug.get("generic_name") or ""
        if not base:
            continue
        grouped.setdefault(base, []).append(drug)

    result: List[Dict[str, Any]] = []
    for base_name, preps in grouped.items():
        result.append(
            {
                "base_name": base_name,
                "preparations": preps,
            }
        )
    return result


def find_drugs_in_text(text: str) -> List[Dict[str, Any]]:
    """
    High level API:

    1. Match drug names in text using all name variants.
    2. Group results by base_name so that different preparations of the same ingredient are aggregated.

    The returned structure is designed to be passed directly to the LLM.
    """

    raw_matches = find_drugs_in_text_raw(text)
    return group_by_base(raw_matches)

def find_by_generic_name(name: str) -> Optional[Dict[str, Any]]:
    preps = find_preps_by_generic_name(name)
    if preps:
        return preps[0]
    return None