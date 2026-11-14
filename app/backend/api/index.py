from fastapi import FastAPI

from backend.api.routes import build_api_router

app = FastAPI(title='Analog Finder')
app.include_router(build_api_router())
