from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import listings, stats, price_history, config, scraper

app = FastAPI(title="Idealista Scraper API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(listings.router)
app.include_router(stats.router)
app.include_router(price_history.router)
app.include_router(config.router)
app.include_router(scraper.router)


@app.get("/")
def root():
    return {"status": "ok"}
