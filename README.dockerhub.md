# **Health Information Harmonizer (HIH)**

A lightweight API service for harmonizing online health information, identifying OTC drug mentions, highlighting potential risks, and providing LLM-based explanations.

> This image **requires a valid LLM API key**.  
>
> Without LLM configuration, the container will not start successfully.

---

## 🔧 How to run

1. Create a `.env` file next to where you run Docker (or copy from `.env.example` if you cloned the GitHub repo).

2. Put one of the following configurations into `.env` (see “LLM Switching” below).

3. Start the container:

```bash
docker run -p 8000:8000 --env-file .env ryoungl/health-information-harmonizer:latest
````

Open:

```text
http://localhost:8000/docs
```

---

## 🔧 Environment Variables (LLM Switching)

HIH supports multiple LLM providers through environment variables:

### Common variables

| Variable       | Description                         |
| -------------- | ----------------------------------- |
| `LLM_PROVIDER` | `openai` or `zhipu` or `deepseek` or `gemini`   |
| `LLM_API_KEY`  | API key for the selected provider   |
| `LLM_API_BASE` | Optional, override default base URL |
| `LLM_MODEL`    | Optional, override default model    |

---

### 1) Use OpenAI

Put this in `.env`:

```env
LLM_PROVIDER=openai
LLM_API_KEY=sk-xxxx
LLM_API_BASE=https://api.openai.com/v1
LLM_MODEL=gpt-4.1-mini
```

---

### 2) Use Zhipu GLM

```env
LLM_PROVIDER=zhipu
LLM_API_KEY=your_zhipu_key
LLM_API_BASE=https://open.bigmodel.cn/api/paas/v4
LLM_MODEL=glm-4-flash
```

---

### 3) Use DeepSeek

```env
LLM_PROVIDER=deepseek
LLM_API_KEY=your_deepseek_key
LLM_API_BASE=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

---

### 4) Use Gemini (OpenAI-compatible endpoint)

```env
LLM_PROVIDER=gemini
LLM_API_KEY=your_gemini_key
LLM_API_BASE=https://generativelanguage.googleapis.com/v1beta/openai/
LLM_MODEL=gemini-flash-latest
```

---

## 📡 Main API Endpoint

### POST `/ask`

Example request:

```json
{
  "question": "Does ibuprofen harm the kidneys?",
  "lang": "en"
}
```

The service returns:

* Summary
* Detected risk signals
* OTC drug information (if any)
* Optional LLM explanation
* Structured JSON output

---

## 📁 Project Source Code

Source code and full documentation:

```text
https://github.com/ryoungl/health-information-harmonizer
```

---

## ⚠ Disclaimer

HIH is **not** a diagnostic tool or medical advice system.
It provides educational health-information harmonization only.
Always consult qualified healthcare professionals for clinical decisions.

---

## 🧩 Image Details

Docker Image: ryoungl/health-information-harmonizer:0.1.0
Base Image: python:3.11-slim
Architecture: linux/amd64
