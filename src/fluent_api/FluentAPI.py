import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Union, List, Dict, Any, Set, Optional

from fluent.syntax import parse, serialize, FluentParser
from fluent.syntax.ast import (Resource, TextElement, Placeable, Junk, Message, Term, Comment, PatternElement,
                               Attribute, Identifier, Pattern)
from fluent.syntax.serializer import serialize_placeable
from loguru import logger

from src.fluent_api.base_type.elements import elements_type
from src.fluent_api.base_type.translation_data import TranslationData
from src.fluent_api.utils.bool_and_string import string_bool, bool_to_string
from src.utils.config_reader import get_config, FtlFieldConfig


class FluentAPI:
    def __init__(self, folder_path: Optional[str] = None):
        self.config = get_config(FtlFieldConfig, root_key='ftl_field')
        self.bundles = defaultdict(list)  # Dictionary to store paths to .ftl files by language
        self.translations_data = defaultdict(lambda: defaultdict(TranslationData))

        self.folder_path = folder_path
        if self.folder_path is not None:
            self.load_ftl_files(folder_path=folder_path)

        self.edited: bool = False

    def get_languages(self) -> List[str]:
        """Return a list of all loaded languages."""
        return list(self.bundles.keys())

    def get_variables(self) -> Set[str]:
        """Return a set of all unique variables in the cache."""
        return set(self.translations_data.keys())

    def get_translation(self, variable: str, language: str) -> TranslationData:
        """Get translation data for a given variable and language."""
        return self.translations_data.get(variable, {}).get(language, TranslationData())

    def update(self, variable: str, language: str, field: str, value: Any, attribute: Optional[str] = None) -> bool:
        """
        Update the value for a given variable and language in the cache.

        Args:
            variable (str): Variable name.
            language (str): Language code.
            field (str): Field to update ('value' or 'attributes').
            value (Any): New value for the field.
            attribute (Optional[str]): Attribute name (used if field is 'value').
        """

        # Validate existence of variable and language
        try:
            translation_entry = self.translations_data[variable][language]
        except KeyError as e:
            key = e.args[0]
            error_message = f"Variable '{variable}' not found." if key == variable else \
                f"Language '{language}' not found for variable '{variable}'."
            logger.error(error_message)
            raise KeyError(error_message) from e

        # Determine if there's a value to update
        if value or value in {False, 0}:
            if field in {'value', 'attributes'}:
                sanitized_value = re.sub(r'\n(?!\\\\) ', '\n ', value)
                beautiful_value, exist_junk = self.elements_to_beautiful_str(sanitized_value)

                if exist_junk:
                    parsed_value = value
                else:
                    parsed_value = beautiful_value

            else:
                parsed_value = value
        else:
            parsed_value = '' if field in {'value', 'attributes'} else None

        if attribute and field == 'value':
            attribute = attribute
            current_value = translation_entry.attributes.get(attribute)
            if current_value != parsed_value:
                translation_entry.attributes[attribute] = parsed_value
                self.edited = True
                logger.info(
                    f"Update value attribute '{attribute}' for variable '{variable}' and language '{language}'. "
                    f"{current_value=}  -> {value=} -> {parsed_value=}"
                )
                return True
        else:
            current_value = getattr(translation_entry, field, None)
            values_differ = (
                current_value != parsed_value
                if field == 'value'
                else current_value != parsed_value
            )

            if values_differ:
                setattr(translation_entry, field, parsed_value)
                self.edited = True
                logger.info(
                    f"Update field '{field}' for variable '{variable}' and language '{language}'. "
                    f"{current_value=}  -> {value=} -> {parsed_value=}"
                )
                return True

        return False

    def parse_fluent_ast(self, resource: Resource, lang_folder: str = None, file_patch: str = None) \
            -> Dict[str, Dict[str, TranslationData]]:
        for entry in resource.body:
            if isinstance(entry, Message):
                self._parse_message_or_term(entry, lang_folder, file_patch)
            elif isinstance(entry, Term):
                self._parse_message_or_term(entry, lang_folder, file_patch, is_term=True)
            else:
                logger.warning(f"Unsupported entry type: {type(entry)}")
        return self.translations_data

    def _parse_message_or_term(self, entry, lang_folder, file_patch, is_term=False):
        try:
            var_name = f"-{entry.id.name}" if is_term else entry.id.name
            self.translations_data[var_name][lang_folder] = self.parse_message(entry, file_patch=file_patch)
        except Exception as e:
            logger.error(f"Error parsing {'term' if is_term else 'message'} '{entry.id.name}': {e}")

    def parse_message(self, entry: Union[Message, Term], file_patch: str = None) -> TranslationData:
        comment, check = self._parse_comment(entry.comment)

        attributes = {}
        if entry.attributes:
            for attr in entry.attributes:
                attr_name = f'.{attr.id.name}'
                try:
                    attributes[attr_name] = self.elements_to_str(attr.value.elements)
                except Exception as e:
                    logger.error(f"Error parsing attribute '{attr.id.name}': {e}")
                    attributes[attr_name] = []

        value = self.elements_to_str(entry.value.elements) if entry.value else ''
        
        return TranslationData(value=value, attributes=attributes, comment=comment, check=check, patch=file_patch)

    def _parse_comment(self, comment: Optional[Comment]) -> tuple[Optional[str], bool]:
        if comment:
            comments_row = re.split(r'\n(?!\\\\)', comment.content)
            comments = []
            check = False
            for row in comments_row:
                if row.startswith(f'@{self.config.check}'):
                    check_value = row.removeprefix(f'@{self.config.check}: ').strip()
                    check = string_bool(check_value)
                else:
                    comments.append(row)
            comments_text = "\n".join(comments) if comments else None
        else:
            comments_text = None
            check = False

        return comments_text, check

    @staticmethod
    def serialize_element(element: PatternElement) -> str:
        if isinstance(element, TextElement):
            return element.value
        if isinstance(element, Junk):
            return element.content.removeprefix('variable = ')
        if isinstance(element, Placeable):
            return serialize_placeable(element)
        raise Exception('Unknown element type: {}'.format(type(element)))

    @staticmethod
    def elements_to_str(elements: elements_type) -> str:
        if not elements:
            return ''
        return ''.join(FluentAPI.serialize_element(element) for element in elements)

    @staticmethod
    def parse_str_to_ast(value: str) -> list[TextElement | Placeable]:
        sanitized_value = re.sub(r'\n(?!\\\\)', '\n ', value)
        parsed = FluentParser(with_spans=False).parse_entry(f"variable = {sanitized_value}")
        if isinstance(parsed, Junk):
            logger.warning(f'Junk: {parsed}')
            return [TextElement(value=parsed.content)]
        return parsed.value.elements

    @staticmethod
    def elements_to_beautiful_str(value: str) -> tuple[str, bool]:
        parsed_entry = FluentParser().parse(f"variable = {value}")
        parsed_value = []
        for i in parsed_entry.body:
            if isinstance(i, Junk):
                return value, True
            else:
                parsed_value.extend(i.value.elements)

        beautiful_str = FluentAPI.elements_to_str(parsed_value)
        if value.endswith('\n'):
            beautiful_str += '\n'
        return beautiful_str, False

    def translation_data_to_ast(self, translation_data: TranslationData,
                                name: Optional[str] = None) -> Term | Message:
        # Create comment
        comment = translation_data.comment or None

        if translation_data.check:
            check_str = f"@{self.config.check}: {bool_to_string(translation_data.check)}"
            comment = f"{comment}\n{check_str}" if comment else check_str

        comment_ast = Comment(content=comment) if comment else None

        # Create attributes
        attributes = [
            Attribute(
                id=Identifier(name=key.removeprefix('.')),
                value=Pattern(elements=self.parse_str_to_ast(value))
            )
            for key, value in translation_data.attributes.items()
        ]

        # Create Term or Message
        if name.startswith('-'):
            # Create value
            ast_value = Pattern(elements=self.parse_str_to_ast(translation_data.value))

            return Term(
                id=Identifier(name=name.removeprefix('-')), 
                value=ast_value, 
                attributes=attributes, 
                comment=comment_ast
            )

        if not translation_data.value:
            ast_value = None
        else:
            # Create value
            ast_value = Pattern(elements=self.parse_str_to_ast(translation_data.value))
        return Message(id=Identifier(name=name), value=ast_value, attributes=attributes, comment=comment_ast)

    def load_ftl_files(self, folder_path: str) -> None:
        self.folder_path = folder_path

        for lang_folder in filter(lambda d: os.path.isdir(os.path.join(folder_path, d)), os.listdir(folder_path)):
            lang_path = os.path.join(folder_path, lang_folder)
            for file_name in filter(lambda f: f.endswith(".ftl"), os.listdir(lang_path)):
                file_path = os.path.join(lang_path, file_name)
                self._load_single_file(file_path, lang_folder)

    def _load_single_file(self, ftl_path: str, lang_folder: str) -> None:
        try:
            with open(ftl_path, 'r', encoding='utf-8') as file:
                resource = parse(file.read())

                self.parse_fluent_ast(resource, lang_folder=lang_folder, file_patch=ftl_path)
                self.bundles[lang_folder].append(ftl_path)
        except Exception as e:
            logger.error(f"Error loading file {ftl_path}: {e}")

    def save_all_files(self, new_patch_folder: Optional[str] = None):
        bodies: Dict[str, List[Message | Term]] = defaultdict(list)

        for variable, tdata_langs in self.translations_data.items():
            for lang, tdata in tdata_langs.items():
                if not tdata.patch:
                    logger.error(f'{variable}: {tdata.patch}')
                    raise Exception(f'Patch for {lang=}, {variable=} is {tdata.patch}')

                if new_patch_folder:
                    patch_file = tdata.patch.replace(self.folder_path, new_patch_folder)
                else:
                    patch_file = tdata.patch

                bodies[patch_file].append(self.translation_data_to_ast(tdata, variable))

            for patch_file, body in bodies.items():
                patch_path = Path(patch_file)
                patch_path.parent.mkdir(parents=True, exist_ok=True)

                with patch_path.open('w', encoding='utf-8') as file:
                    file.write(serialize(Resource(body=body)))

        self.edited = False
