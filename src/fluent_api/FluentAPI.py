import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Union, List, Any, Set, Optional, DefaultDict

from fluent.syntax import parse, serialize, FluentParser
from fluent.syntax.ast import (Resource, TextElement, Placeable, Junk, Message, Term, Comment, PatternElement,
                               Attribute, Identifier, Pattern)
from fluent.syntax.serializer import serialize_placeable
from loguru import logger

from src.fluent_api.base_type.elements import elements_type
from src.fluent_api.base_type.translations import Translation, TranslationsType
from src.fluent_api.utils.bool_and_string import string_bool, bool_to_string
from src.utils.config_reader import get_config, FtlFieldConfig


class FluentAPI:
    RE_NEWLINE_PATTERN = re.compile(r'\n(?!\\\\) ')
    RE_LINE_SPLIT_PATTERN = re.compile(r'\n(?!\\\\)')
    RE_SEARCH_WHITESPACE = re.compile(r'(\s+)$')
    RE_SUB_IN_JUNK = re.compile(r'\n(?!\\\\)\s\s\s\s')

    def __init__(self, folder_path: Optional[str]):
        self.config: FtlFieldConfig = get_config(FtlFieldConfig, root_key='ftl_field')
        self.bundles = defaultdict(list)  # Dictionary to store paths to .ftl files by language
        self.translations: TranslationsType = defaultdict(lambda: defaultdict(Translation))

        self.folder_path = folder_path
        self._load_ftl_files(folder_path=folder_path)

        self.edited: bool = False

    def get_languages(self) -> List[str]:
        """Return a list of all loaded languages."""
        return list(self.bundles.keys())

    def get_variables(self) -> Set[str]:
        """Return a set of all unique variables in the cache."""
        return set(self.translations.keys())

    def get_translation(self, variable: str, language: str) -> Translation:
        """Get translation data for a given variable and language."""
        return self.translations[variable][language]

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
            translation = self.translations[variable][language]
        except KeyError as e:
            key = e.args[0]
            error_message = f"Variable '{variable}' not found." if key == variable else \
                f"Language '{language}' not found for variable '{variable}'."
            logger.error(error_message)
            raise KeyError(error_message) from e

        # Determine if there's a value to update
        if value or value in {False, 0}:
            if field in {'value', 'attributes'}:
                sanitized_value = re.sub(self.RE_NEWLINE_PATTERN, '\n', value)
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
            current_value = translation.attributes[attribute]
            if current_value != parsed_value:
                translation.attributes[attribute] = parsed_value
                self.edited = True
                logger.info(
                    f"Update value attribute '{attribute}' for variable '{variable}' and language '{language}'. "
                    f"{current_value=}  -> {value=} -> {parsed_value=}"
                )
                return True
        else:
            current_value = getattr(translation, field, None)
            values_differ = (
                current_value != parsed_value
                if field == 'value'
                else current_value != parsed_value
            )

            if values_differ:
                setattr(translation, field, parsed_value)
                self.edited = True
                logger.info(
                    f"Update field '{field}' for variable '{variable}' and language '{language}'. "
                    f"{current_value=}  -> {value=} -> {parsed_value=}"
                )
                return True

        return False

    def parse_fluent_ast(
            self, resource: Resource, lang_folder: Optional[str] = None, filepath: Optional[Path] = None
    ) -> TranslationsType:
        """
        Parses a Fluent AST and updates the internal translations cache.

        Args:
            resource (Resource): The Fluent AST resource.
            lang_folder (Optional[str]): The language code (locale folder).
            filepath (Optional[Path]): The file path of the translation file.

        Returns:
            TranslationsType: The updated translations cache.
        """
        for entry in resource.body:
            if isinstance(entry, (Message, Term)):
                var_name = f"-{entry.id.name}" if isinstance(entry, Term) else entry.id.name

                try:
                    self.translations[var_name][lang_folder] = self.parse_message(entry, filepath=filepath)
                except Exception as e:
                    logger.error(f"Error parsing {type(entry)} '{entry.id.name}': {e}")
            else:
                logger.warning(f"Unsupported entry type: {type(entry)}")

        return self.translations

    def parse_message(self, entry: Union[Message, Term], filepath: Optional[Path] = None) -> Translation:
        """
            Parses a message or term and returns a Translation object.

            Args:
                entry (Union[Message, Term]): The entry to parse.
                filepath (Optional[str]): File path for the translation, if available.

            Returns:
                Translation: Parsed translation data.
            """

        # Parse the comment
        comment, check = self._parse_comment(entry.comment)

        # Parse attributes
        attributes = {}
        if entry.attributes:
            for attr in entry.attributes:
                try:
                    attr_value = self.elements_to_str(attr.value.elements)
                except Exception as e:
                    attr_value = ''
                    logger.error(f"Error parsing attribute '{attr.id.name}' in {filepath or 'unknown'}: {e}")
                attributes[f'.{attr.id.name}'] = attr_value

        # Parse value
        value = self.elements_to_str(entry.value.elements) if entry.value else ''

        return Translation(value=value, attributes=attributes, comment=comment, check=check, filepath=filepath)

    def _parse_comment(self, comment: Optional[Comment]) -> tuple[Optional[str], bool]:
        """
        Parses a comment to extract its text and check status.

        Args:
            comment (Optional[Comment]): The comment to parse.

        Returns:
            tuple[Optional[str], bool]: A tuple containing the comment text (if any)
            and a boolean indicating the check status.
        """

        if not comment:
            return None, False

        comments_row = re.split(self.RE_LINE_SPLIT_PATTERN, comment.content)
        check_prefix = f'@{self.config.check}: '
        comments = []
        check = False

        for row in comments_row:
            row = row.strip()
            if row.startswith(check_prefix):
                check_value = row.removeprefix(check_prefix).strip()
                check = string_bool(check_value)
            else:
                comments.append(row)

        comments_text = "\n".join(comments) if comments else None
        return comments_text, check

    @staticmethod
    def serialize_element(element: PatternElement) -> str:
        if isinstance(element, TextElement):
            return element.value
        if isinstance(element, Junk):
            return element.content.removeprefix('variable =').strip()
        if isinstance(element, Placeable):
            return serialize_placeable(element)
        raise Exception('Unknown element type: {}'.format(type(element)))

    @staticmethod
    def elements_to_str(elements: elements_type) -> str:
        return ''.join(FluentAPI.serialize_element(element) for element in elements)

    @staticmethod
    def parse_str_to_ast(value: str) -> list[TextElement | Placeable]:
        sanitized_value = re.sub(FluentAPI.RE_LINE_SPLIT_PATTERN, '\n    ', value)
        parsed = FluentParser(with_spans=False).parse_entry("variable ="
                                                            f"\n    {sanitized_value}")
        if isinstance(parsed, Junk):
            logger.warning(f'Junk: {parsed}')
            value = re.sub(FluentAPI.RE_SUB_IN_JUNK, '\n', (parsed.content.removeprefix('variable =').strip()))
            return [TextElement(value=value)]
        return parsed.value.elements

    @staticmethod
    def elements_to_beautiful_str(value: str) -> tuple[str, bool]:
        parsed_entry = FluentAPI.parse_str_to_ast(value)
        parsed_value = []
        exist_junk = False
        for i in parsed_entry:
            if isinstance(i, Junk):
                exist_junk = True
                parsed_value.append(i)
            else:
                parsed_value.append(i)

        beautiful_str = FluentAPI.elements_to_str(parsed_value)

        if match := re.search(FluentAPI.RE_SEARCH_WHITESPACE, value):
            beautiful_str += match.group(1)

        return beautiful_str, exist_junk

    def translation_data_to_ast(self, translation_data: Translation, name: Optional[str] = None) -> Term | Message:
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
            return Term(
                id=Identifier(name=name.removeprefix('-')),
                value=Pattern(elements=self.parse_str_to_ast(translation_data.value)),
                attributes=attributes,
                comment=comment_ast
            )

        if not translation_data.value:
            ast_value = None
        else:
            # Create value
            ast_value = Pattern(elements=self.parse_str_to_ast(translation_data.value))
        return Message(id=Identifier(name=name), value=ast_value, attributes=attributes, comment=comment_ast)

    def _load_ftl_files(self, folder_path: str) -> None:
        # TODO: add a check for .ftl files

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

            self.parse_fluent_ast(resource, lang_folder=lang_folder, filepath=ftl_path)
            self.bundles[lang_folder].append(ftl_path)
        except Exception as e:
            logger.error(f"Error loading file {ftl_path}: {e}")

    def save_all_files(self, target_folder: Optional[str] = None):
        file_content_map: DefaultDict[str, List[Message | Term]] = defaultdict(list)

        for variable_name, translations_by_lang in self.translations.items():
            for language, translation_data in translations_by_lang.items():
                if not translation_data.filepath:
                    logger.error(f"Missing filepath for variable '{variable_name}': {translation_data.filepath}")
                    raise ValueError(f"Filepath is missing for language '{language}', variable '{variable_name}'")

                # Determine the output filepath
                output_filepath = (
                    translation_data.filepath.replace(self.folder_path, target_folder)
                    if target_folder else translation_data.filepath
                )

                # Generate translation AST and append to the file content map
                file_content_map[output_filepath].append(
                    self.translation_data_to_ast(translation_data, variable_name)
                )

        # Write content to the respective files
        for filepath, content_ast in file_content_map.items():
            output_path = Path(filepath)
            output_path.parent.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists

            with output_path.open('w', encoding='utf-8') as file:
                file.write(serialize(Resource(body=content_ast)))

        self.edited = False
