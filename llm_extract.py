from typing import List, Dict
import json
import re

from glm_client import client, DEFAULT_MODEL

EXTRACT_SYSTEM_PROMPT = """
你是一个药物名称识别助手。
用户输入的是自然语言（可能包含中文、英文、商品名、别名、拼写错误等），
你需要从中找出提到的药品名称，并尽量归一化，供后续在本地药物库中检索。

任务要求：

1. 识别所有可能的药品商品名和通用名（包括中文和英文）。
   - 例如：芬必得、Advil、Nurofen、布洛芬片、Ibuprofen tablets 等。

2. 尽量将商品名归一化为通用名：
   - 例如：芬必得、Advil、Nurofen → 布洛芬
   - 扑热息痛、Tylenol → 对乙酰氨基酚
   - 氯雷他定片 → 氯雷他定
   如果用户提到了明确的剂型（片、胶囊、缓释片、口服液、悬液等），
   请在 normalized 中保留完整的通用名+剂型，例如：
   - “布洛芬缓释片”
   - “氯雷他定片”
   这样后续可以区分同一成分的不同剂型。

3. 如果你只能确定成分级别（base_name），而不确定具体剂型，
   那么 normalized 中只写成分通用名，例如：
   - “布洛芬”
   - “对乙酰氨基酚”
   - “氯雷他定”

4. 如果完全不确定通用名（例如一个模糊的商品名），
   可以把 normalized 字段留空字符串 ""，只保留 raw 原始写法。
   严禁自己发明世界上不存在的药名。

5. 输出格式必须是一个 JSON，对象结构为：
   {
     "mentioned_drugs": [
       {
         "raw": "用户原文中的药名或片段",
         "normalized": "尽量归一化后的通用名（可包括剂型），不确定时为空字符串"
       },
       ...
     ]
   }

6. 只输出 JSON 本身，不要输出任何额外说明文字，不要使用 ```json ``` 代码块。
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