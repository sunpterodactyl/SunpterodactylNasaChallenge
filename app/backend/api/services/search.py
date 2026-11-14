from backend.api.db import get_candidates, get_target
from backend.llm import rules
from backend.llm.models import Match, SearchRequest


def run_search(req: SearchRequest) -> list[Match] | None:
    target = get_target(req.target_id)
    if not target:
        return None
    matches = [
        rules.score(target, c, req)
        for c in get_candidates()
        if rules.passes(c, req)
    ]
    return sorted(matches, key=lambda m: m.score, reverse=True)
