from __future__ import annotations

import json
import sys
import re
from pathlib import Path

from glm_client import client, DEFAULT_MODEL

# TEMPLATE_PROMPT = """
# 你是一个帮助药师整理药品信息的助手。
# 我会给你一份药品说明书的完整文本，请你严格基于其中内容，提取并整理为一个 JSON 对象，字段包括：

# - generic_name: 通用名
# - aliases: 常见商品名或别名列表
# - category: 药物类别
# - indications: 适应证列表（每条为一句话）
# - contraindications: 禁忌列表
# - cautions: 慎用情况列表
# - age_note: 年龄相关说明（儿童、老人、孕期等）
# - important_warnings: 重要警示信息列表（例如用药时间限制、严重不良反应提示、就医时机等）

# 要求：
# 1. 严格从说明书中提取信息，不要自己编造。
# 2. 如某一类信息说明书中没有提到，用空列表 [] 或空字符串 ""。
# 3. 输出必须是合法 JSON。
# 4. 不要使用 ```json ``` 这样的代码块，不要输出任何额外解释或文字，只输出 JSON 本身。
# """

TEMPLATE_PROMPT = """
You are a helper that normalizes drug leaflets into structured JSON.

Fields:
- generic_name
- aliases
- category
- indications
- contraindications
- cautions
- age_note
- important_warnings

Constraints:
1. Only extract information present in the leaflet.
2. Use [] or "" for missing fields.
3. Output must be valid JSON without code fences or extra text.
"""

def extract_json_str(text: str) -> str:
    """
    Extract the first JSON-looking block { ... } from the model output.
    The model may include surrounding text or code fences; ignore those.

    Limitations:
    - Uses a simple regex to find the first {...} block, which may fail if the JSON is malformed or if there are multiple JSON objects.
    - Does not validate that the extracted block is valid JSON.
    - May not work correctly if braces are nested or if the output contains non-JSON curly braces.
    """
    if not text:
        raise ValueError("Model returned empty content")

    # Try matching the first JSON-looking block.
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        raise ValueError("No JSON object found in model output")
    return m.group(0)

def build_single_drug(input_path: Path, output_path: Path):
    # 1. Read raw leaflet text.
    text = input_path.read_text(encoding="utf-8")

    # 2. Query the LLM.
    resp = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": TEMPLATE_PROMPT},
            {"role": "user", "content": text},
        ],
        temperature=0
    )

    content = resp.choices[0].message.content

    # Debug: inspect model output.
    print("=== Raw model output (first 500 chars) ===")
    print(repr(content[:500]))
    print("================================")

    # 3. Extract JSON substring from model output.
    json_str = extract_json_str(content)

    # 4. Parse JSON.
    data = json.loads(json_str)

    # 5. Save parsed JSON to disk.
    output_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"Generated {output_path}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python build_db.py input.txt output.json")
        sys.exit(1)
    build_single_drug(Path(sys.argv[1]), Path(sys.argv[2]))