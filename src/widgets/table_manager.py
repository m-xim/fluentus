import re
from collections import defaultdict
from typing import Optional, Callable, Iterable

from PyQt6.QtGui import QColor, QIcon
from PyQt6.QtWidgets import QHeaderView, QTreeWidget, QTreeWidgetItem

from src.fluent_api.FluentAPI import FluentAPI
from src.fluent_api.base_type.translations import LanguagesType
from src.utils.resource_path import resource_path


class TableManager:
    """Manages the variable table and synchronizes updates."""

    # Column indices
    COLUMN_ICON = 0
    COLUMN_VARIABLE = 1
    COLUMN_TRANSLATION1 = 2
    COLUMN_TRANSLATION2 = 3

    COLUMN_COUNT = 4

    # Colors for text highlighting
    COLOR_HIGHLIGHT = QColor(230, 200, 49)
    COLOR_DEFAULT = QColor(255, 255, 255)

    # Path to the comment icon
    ICON_COMMENT_PATH = resource_path("resource/icons/comment.png")

    # Fixed width for the icon column
    FIXED_COLUMN_WIDTH = 45

    def __init__(
            self,
            table: QTreeWidget,
            fluent_api: FluentAPI,
            item_clicked_callback: Optional[Callable] = None
    ):
        """
        Initializes the TableManager.

        :param table: The QTreeWidget instance to manage.
        """
        self.table = table
        self.fluent_api = fluent_api
        self.item_clicked_callback = item_clicked_callback

        self.translations = self.fluent_api.translations

        self.comment_icon = QIcon(self.ICON_COMMENT_PATH)
        self._setup_table()

    def _setup_table(self):
        """Configures the table settings."""

        self.table.setSelectionBehavior(QTreeWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)

        self.table.itemSelectionChanged.connect(self.item_clicked_callback)

        self.table.setColumnCount(self.COLUMN_COUNT)
        self.set_headers()
        self.table.header().setSectionResizeMode(self.COLUMN_ICON, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(self.COLUMN_ICON, self.FIXED_COLUMN_WIDTH)

    def set_current_item(self, lang1: str, lang2: str):
        """
        Updates the current item's translations and formatting based on the provided languages.

        :param lang1: The first language code.
        :param lang2: The second language code.
        """

        variable, attribute = self.get_variable()
        if not variable:
            return

        variable_item, attribute_item = self.get_item()

        languages = self.translations[variable]

        if attribute:
            self._update_attribute_item(attribute_item, languages, attribute, lang1, lang2)
        else:
            self._update_variable_item(variable_item, languages, lang1, lang2)

        self._update_icon_and_formatting(variable_item, languages, lang1, lang2)

    def _update_variable_item(self, variable_item: QTreeWidgetItem, languages: LanguagesType, lang1: str, lang2: str) -> None:
        """Updates the variable item's translations."""

        # Update Translation 1
        translation1_new = self._extract_text(languages[lang1].value)
        translation1_old = variable_item.text(self.COLUMN_TRANSLATION1)
        if translation1_new != translation1_old:
            variable_item.setText(self.COLUMN_TRANSLATION1, translation1_new)

        # Update Translation 2
        translation2_new = self._extract_text(languages[lang2].value)
        translation2_old = variable_item.text(self.COLUMN_TRANSLATION2)
        if translation2_new != translation2_old:
            variable_item.setText(self.COLUMN_TRANSLATION2, translation2_new)

    def _update_attribute_item(
            self, attribute_item: QTreeWidgetItem, languages: LanguagesType, attribute: str, lang1: str, lang2: str
    ) -> None:
        """Updates the attribute item's translations."""

        # Update Translation 1
        translation1_new = self._extract_text(languages[lang1].attributes[attribute])
        translation1_old = attribute_item.text(self.COLUMN_TRANSLATION1)
        if translation1_new != translation1_old:
            attribute_item.setText(self.COLUMN_TRANSLATION1, translation1_new)

        # Update Translation 2
        translation2_new = self._extract_text(languages[lang2].attributes[attribute])
        translation2_old = attribute_item.text(self.COLUMN_TRANSLATION2)
        if translation2_new != translation2_old:
            attribute_item.setText(self.COLUMN_TRANSLATION2, translation2_new)

    def _update_icon_and_formatting(self, variable_item: QTreeWidgetItem, languages: LanguagesType, lang1: str, lang2: str) -> None:
        """Sets the icon and text formatting based on comments and checks."""

        # Set icon
        has_comment = bool(languages[lang1].comment or languages[lang2].comment)
        variable_item.setIcon(self.COLUMN_ICON, self.comment_icon if has_comment else QIcon())

        # Set foreground colors
        highlight_lang1 = self.COLOR_HIGHLIGHT if languages[lang1].check else self.COLOR_DEFAULT
        highlight_lang2 = self.COLOR_HIGHLIGHT if languages[lang2].check else self.COLOR_DEFAULT
        variable_item.setForeground(self.COLUMN_TRANSLATION1, highlight_lang1)
        variable_item.setForeground(self.COLUMN_TRANSLATION2, highlight_lang2)

    def populate_table(self, lang1: str, lang2: str):
        """
        Populates the table with variables and translations, preserving the user's selection.

        :param lang1: The first language code.
        :param lang2: The second language code.
        """
        selected_variable, selected_attribute = self.get_variable()

        self.table.clear()

        for variable, languages in self.translations.items():
            item = self._create_top_level_item(variable, languages, lang1, lang2)
            self.table.addTopLevelItem(item)

        self.set_headers(lang1, lang2)
        self._restore_selection(selected_variable, selected_attribute)

    def _create_top_level_item(self, variable: str, languages: LanguagesType, lang1: str, lang2: str) -> QTreeWidgetItem:
        """
        Creates a top-level table item with translations and attributes.

        :param variable: The variable name.
        :param languages: The data associated with the variable.
        :param lang1: The first language code.
        :param lang2: The second language code.
        :return: A configured QTreeWidgetItem.
        """
        translation1 = self._extract_text(languages[lang1].value)
        translation2 = self._extract_text(languages[lang2].value)
        item = QTreeWidgetItem([
            "",  # Empty cell for the icon
            variable,
            translation1,
            translation2
        ])
        # Set icon and formatting
        self._update_icon_and_formatting(item, languages, lang1, lang2)

        # Add child items for attributes
        attributes = self.aggregate_attributes(languages, self.fluent_api.get_languages())
        for attr_name, attr_values in attributes.items():
            child_item = QTreeWidgetItem([
                "",  # Empty cell for the icon
                attr_name,
                self._extract_text(attr_values.get(lang1, '')),
                self._extract_text(attr_values.get(lang2, ''))
            ])
            item.addChild(child_item)

        return item

    @staticmethod
    def _extract_text(contents: str) -> str:
        """
        Joins a list of content into a single string.

        :param contents: List of content objects.
        :return: Concatenated string.
        """

        if not contents:
            return ''
        return re.sub(pattern=FluentAPI.RE_LINE_SPLIT_PATTERN, repl='➚', string=contents)

    @staticmethod
    def aggregate_attributes(languages: LanguagesType, langs: Iterable[str]) -> defaultdict[str, dict]:
        """
        Aggregate attributes for languages.

        :param languages: The data containing attributes.
        :param langs: Languages code.
        :return: A dictionary of attributes with their translations.
        """
        attributes = defaultdict(lambda: defaultdict(str))

        for lang in langs:
            lang_data = languages[lang]
            if lang_data and lang_data.attributes:
                for name, attr_value in lang_data.attributes.items():
                    attributes[name][lang] = attr_value or ''

        return attributes

    def _restore_selection(self, variable: str, attribute: str):
        """
        Restores the selection based on remembered variable and attribute.

        :param variable: The previously selected variable.
        :param attribute: The previously selected attribute.
        """
        if not variable:
            return

        for i in range(self.table.topLevelItemCount()):
            parent_item = self.table.topLevelItem(i)
            if parent_item.text(self.COLUMN_VARIABLE) == variable:
                self.table.setCurrentItem(parent_item)
                if attribute:
                    for j in range(parent_item.childCount()):
                        child_item = parent_item.child(j)
                        if child_item.text(self.COLUMN_VARIABLE) == attribute:
                            self.table.setCurrentItem(child_item)
                            return
                return
            
    def set_headers(self, lang1: Optional[str] = None, lang2: Optional[str] = None):
        """
        Sets the headers of the table, optionally including language codes.

        :param lang1: The first language code.
        :param lang2: The second language code.
        """

        lang1_name = 'Translation 1'
        if lang1 is not None:
            lang1_name += f' — {lang1}'

        lang2_name = 'Translation 2'
        if lang2 is not None:
            lang2_name += f' — {lang2}'

        headers = ['', 'Variable', lang1_name, lang2_name]
        self.table.setHeaderLabels(headers)

    def get_item(self) -> tuple[QTreeWidgetItem | None, QTreeWidgetItem | None]:
        """
        Retrieves the selected item.

        :return: The selected QTreeWidgetItem or None.
        """
        selected_items = self.table.currentItem()
        if selected_items:
            item = selected_items
            parent = item.parent()
            if parent:
                return parent, item
            return item, None
        return None, None

    def get_variable(self) -> tuple[str | None, str | None]:
        """
        Retrieves the selected variable and attribute.

        :return: A tuple containing the selected variable and attribute.
        """
        parent, item = self.get_item()
        return parent.text(self.COLUMN_VARIABLE) if parent else None, item.text(self.COLUMN_VARIABLE) if item else None
