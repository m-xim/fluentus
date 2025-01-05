from collections import defaultdict
from typing import Optional, DefaultDict

from pydantic import BaseModel, ConfigDict, Field


class Translation(BaseModel):
    value: Optional[str] = Field(default_factory=str)
    attributes: DefaultDict[str, str] = Field(default_factory=lambda: defaultdict(str))
    comment: Optional[str] = None
    check: bool = False
    filepath: Optional[str] = None

    model_config = ConfigDict(validate_assignment=True, arbitrary_types_allowed=True)

    # TODO: add check Junk


Translation.model_rebuild()

LanguagesType = DefaultDict[str, Translation]
TranslationsType = DefaultDict[str, LanguagesType]

Languages: LanguagesType = defaultdict(Translation)
Translations: TranslationsType = defaultdict(lambda: defaultdict(Translation))
