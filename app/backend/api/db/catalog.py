"""Catalogue access. Mock rows live in backend.llm.data until a real store exists."""

from backend.llm import data
from backend.llm.models import Candidate, Metric, Target


def get_metrics() -> list[Metric]:
    return list(data.METRICS)


def get_targets() -> list[Target]:
    return list(data.TARGETS)


def get_target(target_id: str) -> Target | None:
    return next((t for t in data.TARGETS if t.id == target_id), None)


def get_candidates() -> list[Candidate]:
    return list(data.CANDIDATES)


def get_terrain_grid(site_id: str) -> list[list[float]]:
    return data.terrain(site_id)
