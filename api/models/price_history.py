from pydantic import BaseModel, computed_field


class PriceHistoryEntry(BaseModel):
    url: str
    price: str
    recorded_at: str

    @computed_field
    @property
    def full_url(self) -> str:
        return f"https://www.idealista.com{self.url}"
