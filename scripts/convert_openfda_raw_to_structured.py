#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Convert a raw openFDA-based DB into the structured OTC DB schema
expected by drug_db.py.

Input:
  data/otc_db_openfda_raw.json
    [
      {
        "generic_query": "ibuprofen",
        "label_raw": {...},   # openFDA drug/label entry
        "ndc_raw": {...}      # openFDA drug/ndc entry (optional)
      },
      ...
    ]

Output:
  data/otc_db.json
    [
      {
        "base_name": "ibuprofen",
        "generic_name": "ibuprofen",
        "aliases": [...],
        "category": "...",
        "indications": [...],
        "contraindications": [...],
        "cautions": [...],
        "age_note": "...",
        "important_warnings": [...]
      },
      ...
    ]

We only use a small subset of openFDA fields:
  - label.openfda.generic_name / brand_name / substance_name / route / pharm_class_*
  - label.indications_and_usage / uses
  - label.contraindications
  - label.warnings / warnings_and_cautions / precautions
  - label.boxed_warning
  - label.pediatric_use / geriatric_use
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

RAW_DB_PATH = DATA_DIR / "otc_db_openfda_raw.json"
STRUCTURED_DB_PATH = DATA_DIR / "otc_db.json"

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )


def ensure_list(value: Any) -> List[str]:
    """Normalize openFDA fields into a list of strings."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v not in (None, "")]
    return [str(value)]


def first_or_none(value: Any) -> Optional[str]:
    """Return the first item if value is a list, otherwise value as a string."""
    if value is None:
        return None
    if isinstance(value, list):
        return str(value[0]) if value else None
    return str(value)


def extract_from_label(label: Dict[str, Any], generic_fallback: str) -> Dict[str, Any]:
    """
    Map a single openFDA label entry into our structured fields.
    """
    ofd = label.get("openfda") or {}

    # generic_name: try openfda.generic_name first, otherwise fallback to generic_query
    generic_name = first_or_none(ofd.get("generic_name")) or generic_fallback
    generic_name = generic_name.strip() if generic_name else generic_fallback

    # base_name: lowercased generic_name for indexing
    base_name = generic_name.lower()

    # aliases: generic_name + brand_name + substance_name + route 等
    aliases: List[str] = []

    if generic_name:
        aliases.append(generic_name)

    brand_names = ensure_list(ofd.get("brand_name"))
    substance_names = ensure_list(ofd.get("substance_name"))
    routes = ensure_list(ofd.get("route"))

    aliases.extend(brand_names)
    aliases.extend(substance_names)

    # category
    pharm_classes = []
    for key in ["pharm_class_epc", "pharm_class_pe", "pharm_class_cs", "pharm_class_moa"]:
        pharm_classes.extend(ensure_list(ofd.get(key)))

    category = pharm_classes[0] if pharm_classes else ""

    if category:
        clean_cat = category.split('[')[0].strip().upper()
        if clean_cat and clean_cat not in [a.upper() for a in aliases]:
            aliases.append(clean_cat)
            logger.debug(f"Added category alias: {clean_cat}")

    seen = set()
    alias_clean: List[str] = []
    for a in aliases:
        a_norm = a.strip()
        if not a_norm:
            continue
        low = a_norm.lower()
        if low in seen:
            continue
        seen.add(low)
        alias_clean.append(a_norm)

    # indications
    indications = []
    indications.extend(ensure_list(label.get("indications_and_usage")))
    indications.extend(ensure_list(label.get("uses")))

    # contraindications
    contraindications = ensure_list(label.get("contraindications"))

    # warnings / cautions
    warnings = []
    warnings.extend(ensure_list(label.get("warnings")))
    warnings.extend(ensure_list(label.get("warnings_and_cautions")))
    precautions = ensure_list(label.get("precautions"))

    cautions = warnings + precautions

    # age_note
    age_notes_parts = []
    age_notes_parts.extend(ensure_list(label.get("pediatric_use")))
    age_notes_parts.extend(ensure_list(label.get("geriatric_use")))
    age_note = " ".join(age_notes_parts) if age_notes_parts else ""

    # important_warnings
    boxed = ensure_list(label.get("boxed_warning"))
    important_warnings = boxed if boxed else warnings

    return {
        "base_name": generic_name.upper(),
        "generic_name": generic_name.upper(),
        "aliases": [a.upper() for a in alias_clean],
        "category": category,
        "indications": indications,
        "contraindications": contraindications,
        "cautions": cautions,
        "age_note": age_note,
        "important_warnings": important_warnings,
    }


def convert(verbose: bool = False) -> None:
    setup_logging(verbose)

    if not RAW_DB_PATH.exists():
        raise SystemExit(f"Raw openFDA DB not found at {RAW_DB_PATH}")

    raw_text = RAW_DB_PATH.read_text(encoding="utf-8")
    raw_db = json.loads(raw_text)

    if not isinstance(raw_db, list):
        raise SystemExit("Raw DB must be a list of entries.")

    logger.info("Loaded %d raw entries from %s", len(raw_db), RAW_DB_PATH)

    structured: List[Dict[str, Any]] = []

    for idx, entry in enumerate(raw_db):
        if not isinstance(entry, dict):
            logger.warning("Skipping non-dict entry at index %d", idx)
            continue

        generic_query = str(entry.get("generic_query") or "").strip()
        label = entry.get("label_raw") or {}

        if not label:
            logger.warning("No label_raw for entry %d (generic_query=%s)", idx, generic_query)
            generic_name = (generic_query or "UNKNOWN").upper()
            structured.append(
                {
                    "base_name": generic_name,
                    "generic_name": generic_name,
                    "aliases": [generic_name],
                    "category": "",
                    "indications": [],
                    "contraindications": [],
                    "cautions": [],
                    "age_note": "",
                    "important_warnings": [],
                }
            )
            continue

        logger.info("Converting %d/%d: generic_query=%s", idx + 1, len(raw_db), generic_query)
        record = extract_from_label(label, generic_fallback=generic_query or "unknown")
        structured.append(record)

    STRUCTURED_DB_PATH.write_text(
        json.dumps(structured, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Wrote structured DB to %s", STRUCTURED_DB_PATH)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Convert raw openFDA DB to structured OTC DB schema."
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    convert(verbose=args.verbose)


if __name__ == "__main__":
    main()