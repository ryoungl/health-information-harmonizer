from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles  # 新增
from pydantic import BaseModel
from typing import Literal, Optional

from glm_client import ask_glm
from drug_db import find_by_generic_name
from llm_extract import extract_drugs

app = FastAPI(
    title="Health Information Harmonizer",
    description="AI 健康信息调和器：对用户提供的健康相关文本做信息过滤、解释、调和和风险提示。",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


class Query(BaseModel):
    question: str
    lang: Optional[Literal["zh", "en"]] = "zh"


@app.get("/", response_class=FileResponse)
def index():
    return FileResponse("static/index.html")


@app.post("/ask")
def ask(query: Query):
    q = query.question.strip()
    lang = query.lang or "zh"

    disclaimer = (
        "本回答仅整合公开健康信息作一般性参考，不替代医疗诊断或治疗。"
        if lang == "zh"
        else "This answer harmonizes public health information for general reference only and does not replace professional diagnosis or treatment."
    )

    # Handle empty question input.
    if not q:
        msg = (
            "请描述你看到的健康信息或你关心的问题。"
            if lang == "zh"
            else "Please describe the health information or concern you have."
        )

        return {
            "echo": q,
            "matched_drugs": [],
            "recognized_drugs": [],
            "analysis": {"summary": msg},
            "answer": msg,
            "disclaimer": disclaimer,
            "sources": []
        }

    # Extract drug names via LLM.
    extracted = extract_drugs(q)
    normalized = [i.get("normalized") for i in extracted if i.get("normalized")]

    known = []
    unknown = []

    for item in extracted:
        norm = item.get("normalized")
        if norm:
            info = find_by_generic_name(norm)
            if info:
                known.append(info)
            else:
                unknown.append(item.get("raw") or norm)
        else:
            unknown.append(item.get("raw") or "")

    # Case 1: recognized drug exists in local database.
    if known:
        glm_answer = ask_glm(q, known, lang=lang)

        if unknown:
            if lang == "zh":
                glm_answer += (
                    f"\n\n【额外提示】你还提到了未收录药物：{', '.join(set(unknown))}，建议咨询医生或药师。"
                )
            else:
                glm_answer += (
                    f"\n\n[Extra note] You also mentioned unlisted drugs: {', '.join(set(unknown))}. "
                    f"Please consult a doctor or pharmacist."
                )

        # Sources — no URLs, no DB dependencies
        if lang == "zh":
            sources = [
                {
                    "name": "本地药物数据库",
                    "note": f"匹配到药物：{', '.join(d['generic_name'] for d in known)}",
                    "url": None
                },
                {
                    "name": "AI 信息调和与解释",
                    "note": "回答内容基于本地结构化药物信息及语言模型推理生成。",
                    "url": None
                }
            ]
        else:
            sources = [
                {
                    "name": "Local Drug Database",
                    "note": f"Matched drugs: {', '.join(d['generic_name'] for d in known)}",
                    "url": None
                },
                {
                    "name": "AI Harmonization",
                    "note": "Answer generated using structured drug information and model reasoning.",
                    "url": None
                }
            ]

        return {
            "echo": q,
            "matched_drugs": [d["generic_name"] for d in known],
            "recognized_drugs": normalized,
            "analysis": {"summary": glm_answer},
            "answer": glm_answer,
            "disclaimer": disclaimer,
            "sources": sources
        }

    # Case 2: drugs recognized but none found in local database → fallback to LLM.
    if unknown and not known:
        # 让 LLM 正常解释这些药物，drug_info 列表传空
        glm_answer = ask_glm(q, [], lang=lang)

        # 追加一个轻度提示：本地库没结构化匹配，但已用通用医学知识解释
        if lang == "zh":
            glm_answer += (
                f"\n\n【系统说明】检测到以下药物名称：{', '.join(set(unknown))}。"
                f"这些名称未在本地结构化数据库中匹配到标准药物条目，我会基于通用医学资料和语境进行解释，仅作一般信息参考。"
            )
        else:
            glm_answer += (
                f"\n\n[System note] I detected the following drug names: {', '.join(set(unknown))}. "
                f"They are not mapped to a structured local entry, so I responded based on general medical knowledge and context. "
                f"This is for general information only."
            )

        return {
            "echo": q,
            "matched_drugs": [],
            "recognized_drugs": normalized,
            "analysis": {"summary": glm_answer},
            "answer": glm_answer,
            "disclaimer": disclaimer,
            "sources": [
                {
                    "name": "AI 信息调和与解释" if lang == "zh" else "AI Harmonization",
                    "note": (
                        "回答内容基于通用医学资料和模型对别名/俗称的理解生成。"
                        if lang == "zh"
                        else "Answer generated from general medical knowledge and model understanding of aliases/nicknames."
                    ),
                    "url": None
                }
            ]
        }

    # Case 3: no drug names recognized → general health-information harmonization.
    msg = (
        "未识别到药物名称。我可以帮助你调和网络上不同来源的健康信息，你可以继续补充细节。"
        if lang == "zh"
        else "No drug names recognized. I can help harmonize different sources of health information. "
             "Please provide more details."
    )
    return {
        "echo": q,
        "matched_drugs": [],
        "recognized_drugs": [],
        "analysis": {"summary": msg},
        "answer": msg,
        "disclaimer": disclaimer,
        "sources": []
    }