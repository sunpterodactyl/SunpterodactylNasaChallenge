from backend.api.db import get_metrics, get_targets

CATEGORIES = ['terrain', 'isru', 'human_factors']


def build_catalog() -> dict:
    return {
        'metrics': get_metrics(),
        'targets': get_targets(),
        'categories': CATEGORIES,
    }
