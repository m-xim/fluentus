from functools import lru_cache
from tomllib import load
from typing import Type, TypeVar

from PyQt6.QtGui import QColor
from pydantic import BaseModel, field_validator, ConfigDict

from src.utils.resource_path import resource_path

ConfigType = TypeVar("ConfigType", bound=BaseModel)


class Program(BaseModel):
    title: str


class DatabaseTablesConfig(BaseModel):
    projects: str


class DatabaseConfig(BaseModel):
    name: str
    tables: DatabaseTablesConfig


class FtlFieldConfig(BaseModel):
    check: str


class TableColumn(BaseModel):
    icon: str
    variable: str
    translation: str


class Colors(BaseModel):
    highlight: QColor

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("highlight", mode="before")
    def parse_color(cls, v) -> QColor:

        if isinstance(v, list):
            if len(v) < 3:
                raise ValueError("RGB list must contain at least 3 values.")
            return QColor(*v)
        elif isinstance(v, str):
            return QColor(v)
        elif isinstance(v, QColor):
            return v
        else:
            raise ValueError(f"Unsupported colour format: {v}")


@lru_cache
def parse_config_file() -> dict:
    file_path = resource_path("config.toml")
    if file_path is None:
        error = "Could not find settings file"
        raise ValueError(error)

    with open(file_path, "rb") as file:
        config_data = load(file)
    return config_data


@lru_cache
def get_config(model: Type[ConfigType], root_key: str) -> ConfigType:
    config_dict = parse_config_file()
    if root_key not in config_dict:
        error = f"Key {root_key} not found"
        raise ValueError(error)
    return model.model_validate(config_dict[root_key])
