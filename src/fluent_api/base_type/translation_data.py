from typing import Optional, Dict

from pydantic import BaseModel, ConfigDict, Field


class TranslationData(BaseModel):
    value: Optional[str] = Field(default_factory=list)
    attributes: Optional[Dict[str, str]] = Field(default_factory=dict[str, str])
    comment: Optional[str] = None
    check: bool = False
    patch: Optional[str] = None

    model_config = ConfigDict(validate_assignment=True, arbitrary_types_allowed=True)

    # TODO: add check Junk


TranslationData.model_rebuild()
