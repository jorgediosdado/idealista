import json
import os
from api.models.config import ConfigModel

CONFIG_FILE = "config.json"
_TMP_FILE = "config.tmp.json"


def get_config() -> ConfigModel:
    with open(CONFIG_FILE, encoding="utf-8") as f:
        return ConfigModel(**json.load(f))


def update_config(new_config: ConfigModel) -> ConfigModel:
    with open(_TMP_FILE, "w", encoding="utf-8") as f:
        json.dump(new_config.model_dump(), f, indent=2, ensure_ascii=False)
    os.replace(_TMP_FILE, CONFIG_FILE)
    return new_config
