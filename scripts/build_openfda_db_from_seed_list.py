#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Build data/otc_db.json directly from a list of common generic names,
using only openFDA English data.

Input:
  data/common_generics_en.txt   # one generic name per line

Output:
  data/otc_db.json

Each record in otc_db.json looks like:

  {
    "generic_query": "ibuprofen",
    "label_raw": {...} or null,
    "ndc_raw": {...} or null
  }

No Chinese data is involved. This DB is purely based on openFDA.

openFDA terms (CC0):
https://open.fda.gov/terms/
"""

import json
import os
import time
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SEED_PATH = DATA_DIR / "common_generics_en.txt"
OTC_DB_PATH = DATA_DIR / "otc_db.json"

OPENFDA_LABEL_URL = "https://api.fda.gov/drug/label.json"
OPENFDA_NDC_URL = "https://api.fda.gov/drug/ndc.json"

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )


def safe_get(url: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Wrapper around requests.get with basic error handling."""
    try:
        res = requests.get(url, params=params, timeout=15)
        if res.status_code != 200:
            logger.warning("openFDA request failed: %s (status=%s)", res.url, res.status_code)
            return None
        return res.json()
    except Exception as e:
        logger.warning("HTTP error while fetching %s: %s", url, e)
        return None


def query_openfda_label(generic: str, api_key: Optional[str]) -> Optional[Dict[str, Any]]:
    params: Dict[str, Any] = {
        "search": f'openfda.generic_name:"{generic}" OR openfda.brand_name:"{generic}"',
        "limit": 1,
    }
    if api_key:
        params["api_key"] = api_key

    logger.info("Label lookup: %s", generic)
    data = safe_get(OPENFDA_LABEL_URL, params)
    if data and data.get("results"):
        return data["results"][0]
    return None


def query_openfda_ndc(generic: str, api_key: Optional[str]) -> Optional[Dict[str, Any]]:
    params: Dict[str, Any] = {
        "search": f'generic_name:"{generic}" OR brand_name:"{generic}"',
        "limit": 1,
    }
    if api_key:
        params["api_key"] = api_key

    logger.info("NDC lookup: %s", generic)
    data = safe_get(OPENFDA_NDC_URL, params)
    if data and data.get("results"):
        return data["results"][0]
    return None


def read_seed_list() -> List[str]:
    if not SEED_PATH.exists():
        raise SystemExit(f"Seed list not found at {SEED_PATH}")
    lines = SEED_PATH.read_text(encoding="utf-8").splitlines()
    names = [ln.strip() for ln in lines if ln.strip() and not ln.strip().startswith("#")]
    # de-duplicate while preserving order
    seen = set()
    result = []
    for name in names:
        if name.lower() not in seen:
            seen.add(name.lower())
            result.append(name)
    return result


def build_db(verbose: bool = False, api_key: Optional[str] = None) -> None:
    setup_logging(verbose)

    generics = read_seed_list()
    logger.info("Loaded %d generic names from %s", len(generics), SEED_PATH)

    records: List[Dict[str, Any]] = []

    for idx, generic in enumerate(generics):
        logger.info("Processing %d/%d: %s", idx + 1, len(generics), generic)

        label = query_openfda_label(generic, api_key=api_key)
        time.sleep(0.5)  # be gentle without an API key
        ndc = query_openfda_ndc(generic, api_key=api_key)
        time.sleep(0.5)

        records.append({
            "generic_query": generic,
            "label_raw": label,
            "ndc_raw": ndc,
        })

    OTC_DB_PATH.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Wrote openFDA-based DB to %s", OTC_DB_PATH)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Build openFDA-only OTC DB from a list of generic names."
    )
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument(
        "--api-key",
        default=os.getenv("OPENFDA_API_KEY"),
        help="openFDA API key (optional, but recommended).",
    )
    args = parser.parse_args()

    build_db(verbose=args.verbose, api_key=args.api_key)


if __name__ == "__main__":
    main()