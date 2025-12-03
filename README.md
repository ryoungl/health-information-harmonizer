[English Version](#english-version) | [中文说明](#中文说明)

---

# English Version

## Health Information Harmonizer (HIH)

Health Information Harmonizer (HIH) is a small health information assistant focused on:

- Filtering noisy or unreliable health claims
- Explaining symptoms, over-the-counter (OTC) medicines, and common online narratives
- Highlighting potential red-flag signals where professional care may be needed
- Harmonizing information instead of acting as an online doctor

HIH is **not**:

- A diagnostic system  
- A dosing calculator  
- A prescription generator  
- A replacement for medical professionals  

It is designed as an information filter, explainer, and risk signal highlighter.

Typical use cases:

- Clarifying confusing health articles or social media posts
- Understanding what an OTC drug is generally used for and what to be careful about
- Demonstrating how to connect an LLM with a local structured drug database
- Course projects or demos for medical AI and health informatics

---

## Features

- Structured markdown output with four sections:
  - “What you are concerned about”
  - “Information synthesis and explanation”
  - “Potential risk signals”
  - “Possible next steps”
- Local OTC drug database (JSON) with basic fields
- Automatic drug-name extraction using an LLM
- Chinese and English modes (controlled by a `lang` field)
- Pluggable LLM backend with OpenAI-style APIs:
  - OpenAI
  - Zhipu GLM (OpenAI-compatible endpoint)
  - DeepSeek and other OpenAI-compatible providers
- Simple front end:
  - `/static/index.html` renders messages as cards
  - Backend FastAPI endpoint `/ask` returns structured JSON

---

## Project Structure

```text
project-root/
├─ main.py                 # FastAPI backend, /ask endpoint
├─ glm_client.py           # Unified LLM client (OpenAI / Zhipu / DeepSeek)
├─ llm_extract.py          # Drug name extraction via LLM
├─ drug_db.py              # Local OTC DB loading and matching
├─ build_db.py             # Utility for building / normalizing drug DB
├─ data/
│   └─ otc_db.json         # Local OTC drug data
├─ static/
│   └─ index.html          # Front-end UI
├─ .env.example            # Environment variable template
├─ requirements.txt
├─ .gitignore
└─ README.md
```

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/ryoungl/health-information-harmonizer.git
cd health-information-harmonizer
```

### 2. Create and edit `.env`

```bash
cp .env.example .env
```

Open `.env` and fill in your own API key and provider configuration.

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

Make sure `requirements.txt` includes at least:

```text
fastapi
uvicorn[standard]
openai
python-dotenv
```

### 4. Run the backend

```bash
uvicorn main:app --reload
```

By default the app listens on:

```text
http://127.0.0.1:8000
```

### 5. Open the front end

In your browser:

```text
http://127.0.0.1:8000
```

The front end calls `/ask` with JSON payloads like:

```json
{
  "question": "Does ibuprofen harm the kidneys?",
  "lang": "en"
}
```

or

```json
{
  "question": "布洛芬会伤肾吗？",
  "lang": "zh"
}
```

---

## LLM Configuration

HIH uses a unified client in `glm_client.py`. The provider is selected by environment variables.

Supported providers (through OpenAI-style APIs):

- `openai`
- `zhipu`
- `deepseek`

### Environment variables

The main variables are:

| Variable       | Description                         | Example                            |
|----------------|-------------------------------------|------------------------------------|
| `LLM_PROVIDER` | Provider name                       | `openai`, `zhipu`, or `deepseek`   |
| `LLM_API_KEY`  | API key for the chosen provider     | `sk-...`                           |
| `LLM_API_BASE` | Base URL for the API (optional)     | `https://api.openai.com/v1`        |
| `LLM_MODEL`    | Model name (optional)              | `gpt-4.1-mini`, `glm-4-flash`     |

There are also provider-specific fallbacks such as `OPENAI_API_KEY`, `ZHIPU_API_KEY`, and `DEEPSEEK_API_KEY`, but users are encouraged to use the generic names.

### `.env.example` template

```env
# LLM provider: openai / zhipu / deepseek
LLM_PROVIDER=openai

# Your API key
LLM_API_KEY=YOUR_API_KEY_HERE

# Optional: override base URL and model

# For OpenAI:
# LLM_API_BASE=https://api.openai.com/v1
# LLM_MODEL=gpt-4.1-mini

# For Zhipu:
# LLM_API_BASE=https://open.bigmodel.cn/api/paas/v4
# LLM_MODEL=glm-4-flash

# For DeepSeek:
# LLM_API_BASE=https://api.deepseek.com
# LLM_MODEL=deepseek-chat
```

Actual base URLs and model names may change over time. Always refer to the official documentation of each provider.

---

## Local OTC Database

The local OTC database is stored in `data/otc_db.json`.

Typical fields per drug record:

- `base_name`: ingredient-level name, used for grouping preparations
- `generic_name`: specific dosage form name
- `aliases`: brand or alternative names
- `category`: drug category
- `indications`: general indications
- `contraindications`: known contraindications
- `cautions`: use with caution in these situations
- `important_warnings`: summary of important warnings

`drug_db.py` loads the JSON file and constructs several in-memory indexes for fast matching and grouping.

You can extend `otc_db.json` with your own data, as long as you keep the overall structure consistent.

---

## API Endpoint

### POST `/ask`

Request body:

```json
{
  "question": "string",
  "lang": "zh or en"
}
```

Response:

```json
{
  "answer": "Markdown text from the LLM",
  "analysis": {
    "summary": "Optional short summary if provided"
  },
  "matched_drugs": [
    "Ibuprofen"
  ],
  "recognized_drugs": [
    "Ibuprofen"
  ],
  "disclaimer": "Tool-level disclaimer text"
}
```

The front end splits the markdown into cards based on headings and displays drug tags plus disclaimers as a footer line.

---

## Safety Notice

This project is designed for educational and informational purposes only.

HIH does not:

- Diagnose medical conditions
- Provide dosing instructions
- Recommend specific treatments
- Replace professional clinical care

Users should always consult qualified healthcare professionals for clinical decisions.

---

## License

This project is released under the MIT License.

---

# 中文说明

[Back to English](#english-version)

## AI 健康信息调和器（HIH）

**AI 健康信息调和器（Health Information Harmonizer, HIH）** 是一个面向公众健康信息的解释与风险提示小工具。

它的定位是：

- 健康信息过滤器  
- 解释器  
- 风险信号提示器  

而不是：

- 在线问诊  
- 自动诊断系统  
- 药物剂量或处方工具  

典型使用场景：

- 看了一篇健康科普或小红书种草笔记，想确认内容是否可靠  
- 想了解某个常见药物大致是干什么用的，有哪些禁忌和注意事项  
- 在课程或实验中演示“LLM + 本地药物知识库”的组合方式  

---

## 功能特点

- 固定的四段式结构输出：
  - 你在关心什么
  - 信息调和与解释
  - 潜在风险信号
  - 可以考虑的下一步
- 使用本地 JSON 药物数据库（OTC 常用药）
- 通过 LLM 抽取药品名称，并与本地数据库匹配
- 支持中文和英文两种模式（通过 `lang` 字段控制）
- LLM 后端可插拔，支持多家 OpenAI-Style API
- 前后端简单解耦：
  - `static/index.html` 提供页面  
  - FastAPI 提供 `/ask` 接口  

---

## 项目结构

```text
project-root/
├─ main.py                 # FastAPI 后端，提供 /ask
├─ glm_client.py           # 统一 LLM 客户端（OpenAI / 智谱 / DeepSeek）
├─ llm_extract.py          # 使用 LLM 抽取药品名称
├─ drug_db.py              # 本地药物数据库加载与匹配
├─ build_db.py             # 可选：构建或规范化药物数据库
├─ data/
│   └── otc_db.json        # 本地常用药数据
├─ static/
│   └── index.html         # 前端界面
├─ .env.example            # 环境变量示例文件
├─ requirements.txt
├─ .gitignore
└─ README.md
```

---

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/ryoungl/health-information-harmonizer.git
cd health-information-harmonizer
```

### 2. 创建并编辑 `.env`

```bash
cp .env.example .env
```

然后在 `.env` 中填写你自己的 API Key 以及 LLM 提供商配置。

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

建议 `requirements.txt` 至少包含：

```text
fastapi
uvicorn[standard]
openai
python-dotenv
```

### 4. 启动后端服务

```bash
uvicorn main:app --reload
```

默认监听地址为：

```text
http://127.0.0.1:8000
```

### 5. 打开前端页面

在浏览器中访问：

```text
http://127.0.0.1:8000
```

前端会向 `/ask` 发送 JSON 请求，例如：

```json
{
  "question": "布洛芬会伤肾吗？",
  "lang": "zh"
}
```

或

```json
{
  "question": "Does ibuprofen harm the kidneys?",
  "lang": "en"
}
```

---

## LLM 配置方式

项目使用 `glm_client.py` 统一封装了对不同 LLM 的调用。  
实际使用哪个服务由环境变量决定。

当前支持通过 OpenAI 风格接口访问的几类：

- OpenAI 官方  
- 智谱 GLM（OpenAI 兼容通道）  
- DeepSeek 等其他兼容服务  

### 关键环境变量

| 变量名         | 作用                         | 示例                            |
|----------------|------------------------------|---------------------------------|
| `LLM_PROVIDER` | 提供商名称                   | `openai` / `zhipu` / `deepseek` |
| `LLM_API_KEY`  | 对应提供商的 API Key         | `sk-...`                        |
| `LLM_API_BASE` | 接口地址（可选）             | `https://api.openai.com/v1`     |
| `LLM_MODEL`    | 模型名称（可选）             | `gpt-4.1-mini` / `glm-4-flash` |

项目中也兼容部分旧变量名（如 `OPENAI_API_KEY`、`ZHIPU_API_KEY` 等），但更推荐统一使用 `LLM_*` 形式。

### `.env.example` 示例

```env
# LLM provider: openai / zhipu / deepseek
LLM_PROVIDER=openai

# Your API key
LLM_API_KEY=YOUR_API_KEY_HERE

# Optional: override base URL and model

# For OpenAI:
# LLM_API_BASE=https://api.openai.com/v1
# LLM_MODEL=gpt-4.1-mini

# For Zhipu:
# LLM_API_BASE=https://open.bigmodel.cn/api/paas/v4
# LLM_MODEL=glm-4-flash

# For DeepSeek:
# LLM_API_BASE=https://api.deepseek.com
# LLM_MODEL=deepseek-chat
```

不同厂商的 base_url 和模型名可能随时间变化，请以官方文档为准。

---

## 本地药物数据库说明

本地药物数据库位于 `data/otc_db.json`，使用 JSON 数组格式。

每条记录通常包含：

- `base_name`：基础药物名（成分级别）
- `generic_name`：具体制剂名称
- `aliases`：常见别名或商品名
- `category`：药物类别
- `indications`：适应证
- `contraindications`：禁忌
- `cautions`：慎用情况
- `important_warnings`：重要警示

`drug_db.py` 会在启动时加载该文件，并构建索引，用于快速匹配和按 `base_name` 归纳剂型。

如果你想扩展更多药物，只需要在 `otc_db.json` 中按相同结构追加即可。

---

## 接口说明

### POST `/ask`

请求体：

```json
{
  "question": "用户的问题",
  "lang": "zh 或 en"
}
```

返回示例：

```json
{
  "answer": "LLM 返回的 Markdown 文本",
  "analysis": {
    "summary": "可选的简要总结"
  },
  "matched_drugs": ["Ibuprofen"],
  "recognized_drugs": ["Ibuprofen"],
  "disclaimer": "工具级免责声明文本"
}
```

前端会将 `answer` 中的 Markdown 按标题拆成若干卡片，并在卡片下方展示药物标签和免责声明。

---

## 风险提示

本项目仅用于教学与一般性健康信息参考，不具有任何医疗效力。

HIH 不提供：

- 疾病诊断  
- 具体剂量建议  
- 药物处方  
- 个体化治疗决策  

如有症状或用药疑问，请及时咨询专业医生或药师。

---

## License

本项目使用 MIT License 开源。

可自由用于学习、研究和二次开发，但在使用过程中请自行遵守所在地区的法律与医学监管要求。
