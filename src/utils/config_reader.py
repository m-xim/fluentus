from functools import lru_cache
from tomllib import load
from typing import Type, TypeVar
from pydantic import BaseModel

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
