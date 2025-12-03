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

        return {
            "echo": q,
            "matched_drugs": [d["generic_name"] for d in known],
            "recognized_drugs": normalized,
            "analysis": {"summary": glm_answer},
            "answer": glm_answer,
            "disclaimer": disclaimer,
        }

    # Case 2: drugs recognized but none found in local database.
    if unknown:
        msg = (
            f"你提到的药物：{', '.join(set(unknown))} 未收录在本系统数据库中。在不了解成分的情况下不建议盲目合并用药。"
            if lang == "zh"
            else f"The drugs you mentioned ({', '.join(set(unknown))}) are not in the local database. "
                 f"Avoid combining medicines without professional advice."
        )
        return {
            "echo": q,
            "matched_drugs": [],
            "recognized_drugs": normalized,
            "analysis": {"summary": msg},
            "answer": msg,
            "disclaimer": disclaimer,
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
    }