# Terrain Mapper
Finds Earth terrain patches whose 3D shape matches Moon/Mars terrain patches, then ranks them by fidelity, accessibility, repeatability and affordability.
Full spec: @docs/SPEC.md (read the relevant section before starting each milestone)

## Stack
- Python 3.11: FastAPI, Pydantic v2, numpy, scipy, pandas, scikit-learn
- Frontend: Vite + React + TypeScript + three.js
- Deploy: Vercel (static frontend + Python function in /api)
- pipeline/ = offline data work. backend/ and api/ = runtime (numpy only).

## Commands (update as they are created)
- API: uvicorn api.index:app --reload
- Frontend: npm run dev
- Verify data sources: python pipeline/verify_sources.py
- Build corpus: python pipeline/build_corpus.py
- Fit model artifacts: python pipeline/fit_model.py
- CLI search: python -m backend.search --target jezero_delta --objective mobility --stage early

## Rules
- Work ONE milestone at a time (SPEC section 10). After each, stop and report the acceptance results.
- Plan first (plan mode) for any change touching more than 2 files.
- No hardcoded feature weights. Fidelity = geometric mean of percentile-calibrated components.
- Never present curated or mock data as measured. Keep a provenance/source column.
- Runtime dependencies are fastapi, pydantic, numpy only. rasterio, pandas, requests stay in pipeline/.
- The runtime API makes no external network calls. All data access happens in pipeline/.
- If a data source fails or returns odd values, STOP and report. Never silently substitute data.
- Mark assumptions UNVERIFIED until pipeline/verify_sources.py output confirms them.
- No automated tests in v1 unless asked. Verify by running scripts and printing results.
- Ask before adding a dependency or changing the API contract.
