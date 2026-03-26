import re
from typing import Optional
from pydantic import BaseModel, computed_field


class Listing(BaseModel):
    url: str
    neighbourhood: Optional[str] = None
    title: Optional[str] = None
    price: Optional[str] = None
    details: Optional[str] = None
    published: Optional[str] = None
    description: Optional[str] = None
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    bathrooms: Optional[int] = None
    usable_sqm: Optional[int] = None
    has_terrace: Optional[bool] = None
    has_elevator: Optional[bool] = None
    condition: Optional[str] = None
    heating: Optional[str] = None
    energy_rating: Optional[str] = None
    community_fees: Optional[str] = None
    price_per_sqm: Optional[str] = None

    @computed_field
    @property
    def price_num(self) -> Optional[int]:
        if not self.price:
            return None
        d = re.sub(r"[^\d]", "", self.price)
        return int(d) if d else None

    @computed_field
    @property
    def ppm_num(self) -> Optional[int]:
        if not self.price_per_sqm:
            return None
        d = re.sub(r"[^\d]", "", self.price_per_sqm.split("€")[0])
        return int(d) if d else None

    @computed_field
    @property
    def full_url(self) -> str:
        return f"https://www.idealista.com{self.url}"

    model_config = {"from_attributes": True}


class ListingsResponse(BaseModel):
    total: int
    listings: list[Listing]
