from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
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

    if not q:
        msg = "请描述你看到的健康信息。" if lang == "zh" else "Please describe the health information."
        return {
            "echo": q, "matched_drugs": [], "recognized_drugs": [],
            "analysis": {"summary": msg}, "answer": msg,
            "disclaimer": disclaimer, "sources": []
        }

    # 1. Extraction and Normalization
    extracted = extract_drugs(q)
    # Collect all normalized names for frontend display
    normalized_names = [item.get("normalized") for item in extracted if item.get("normalized")]
    
    known = []
    unknown = []

    for item in extracted:
        # norm_name is essential for database lookup
        norm_name = item.get("normalized", "").strip().upper()
        drug_info = find_by_generic_name(norm_name)
        
        if drug_info:
            known.append(drug_info)
        else:
            # Fallback to raw text if normalization failed
            unknown.append(item.get("raw") or norm_name)

    # 2. Case 1: Match found in local DB
    if known:
        glm_answer = ask_glm(q, known, lang=lang)
        if unknown:
            note = f"\n\n【额外提示】未收录：{', '.join(set(unknown))}" if lang == "zh" else f"\n\n[Note] Unlisted: {', '.join(set(unknown))}"
            glm_answer += note

        return {
            "echo": q,
            "matched_drugs": [d["generic_name"] for d in known],
            "recognized_drugs": normalized_names,
            "analysis": {"summary": glm_answer},
            "answer": glm_answer,
            "disclaimer": disclaimer,
            "sources": [
                {"name": "本地数据库" if lang=="zh" else "Local DB", "note": "匹配受控来源", "url": None},
                {"name": "AI 调和解释" if lang=="zh" else "AI Harmonization", "note": "基于结构化数据生成", "url": None}
            ]
        }

    # 3. Case 2: Recognized but not in DB (Safety Guardrail)
    if unknown:
        recognized_list = ', '.join(set(unknown))
        if lang == "zh":
            glm_answer = (
                f"系统识别到您询问的药物名称：{recognized_list}。\n\n"
                "**安全提示**：该药物暂未收录于合规数据库中。AI 不会生成用药建议。\n\n"
                "建议咨询医生或药剂师获取专业意见。"
            )
            source_note = "语义识别完成，但未匹配到受控数据源。"
        else:
            glm_answer = (
                f"System identified: {recognized_list}.\n\n"
                "**Safety Notice**: This drug is not in our verified database. AI will NOT generate medical advice."
            )
            source_note = "Semantic recognition complete, no controlled source matched."

        return {
            "echo": q,
            "matched_drugs": [],
            "recognized_drugs": normalized_names,
            "analysis": {"summary": glm_answer},
            "answer": glm_answer,
            "disclaimer": disclaimer,
            "sources": [{"name": "System Safety Guardrail", "note": source_note, "url": None}]
        }

    # 4. Case 3: No drug-like entities found
    msg = "未识别到药物名称。" if lang == "zh" else "No drug names recognized."
    return {
        "echo": q, "matched_drugs": [], "recognized_drugs": [],
        "analysis": {"summary": msg}, "answer": msg,
        "disclaimer": disclaimer, "sources": []
    }