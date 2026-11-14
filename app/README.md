# Analog Finder

Find Earth analogue sites for Moon and Mars targets. Pick a target, set metrics and weights (manually or via LLM), then compare ranked candidates on a map and in 3D.

> Mock data in v1 — values in `backend/llm/data.py` are placeholders, not real measurements.

## Layout

```
app/
  frontend/                 # Vite + React UI
  backend/
    api/
      index.py              # FastAPI app
      routes/               # HTTP handlers
      services/             # business logic
      db/                   # catalogue access (mock for now)
    llm/                    # models, mock data, rules, LLM suggest
  api/index.py              # Vercel entry (re-exports backend.api.index:app)
```

## Stack

- **Backend:** Python 3.11, FastAPI, LangChain (OpenAI / Anthropic)
- **Frontend:** Vite, React, TypeScript, Zustand, Leaflet, three.js
- **Host:** Vercel (static + Python serverless)

## Local development

```bash
# Backend (from app/)
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add OPENAI_API_KEY and/or ANTHROPIC_API_KEY
uvicorn backend.api.index:app --reload --port 8000
# or: uvicorn api.index:app --reload --port 8000

# Frontend (separate terminal)
npm install
npm run dev
```

Vite proxies `/api` to `http://127.0.0.1:8000`.

Or use `vercel dev` for a combined local setup.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/catalog` | metrics, targets, categories |
| GET | `/api/terrain/{site_id}` | mock heightfield |
| POST | `/api/search` | ranked matches |
| POST | `/api/suggest` | LLM metric suggestions |

## Iteration 1

Hard rules and real scoring live in `backend/llm/rules.py` (placeholder scorer keeps the UI working). See `AGENT.md` for the full build spec and `implementation.md` for gaps and the learning plan.
