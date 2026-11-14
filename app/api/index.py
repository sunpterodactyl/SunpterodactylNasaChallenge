import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from typing import Literal
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from backend import data, rules, llm
from backend.models import SearchRequest, Match, Suggestion

app = FastAPI()

class SuggestReq(BaseModel):
    prompt: str
    provider: Literal['openai', 'anthropic'] = 'openai'

@app.get('/api/catalog')
def catalog():
    return {'metrics': data.METRICS, 'targets': data.TARGETS,
            'categories': ['terrain', 'isru', 'human_factors']}

@app.get('/api/terrain/{site_id}')
def terrain(site_id: str):
    return {'grid': data.terrain(site_id)}

@app.post('/api/search')
def search(req: SearchRequest) -> list[Match]:
    target = next((t for t in data.TARGETS if t.id == req.target_id), None)
    if not target:
        raise HTTPException(404, 'unknown target')
    matches = [rules.score(target, c, req) for c in data.CANDIDATES if rules.passes(c, req)]
    return sorted(matches, key=lambda m: m.score, reverse=True)

@app.post('/api/suggest')
def suggest(r: SuggestReq) -> Suggestion:
    try:
        return llm.suggest(r.prompt, r.provider)
    except Exception as e:
        raise HTTPException(502, str(e))
