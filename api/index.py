"""FastAPI app: two routes (SPEC section 8). Vercel serves this file as a Python function.

Local:  uvicorn api.index:app --reload
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException  # noqa: E402

from backend.model import get_model  # noqa: E402
from backend.scoring import Brief, catalog, search  # noqa: E402

app = FastAPI(title='Terrain Mapper')
get_model()   # load artifacts once at import


@app.get('/api/catalog')
def get_catalog():
    return catalog()


@app.post('/api/search')
def post_search(brief: Brief):
    try:
        return search(brief)
    except KeyError:
        raise HTTPException(404, f'unknown target_id: {brief.target_id}')
