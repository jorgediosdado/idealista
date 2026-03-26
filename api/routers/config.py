from fastapi import APIRouter
from api.models.config import ConfigModel
from api.services import config_service

router = APIRouter(prefix="/config", tags=["config"])


@router.get("", response_model=ConfigModel)
def get_config():
    return config_service.get_config()


@router.put("", response_model=ConfigModel)
def update_config(config: ConfigModel):
    return config_service.update_config(config)
