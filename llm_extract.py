from typing import List, Dict
import json
import re
import os

from glm_client import client, DEFAULT_MODEL

# Load whitelist once to save overhead and ensure local compliance
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WHITELIST_PATH = os.path.join(BASE_DIR, "common_generics_en.txt")

def _load_whitelist() -> Set[str]:
    if not os.path.exists(WHITELIST_PATH):
        return set()
    with open(WHITELIST_PATH, "r", encoding="utf-8-sig") as f:
        return {line.strip().upper().replace('\ufeff', '') for line in f if line.strip()}

GENERIC_WHITELIST = _load_whitelist()

# Optimized prompt: Use examples instead of full list to save tokens
EXTRACT_SYSTEM_PROMPT = """
You are a medical drug-name extraction assistant.
Identify medication and supplement names. Normalize to English generic (INN) in ALL CAPS.

Rules:
1. Examples: "维C" -> "ASCORBIC ACID", "阿司匹林" -> "ASPIRIN", "泰诺" -> "ACETAMINOPHEN".
2. Normalized field: ALL UPPERCASE, generic name only, no dosage.
3. If unsure, set normalized to "".
4. Output ONLY a JSON object:
{"mentioned_drugs": [{"raw": "...", "normalized": "..."}]}
"""

def _extract_json_str(text: str) -> str:
    if not text:
        raise ValueError("Model returned empty content.")
    try:
        json.loads(text)
        return text
    except:
        pass
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        raise ValueError("No JSON object found.")
    return m.group(0)

def extract_drugs(question: str) -> List[Dict[str, str]]:
    user_prompt = f"Input: {question}\nOutput JSON:"

    resp = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": EXTRACT_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0
    )
    content = resp.choices[0].message.content

    try:
        json_str = _extract_json_str(content)
        data = json.loads(json_str)
        mentioned = data.get("mentioned_drugs", [])
        
        result: List[Dict[str, str]] = []
        for item in mentioned:
            raw = str(item.get("raw", "")).strip()
            norm = str(item.get("normalized", "")).upper().strip()
            
            if not raw: continue
            
            # Local Validation: Only allow drugs present in your local text file
            # This ensures LLM doesn't hallucinate facts not in your database
            if norm in GENERIC_WHITELIST:
                print(f"DEBUG: norm='{norm}', whitelist={GENERIC_WHITELIST}")
                result.append({"raw": raw, "normalized": norm})
            else:
                # Mark as unrecognized for Case 2 fallback in main.py
                result.append({"raw": raw, "normalized": ""})
        return result
    except:
        return []