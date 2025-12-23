from __future__ import annotations

import json
import os
import re
from typing import List, Dict, Any, Optional, Tuple

# Project root and default OTC database path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OTC_DB_PATH = os.path.join(BASE_DIR, "data", "otc_db.json")


# ---------------------------------------------------------------------------
# Loading and indexing
# ---------------------------------------------------------------------------

def load_otc_db() -> List[Dict[str, Any]]:
    """Load the local OTC drug database and perform minimal structural validation."""
    with open(OTC_DB_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("OTC DB must be a list of records.")

    for entry in data:
        if not isinstance(entry, dict):
            raise ValueError("Each OTC DB entry must be a dict.")
        if "base_name" not in entry or "generic_name" not in entry:
            raise ValueError("Each entry must contain 'base_name' and 'generic_name'.")

    return data


OTC_DB: List[Dict[str, Any]] = load_otc_db()


def _normalize_name(name: str) -> str:
    """标准化名称：支持中文映射"""
    if not name: return ""
    
    mapping = {
        "维C": "vitamin c",
        "维生素C": "vitamin c",
        "维他命C": "vitamin c",
        "布洛芬": "ibuprofen",
        "对乙酰氨基酚": "acetaminophen",
        "阿司匹林": "aspirin"
    }
    
    n = name.strip().lower()

    return mapping.get(n, n)


def _build_name_index(
    db: List[Dict[str, Any]]
) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Build a flat index of (normalized_name, drug_entry).

    Names include:
      - generic_name
      - base_name
      - aliases (if present)
    """
    index: List[Tuple[str, Dict[str, Any]]] = []

    for entry in db:
        base_name = _normalize_name(entry.get("base_name", ""))
        generic_name = _normalize_name(entry.get("generic_name", ""))

        names = []
        if generic_name:
            names.append(generic_name)
        if base_name and base_name != generic_name:
            names.append(base_name)

        aliases = entry.get("aliases") or []
        for alias in aliases:
            if isinstance(alias, str):
                n = _normalize_name(alias)
                if n:
                    names.append(n)

        # de-duplicate
        seen = set()
        unique_names = []
        for n in names:
            if n not in seen:
                seen.add(n)
                unique_names.append(n)

        for n in unique_names:
            index.append((n, entry))

    return index


NAME_INDEX: List[Tuple[str, Dict[str, Any]]] = _build_name_index(OTC_DB)


# ---------------------------------------------------------------------------
# Matching helpers
# ---------------------------------------------------------------------------

def _build_word_boundary_pattern(name: str) -> re.Pattern:
    """
    Build a regex that matches the name as a whole word or token.

    This is a simple heuristic:
      - Case-insensitive
      - Allows punctuation / whitespace around the name
    """
    escaped = re.escape(name)
    pattern = rf"(?<!\w){escaped}(?!\w)"
    return re.compile(pattern, flags=re.IGNORECASE)


def _match_single_name_in_text(text: str, name: str) -> bool:
    """
    Return True if the given name appears in text with loose word boundaries.

    For English this helps avoid matching 'tan' inside 'tangent'.
    For Chinese this still behaves nicely because there is no word boundary.
    """
    if not name or len(name) < 2:
        return False

    pattern = _build_word_boundary_pattern(name)
    return bool(pattern.search(text))


# ---------------------------------------------------------------------------
# Public query functions
# ---------------------------------------------------------------------------

def find_drugs_in_text_raw(text: str) -> List[Dict[str, Any]]:
    """
    Find all preparations mentioned in the text.

    Returns raw preparation records (OTC_DB entries) without grouping.
    """
    text = text or ""
    if not text.strip():
        return []

    matched: List[Dict[str, Any]] = []
    seen_ids = set()

    for name, entry in NAME_INDEX:
        if id(entry) in seen_ids:
            continue
        if _match_single_name_in_text(text, name):
            matched.append(entry)
            seen_ids.add(id(entry))

    return matched


def group_by_base(preps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Group preparation entries by base_name so that different
    products for the same ingredient are aggregated.

    Returns a list of dicts:

      {
        "base_name": str,
        "generic_name": str,
        "aliases": [str],
        "preps": [original_entry, ...]
      }
    """
    groups: Dict[str, Dict[str, Any]] = {}

    for prep in preps:
        base = prep.get("base_name") or prep.get("generic_name") or ""
        base_norm = _normalize_name(base)

        if base_norm not in groups:
            groups[base_norm] = {
                "base_name": base,
                "generic_name": prep.get("generic_name") or base,
                "aliases": set(),   # temp set, convert to list later
                "preps": [],
            }

        group = groups[base_norm]
        group["preps"].append(prep)

        # collect aliases from all preps
        aliases = prep.get("aliases") or []
        for alias in aliases:
            if isinstance(alias, str):
                group["aliases"].add(alias)

        # also include generic_name itself as an alias for convenience
        if isinstance(prep.get("generic_name"), str):
            group["aliases"].add(prep["generic_name"])

    # finalize aliases sets into sorted lists
    result: List[Dict[str, Any]] = []
    for g in groups.values():
        g["aliases"] = sorted(list(g["aliases"]))
        result.append(g)

    # optional: sort groups by base_name
    result.sort(key=lambda x: x.get("base_name", ""))
    return result


def find_drugs_in_text(text: str) -> List[Dict[str, Any]]:
    """
    High-level API for the LLM:

      1. Match drug names in text using all known name variants.
      2. Group results by base_name so that different products of the same
         ingredient are aggregated.

    The returned structure is designed to be passed directly to the LLM.
    """
    raw_matches = find_drugs_in_text_raw(text)
    return group_by_base(raw_matches)


def find_preps_by_generic_name(name: str) -> List[Dict[str, Any]]:
    """
    Find all preparations whose generic_name or alias matches the given name.
    """
    name_norm = _normalize_name(name)
    if not name_norm:
        return []

    matches: List[Dict[str, Any]] = []
    for entry in OTC_DB:
        g = _normalize_name(entry.get("generic_name", ""))
        if g == name_norm:
            matches.append(entry)
            continue

        aliases = entry.get("aliases") or []
        for alias in aliases:
            if isinstance(alias, str) and _normalize_name(alias) == name_norm:
                matches.append(entry)
                break

    return matches


def find_by_generic_name(name: str):
    if not name:
        return None

    SYNONYMS = {
        "维C": "VITAMIN C",
        "维生素C": "VITAMIN C",
        "维他命C": "VITAMIN C",
        "ASCORBIC ACID": "VITAMIN C",
        "布洛芬": "IBUPROFEN",
        "对乙酰氨基酚": "ACETAMINOPHEN",
        "阿司匹林": "ASPIRIN"
    }

    raw_name = name.strip()

    search_name = SYNONYMS.get(raw_name, SYNONYMS.get(raw_name.upper(), raw_name.upper()))

    for drug in OTC_DB:
        if search_name == (drug.get("generic_name") or "").upper():
            return drug
        
        aliases_upper = [str(a).upper() for a in drug.get("aliases", [])]
        if search_name in aliases_upper:
            return drug
            
        if search_name in (drug.get("base_name") or "").upper():
            return drug

    return None