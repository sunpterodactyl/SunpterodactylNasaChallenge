import math
from .models import Metric, Target, Candidate

METRICS = [
    Metric(id='slope_median', label='Median slope', unit='deg', description='Median slope over a 5 km window'),
    Metric(id='relief', label='Local relief', unit='m', description='Max minus min elevation in the window'),
    Metric(id='roughness', label='Roughness', unit='m', description='RMS height deviation at a 100 m baseline'),
    Metric(id='temp_range', label='Diurnal temperature range', unit='K', description='Day minus night surface temperature'),
    Metric(id='ice_likelihood', label='Ice likelihood', unit='0-1', description='Proxy for near-surface ice'),
]

TARGETS = [
    Target(id='shackleton_rim', body='moon', name='Shackleton Crater rim', lat=-89.9, lon=0.0,
           values={'slope_median': 14, 'relief': 900, 'roughness': 6.0, 'temp_range': 150, 'ice_likelihood': 0.7},
           evidence={'slope_median': 'direct', 'relief': 'direct', 'roughness': 'direct', 'temp_range': 'direct', 'ice_likelihood': 'indirect'}),
    Target(id='jezero_delta', body='mars', name='Jezero Crater delta', lat=18.4, lon=77.5,
           values={'slope_median': 6, 'relief': 400, 'roughness': 3.5, 'temp_range': 90, 'ice_likelihood': 0.2},
           evidence={'slope_median': 'direct', 'relief': 'direct', 'roughness': 'direct', 'temp_range': 'direct', 'ice_likelihood': 'indirect'}),
    Target(id='marius_pit', body='moon', name='Marius Hills pit', lat=14.1, lon=-303.3,
           values={'slope_median': 9, 'relief': 120, 'roughness': 4.2, 'temp_range': 250, 'ice_likelihood': 0.0},
           evidence={'slope_median': 'direct', 'relief': 'direct', 'roughness': 'direct', 'temp_range': 'direct', 'ice_likelihood': 'indirect'}),
]

CANDIDATES = [
    Candidate(id='devon', name='Haughton Crater, Devon Island', country='Canada', lat=75.4, lon=-89.7, category='terrain', cost_index=0.8,
              values={'slope_median': 11, 'relief': 450, 'roughness': 5.1, 'temp_range': 20, 'ice_likelihood': 0.6}),
    Candidate(id='atacama', name='Atacama Desert', country='Chile', lat=-24.5, lon=-69.2, category='terrain', cost_index=0.3,
              values={'slope_median': 5, 'relief': 300, 'roughness': 2.8, 'temp_range': 30, 'ice_likelihood': 0.0}),
    Candidate(id='askja', name='Askja caldera', country='Iceland', lat=65.0, lon=-16.8, category='terrain', cost_index=0.5,
              values={'slope_median': 13, 'relief': 600, 'roughness': 6.4, 'temp_range': 15, 'ice_likelihood': 0.3}),
    Candidate(id='dry_valleys', name='McMurdo Dry Valleys', country='Antarctica', lat=-77.5, lon=162.5, category='isru', cost_index=0.95,
              values={'slope_median': 8, 'relief': 700, 'roughness': 3.9, 'temp_range': 25, 'ice_likelihood': 0.8}),
    Candidate(id='lanzarote', name='Lanzarote lava tubes', country='Spain', lat=29.0, lon=-13.5, category='terrain', cost_index=0.2,
              values={'slope_median': 10, 'relief': 80, 'roughness': 4.0, 'temp_range': 14, 'ice_likelihood': 0.0}),
    Candidate(id='hi_seas', name='HI-SEAS habitat site, Mauna Loa', country='USA', lat=19.7, lon=-155.5, category='human_factors', cost_index=0.6,
              values={'slope_median': 7, 'relief': 150, 'roughness': 4.4, 'temp_range': 18, 'ice_likelihood': 0.0}),
    Candidate(id='svalbard', name='Svalbard (AMASE area)', country='Norway', lat=78.2, lon=15.6, category='isru', cost_index=0.7,
              values={'slope_median': 9, 'relief': 500, 'roughness': 4.8, 'temp_range': 12, 'ice_likelihood': 0.7}),
    Candidate(id='rio_tinto', name='Rio Tinto', country='Spain', lat=37.7, lon=-6.6, category='terrain', cost_index=0.2,
              values={'slope_median': 6, 'relief': 120, 'roughness': 2.5, 'temp_range': 16, 'ice_likelihood': 0.0}),
]

def terrain(seed: str, n: int = 48) -> list[list[float]]:
    # Procedural heightfield so the 3D view works before real DEMs exist.
    s = sum(ord(c) for c in seed)
    return [[round(40 * math.sin((x + s) / 7) * math.cos((y + s * 0.5) / 9) + 15 * math.sin((x * y + s) / 40), 2)
             for x in range(n)] for y in range(n)]
