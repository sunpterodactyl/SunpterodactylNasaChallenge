from fastapi import APIRouter, HTTPException

from backend.api.services import build_catalog, build_terrain, run_search, run_suggest
from backend.llm.models import Match, SearchRequest, Suggestion
from pydantic import BaseModel

router = APIRouter()


@router.get('/catalog')
def catalog():
    return build_catalog()


@router.post('/search')
def search(req: SearchRequest) -> list[Match]:
    matches = run_search(req)
    if matches is None:
        raise HTTPException(404, 'unknown target')
    return matches




class SuggestReq(BaseModel):
    prompt: str
    provider: Literal['openai', 'anthropic'] = 'openai'


@router.post('/suggest')
def suggest(r: SuggestReq) -> Suggestion:
    try:
        return run_suggest(r.prompt, r.provider)
    except Exception as e:
        raise HTTPException(502, str(e))



@router.get('/terrain/{site_id}')
def terrain(site_id: str):
    return build_terrain(site_id)
