from __future__ import annotations

import os
from typing import Any, Dict, List

from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env if present
load_dotenv()

# LLM provider configuration
# Default to OpenAI for maximum compatibility
PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()

if PROVIDER == "zhipu":
    api_key = (
        os.getenv("LLM_API_KEY")
        or os.getenv("ZHIPU_API_KEY")
    )
    base_url = (
        os.getenv("LLM_API_BASE")
        or os.getenv("ZHIPU_BASE_URL")
        or "https://open.bigmodel.cn/api/paas/v4"
    )
    default_model = (
        os.getenv("LLM_MODEL")
        or os.getenv("ZHIPU_MODEL")
        or "glm-4-flash"
    )

elif PROVIDER == "openai":
    api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    base_url = (
        os.getenv("LLM_API_BASE")
        or os.getenv("OPENAI_BASE_URL")
        or "https://api.openai.com/v1"
    )
    default_model = (
        os.getenv("LLM_MODEL")
        or os.getenv("OPENAI_MODEL")
        or "gpt-4.1-mini"
    )

elif PROVIDER == "deepseek":
    api_key = os.getenv("LLM_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
    base_url = (
        os.getenv("LLM_API_BASE")
        or os.getenv("DEEPSEEK_BASE_URL")
        or "https://api.deepseek.com"
    )
    default_model = (
        os.getenv("LLM_MODEL")
        or os.getenv("DEEPSEEK_MODEL")
        or "deepseek-chat"
    )

else:
    raise RuntimeError(f"Unsupported LLM_PROVIDER: {PROVIDER}")

if not api_key:
    raise RuntimeError("Missing API key for configured LLM provider")

client = OpenAI(api_key=api_key, base_url=base_url)
DEFAULT_MODEL = default_model


# System prompts for Chinese and English outputs
SYSTEM_PROMPT_ZH = """
你是“AI 健康信息调和器”（Health Information Harmonizer）。

你的任务是：
1. 对用户提到的健康信息、症状描述、药物名称、网络说法进行过滤、解释和调和。
2. 识别信息噪声、夸大、不确定性并给出安全对应方式。
3. 在可能情况下结合本地药物资料解释，但不得编造说明书中不存在的内容。
4. 不诊断疾病、不给具体剂量、不提供个体化治疗方案。

输出结构（Markdown）：
### 你在关心什么
- …

### 信息调和与解释
- …

### 潜在风险信号
- …

### 可以考虑的下一步
- …

禁止使用“你可以吃”“必须吃”“一定不能吃”等用药性结论。
不输出标题为【声明】的段落，外层系统会添加声明。
"""

SYSTEM_PROMPT_EN = """
You are the “Health Information Harmonizer”.

Your tasks:
1. Filter, interpret, and harmonize the health-related information provided by the user.
2. Identify misinformation, exaggeration, uncertainty, or red-flag signals.
3. When the user mentions medicines, integrate ONLY the provided drug-info. Never invent details.
4. Do NOT diagnose disease, give dosages, or provide individualized treatment plans.

Required Markdown structure:
### What you are concerned about
- …

### Information synthesis and explanation
- …

### Potential risk signals
- …

### Possible next steps
- …

Avoid phrases like “you can take”, “must take”, “definitely cannot take”.
Do NOT output a section titled “Disclaimer”; the system will add it externally.
"""


def _build_drug_context(drug_infos: List[Dict[str, Any]], lang: str) -> str:
    """Render drug information into a language-aware text block for LLM context."""
    if not drug_infos:
        return (
            "No drug information in local database."
            if lang == "en"
            else "未找到相关药物的本地数据库信息。"
        )

    blocks = []
    for idx, d in enumerate(drug_infos, start=1):
        name = d.get("generic_name", "")
        aliases = ", ".join(d.get("aliases", []))
        category = d.get("category", "")
        indications = ", ".join(d.get("indications", []))
        contraind = ", ".join(d.get("contraindications", []))
        cautions = ", ".join(d.get("cautions", []))
        warnings = ", ".join(d.get("important_warnings", []))

        if lang == "zh":
            block = f"""
{idx}. 通用名: {name}
   别名: {aliases}
   类别: {category}
   适应证: {indications}
   禁忌: {contraind}
   慎用: {cautions}
   警示: {warnings}
"""
        else:
            block = f"""
{idx}. Generic name: {name}
   Aliases: {aliases}
   Category: {category}
   Indications: {indications}
   Contraindications: {contraind}
   Cautions: {cautions}
   Warnings: {warnings}
"""

        blocks.append(block.strip())

    return "\n\n".join(blocks)


def ask_glm(question: str, drug_infos: List[Dict[str, Any]], lang: str = "zh") -> str:
    """Call the LLM with harmonizer prompts and optional drug context."""
    system_prompt = SYSTEM_PROMPT_EN if lang == "en" else SYSTEM_PROMPT_ZH
    drug_context = _build_drug_context(drug_infos, lang)

    if lang == "zh":
        prefix = "下面是系统收录的相关药物资料（如有），请基于这些信息回答：\n\n"
    else:
        prefix = "Here is the drug information available in the local database:\n\n"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": prefix + drug_context},
        {"role": "user", "content": question},
    ]

    resp = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=messages,
        temperature=0.2,
    )

    return resp.choices[0].message.content