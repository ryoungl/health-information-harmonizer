from typing import List, Dict
import json
import re

from glm_client import client, DEFAULT_MODEL

EXTRACT_SYSTEM_PROMPT = """
You are a medical drug-name extraction assistant.

Your task is to read a user’s message and identify all medication names mentioned,
including brand names, Chinese names, abbreviations, common misspellings,
and vague phrases (such as “painkiller”, “cold medicine”, “anti-allergy pill”).

Your output must normalize each medication to its English INN generic name,
which will be used to look up drug information in a local FDA-based database.

Normalization rules:

1. When the user mentions a brand name or Chinese name, normalize it to the English generic ingredient.
   Examples:
   - "Advil", "Nurofen", "芬必得", "布洛芬缓释胶囊" → "ibuprofen"
   - "Tylenol", "对乙酰氨基酚", "扑热息痛" → "acetaminophen"
   - "开瑞坦", "氯雷他定片" → "loratadine"
   - "耐信", "埃索美拉唑" → "esomeprazole"

2. When multiple ingredients exist in a brand product, choose the main pharmacologically active ingredient.
   If you are completely unsure, set normalized to an empty string "".

3. The normalized field must contain only the INN name, in lowercase.
   Do not include dosage, form, strength, or duration.
   Example: "ibuprofen", not "ibuprofen 200 mg tablets".

4. If a phrase refers to a class of drugs rather than a specific ingredient:
   - If one likely ingredient can be inferred (for example, “退烧药” → acetaminophen or ibuprofen),
     choose the single most likely INN.
   - If you cannot safely infer a specific INN, set normalized to "".

5. The output must be a single JSON object with the structure:
{
  "mentioned_drugs": [
    {
      "raw": "...",
      "normalized": "..."
    },
    ...
  ]
}

6. Do not output anything other than the JSON object.
Do not wrap it in code fences.
"""

def _extract_json_str(text: str) -> str:
    """
    Extract a JSON object from model output.

    Accepts extra surrounding text or code fences and attempts to locate the first {...} block.
    """
    if not text:
        raise ValueError("Model returned empty content.")

    # Prefer direct parsing first.
    try:
        json.loads(text)
        return text
    except Exception:
        pass

    # Use regex to find the first { ... } block, including newlines.
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        raise ValueError("No JSON object found in model output.")
    return m.group(0)


def extract_drugs(question: str) -> List[Dict[str, str]]:
    """
    Extract drug mentions and normalized names from a user question.

    Returns a list of {"raw": str, "normalized": str} items suitable for downstream lookup.
    """

    user_prompt = (
        f"用户输入：{question}\n\n"
        "请按之前说明，输出 JSON 对象，结构为：\n"
        '{"mentioned_drugs": [{"raw": "...", "normalized": "..."}]}'
    )

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
        # Defensive: ensure we only keep dict items with raw/normalized fields
        result: List[Dict[str, str]] = []
        for item in mentioned:
            if not isinstance(item, dict):
                continue
            raw = str(item.get("raw", "")).strip()
            norm = str(item.get("normalized", "")).strip()
            if not raw and not norm:
                continue
            result.append({"raw": raw, "normalized": norm})
        return result
    except Exception as e:
        # On any parsing error, return an empty list instead of failing the service.
        # Enable logging here during debugging if needed.
        # print("extract_drugs error:", e)
        return []