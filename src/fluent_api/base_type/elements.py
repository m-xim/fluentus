from typing import Union, List

from fluent.syntax.ast import TextElement, Placeable, Junk

element_type = Union[TextElement, Placeable, Junk]
elements_type = List[element_type]
