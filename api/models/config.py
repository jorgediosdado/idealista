from pydantic import BaseModel, Field


class ConfigModel(BaseModel):
    neighbourhoods: list[str]
    max_price: int = Field(gt=0)
    min_sqm: int = Field(gt=0)
    min_rooms: int = Field(ge=1)
