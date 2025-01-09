import re
from collections import defaultdict
from typing import Optional, Callable, Iterable, Tuple, Dict

from PyQt6.QtGui import QColor, QIcon
from PyQt6.QtWidgets import QHeaderView, QTreeWidget, QTreeWidgetItem

from src.fluent_api.FluentAPI import FluentAPI
from src.fluent_api.base_type.translations import LanguagesType
from src.utils.config_reader import get_config, TableColumn
from src.utils.resource_path import resource_path


class TableManager:
    """Manages the variable table and synchronizes updates."""

    # Constants for column indices
    ICON_COLUMN_INDEX = 0
    BASE_COLUMN_COUNT = 2

    # Colors for text highlighting
    HIGHLIGHT_COLOR = QColor(230, 200, 49)
    DEFAULT_COLOR = QColor(255, 255, 255)

    # Path to the comment icon
    COMMENT_ICON_PATH = resource_path("resource/icons/comment.png")

    # Fixed width for the icon column
    ICON_COLUMN_WIDTH = 45

    def __init__(
        self,
        table: QTreeWidget,
        fluent_api: FluentAPI,
        on_item_selected_callback: Optional[Callable[[], None]] = None
    ):
        """
        Initializes the TableManager.

        :param table: The QTreeWidget instance to manage.
        :param fluent_api: Instance of FluentAPI for accessing translations.
        :param on_item_selected_callback: Optional callback for item selection changes.
        """

        self.table = table
        self.fluent_api = fluent_api
        self.on_item_selected_callback = on_item_selected_callback

        self.config: TableColumn = get_config(TableColumn, root_key='table_column')

        # Header labels
        self.BASE_HEADERS = [self.config.icon, self.config.variable]

        self.comment_icon = QIcon(self.COMMENT_ICON_PATH)
        self._setup_table()

    def _setup_table(self) -> None:
        """Configures the table settings."""
        self.table.setSelectionBehavior(QTreeWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)

        if self.on_item_selected_callback:
            self.table.itemSelectionChanged.connect(self.on_item_selected_callback)

        self.table.setColumnCount(self.BASE_COLUMN_COUNT + len(self.fluent_api.get_languages()))
        self.table.header().setSectionResizeMode(self.ICON_COLUMN_INDEX, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(self.ICON_COLUMN_INDEX, self.ICON_COLUMN_WIDTH)

    def _find_header_index(self, header_name: str) -> Optional[int]:
        """Finds the column index for a given header name."""
        for index in range(self.table.columnCount()):
            if self.table.headerItem().text(index) == header_name:
                return index
        return None

    def set_current_item(self, language_code: str) -> None:
        """
        Updates the current item's translations and formatting based on the provided language.

        :param language_code: The language code.
        """
        variable_name, attribute_name = self.get_selected_names()
        if not variable_name:
            return

        variable_item, attribute_item = self.get_selected_items()
        if not variable_item:
            return

        translations = self.fluent_api.translations[variable_name]
        header_name = f'{self.config.translation} — {language_code}'
        column_index = self._find_header_index(header_name)
        if column_index is None:
            return  # Header not found

        if attribute_name:
            self._update_attribute_translation(attribute_item, translations, attribute_name, language_code, column_index)
        else:
            self._update_variable_translation(variable_item, translations, language_code, column_index)

        self._apply_icon_and_formatting(variable_item, translations, language_code)

    def _update_variable_translation(
        self,
        variable_item: QTreeWidgetItem,
        translations: LanguagesType,
        language_code: str,
        column_index: int
    ) -> None:
        """Updates the variable item's translation."""
        new_translation = self._extract_text(translations[language_code].value)
        old_translation = variable_item.text(column_index)
        if new_translation != old_translation:
            variable_item.setText(column_index, new_translation)

    def _update_attribute_translation(
        self,
        attribute_item: QTreeWidgetItem,
        translations: LanguagesType,
        attribute_name: str,
        language_code: str,
        column_index: int
    ) -> None:
        """Updates the attribute item's translation."""
        new_translation = self._extract_text(translations[language_code].attributes[attribute_name])
        old_translation = attribute_item.text(column_index)
        if new_translation != old_translation:
            attribute_item.setText(column_index, new_translation)

    def _apply_icon_and_formatting(
        self,
        variable_item: QTreeWidgetItem,
        translations: LanguagesType,
        language_code: str
    ) -> None:
        """Sets the icon and text formatting based on comments and checks."""
        languages = self.fluent_api.get_languages()

        # Set icon
        comment_exists = any(translations[lang].comment for lang in languages)
        variable_item.setIcon(self.ICON_COLUMN_INDEX, self.comment_icon if comment_exists else QIcon())

        # Set foreground color
        language_data = translations[language_code]
        highlight_color = self.HIGHLIGHT_COLOR if language_data.check else self.DEFAULT_COLOR
        column_index = self._find_header_index(f'{self.config.translation} — {language_code}')
        if column_index is not None:
            variable_item.setForeground(column_index, highlight_color)

    def populate_table(self) -> None:
        """
        Populates the table with variables and translations, preserving the user's selection.
        """
        languages = self.fluent_api.get_languages()
        selected_variable, selected_attribute = self.get_selected_items()

        self.table.clear()

        self._initialize_headers(languages)

        for variable_name, translations in self.fluent_api.translations.items():
            table_item = self._create_top_level_item(variable_name, translations, languages)
            self.table.addTopLevelItem(table_item)

        self._restore_selection(selected_variable, selected_attribute)

    def _create_top_level_item(
        self,
        variable_name: str,
        translations: LanguagesType,
        languages: Iterable[str]
    ) -> QTreeWidgetItem:
        """
        Creates a top-level table item with translations and attributes.

        :param variable_name: The variable name.
        :param translations: The data associated with the variable.
        :param languages: Iterable of language codes.
        :return: A configured QTreeWidgetItem.
        """
        item_data = ["", variable_name]
        comment_exists = False

        for language_code in languages:
            language_data = translations[language_code]
            translation = self._extract_text(language_data.value)
            item_data.append(translation)
            if language_data.comment:
                comment_exists = True

        table_item = QTreeWidgetItem(item_data)
        table_item.setIcon(self.ICON_COLUMN_INDEX, self.comment_icon if comment_exists else QIcon())

        for language_code in languages:
            header_name = f'{self.config.translation} — {language_code}'
            column_index = self._find_header_index(header_name)
            if column_index is None:
                continue
            language_data = translations[language_code]
            highlight_color = self.HIGHLIGHT_COLOR if language_data.check else self.DEFAULT_COLOR
            table_item.setForeground(column_index, highlight_color)

        attributes = self._collect_attributes(translations, languages)
        for attribute_name, attribute_translations in attributes.items():
            attribute_data = ['', attribute_name] + [
                self._extract_text(attribute_translations[lang]) for lang in languages
            ]
            child_item = QTreeWidgetItem(attribute_data)
            table_item.addChild(child_item)

        return table_item

    @staticmethod
    def _extract_text(content: str) -> str:
        """
        Processes the content string by replacing line splits with arrows.

        :param content: The original content string.
        :return: The processed string.
        """
        if not content:
            return ''
        return re.sub(pattern=FluentAPI.RE_LINE_SPLIT_PATTERN, repl='➚', string=content)

    @staticmethod
    def _collect_attributes(translations: LanguagesType, languages: Iterable[str]) -> Dict[str, Dict[str, str]]:
        """
        Aggregates attributes for languages.

        :param translations: The data containing attributes.
        :param languages: Iterable of language codes.
        :return: A dictionary of attributes with their translations.
        """
        attributes = defaultdict(lambda: defaultdict(str))

        for language_code in languages:
            language_data = translations[language_code]
            for attr_name, attr_value in language_data.attributes.items():
                attributes[attr_name][language_code] = attr_value or ''

        return attributes

    def _restore_selection(self, variable_name: Optional[str], attribute_name: Optional[str]) -> None:
        """
        Restores the selection based on remembered variable and attribute.

        :param variable_name: The previously selected variable.
        :param attribute_name: The previously selected attribute.
        """
        if not variable_name:
            return

        variable_column = self._find_header_index(self.config.variable)
        if variable_column is None:
            return

        for row_index in range(self.table.topLevelItemCount()):
            parent_item = self.table.topLevelItem(row_index)
            if parent_item.text(variable_column) == variable_name:
                if attribute_name:
                    for child_index in range(parent_item.childCount()):
                        child_item = parent_item.child(child_index)
                        if child_item.text(variable_column) == attribute_name:
                            self.table.setCurrentItem(child_item)
                            return
                self.table.setCurrentItem(parent_item)
                return

    def _initialize_headers(self, languages: Iterable[str]) -> None:
        """
        Sets the headers of the table, including language-specific headers.

        :param languages: Iterable of language codes.
        """
        headers = self.BASE_HEADERS + [f'{self.config.translation} — {lang}' for lang in languages]
        self.table.setHeaderLabels(headers)

    def get_selected_items(self) -> Tuple[Optional[QTreeWidgetItem], Optional[QTreeWidgetItem]]:
        """
        Retrieves the selected item and its parent.

        :return: A tuple containing the parent QTreeWidgetItem and the selected QTreeWidgetItem.
        """
        selected_item = self.table.currentItem()
        if not selected_item:
            return None, None

        parent = selected_item.parent()
        if parent:
            return parent, selected_item
        return selected_item, None

    def get_selected_names(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Retrieves the selected variable and attribute.

        :return: A tuple containing the selected variable and attribute.
        """
        parent_item, selected_item = self.get_selected_items()
        variable_column = self._find_header_index(self.config.variable)
        if variable_column is None:
            return None, None

        variable_name = parent_item.text(variable_column) if parent_item else None
        attribute_name = selected_item.text(variable_column) if selected_item and parent_item else None
        return variable_name, attribute_name
