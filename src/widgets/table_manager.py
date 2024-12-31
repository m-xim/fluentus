import re
from typing import Optional, Callable

from PyQt6.QtGui import QColor, QIcon
from PyQt6.QtWidgets import QHeaderView, QTreeWidget, QTreeWidgetItem

from src.utils.resource_path import resource_path


class TableManager:
    """Manages the variable table and synchronizes updates."""

    # Column indices
    COLUMN_ICON = 0
    COLUMN_VARIABLE = 1
    COLUMN_TRANSLATION1 = 2
    COLUMN_TRANSLATION2 = 3

    # Header labels for the columns
    HEADER_LABELS = ["", "Variable", "Translation 1", "Translation 2"]

    # Colors for text highlighting
    COLOR_HIGHLIGHT = QColor(230, 200, 49)
    COLOR_DEFAULT = QColor(255, 255, 255)

    # Path to the comment icon
    ICON_COMMENT_PATH = resource_path("resource/icons/comment.png")

    # Fixed width for the icon column
    FIXED_COLUMN_WIDTH = 45

    def __init__(self, table_widget: QTreeWidget, messages_cache,
                 item_clicked_callback: Optional[Callable] = None):
        """
        Initializes the TableManager.

        :param table_widget: The QTreeWidget instance to manage.
        :param messages_cache: Cache containing message data.
        """
        self.table_widget = table_widget
        self.messages_cache = messages_cache
        self.item_clicked_callback = item_clicked_callback

        self.comment_icon = QIcon(self.ICON_COMMENT_PATH)
        self._setup_table()

    def _setup_table(self):
        """Configures the table settings."""

        self.table_widget.setSelectionBehavior(QTreeWidget.SelectionBehavior.SelectRows)
        self.table_widget.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        # self.table_widget.itemClicked.connect(self.item_clicked_callback)

        # FIXME: Called when user values and auto adjustments change
        self.table_widget.itemSelectionChanged.connect(self.item_clicked_callback)

        self.table_widget.setColumnCount(len(self.HEADER_LABELS))
        self.table_widget.setHeaderLabels(self.HEADER_LABELS)
        self.table_widget.header().setSectionResizeMode(
            self.COLUMN_ICON, QHeaderView.ResizeMode.Fixed
        )
        self.table_widget.setColumnWidth(self.COLUMN_ICON, self.FIXED_COLUMN_WIDTH)

    def populate_table(self, lang1: str, lang2: str):
        """
        Populates the table with variables and translations, preserving the user's selection.

        :param lang1: The first language code.
        :param lang2: The second language code.
        """
        selected_variable, selected_attribute = self._get_selection()

        self.table_widget.clear()

        for variable, data in self.messages_cache.items():
            item = self._create_top_level_item(variable, data, lang1, lang2)
            self.table_widget.addTopLevelItem(item)

        self._restore_selection(selected_variable, selected_attribute)

    def _create_top_level_item(self, variable, data, lang1, lang2) -> QTreeWidgetItem:
        """
        Creates a top-level table item with translations and attributes.

        :param variable: The variable name.
        :param data: The data associated with the variable.
        :param lang1: The first language code.
        :param lang2: The second language code.
        :return: A configured QTreeWidgetItem.
        """
        translation1 = self._extract_text(data[lang1].value)
        translation2 = self._extract_text(data[lang2].value)
        item = QTreeWidgetItem([
            "",  # Empty cell for the icon
            variable,
            translation1,
            translation2
        ])
        # Set icon and formatting
        if data[lang1].comment or data[lang2].comment:
            item.setIcon(self.COLUMN_ICON, self.comment_icon)

        item.setForeground(
            self.COLUMN_TRANSLATION1,
            self.COLOR_HIGHLIGHT if data[lang1].check else self.COLOR_DEFAULT
        )
        item.setForeground(
            self.COLUMN_TRANSLATION2,
            self.COLOR_HIGHLIGHT if data[lang2].check else self.COLOR_DEFAULT
        )

        # Add child items for attributes
        attributes = self._process_attributes(data, lang1, lang2)
        for attr_name, attr_values in attributes.items():
            child_item = QTreeWidgetItem([
                "",  # Empty cell for the icon
                attr_name,
                self._extract_text(attr_values.get(lang1, [])),
                self._extract_text(attr_values.get(lang2, []))
            ])
            item.addChild(child_item)

        return item

    @staticmethod
    def _extract_text(contents) -> str:
        """
        Joins a list of content into a single string.

        :param contents: List of content objects.
        :return: Concatenated string.
        """

        if not contents:
            return ''
        return re.sub(pattern=r'\n(?!\\\\)', repl='➚', string=contents)

    @staticmethod
    def _process_attributes(data, lang1, lang2) -> dict:
        """
        Processes attributes for both languages.

        :param data: The data containing attributes.
        :param lang1: The first language code.
        :param lang2: The second language code.
        :return: A dictionary of attributes with their translations.
        """
        attributes = {}
        for lang in (lang1, lang2):
            lang_data = data[lang]
            if lang_data and lang_data.attributes:
                for name, attr_value in lang_data.attributes.items():
                    attributes.setdefault(name, {}).update({
                        lang: attr_value or []
                    })
        return attributes

    def _get_selection(self) -> tuple[str, str] | tuple[str, None] | tuple[None, None]:
        """
        Remembers the currently selected item.

        :return: A tuple containing the selected variable and attribute.
        """
        current_item = self.table_widget.currentItem()
        if current_item:
            parent = current_item.parent()
            if parent:
                return parent.text(self.COLUMN_VARIABLE), current_item.text(self.COLUMN_VARIABLE)
            return current_item.text(self.COLUMN_VARIABLE), None
        return None, None

    def _restore_selection(self, variable: str, attribute: str):
        """
        Restores the selection based on remembered variable and attribute.

        :param variable: The previously selected variable.
        :param attribute: The previously selected attribute.
        """
        if not variable:
            return
        for i in range(self.table_widget.topLevelItemCount()):
            parent_item = self.table_widget.topLevelItem(i)
            if parent_item.text(self.COLUMN_VARIABLE) == variable:
                self.table_widget.setCurrentItem(parent_item)
                if attribute:
                    for j in range(parent_item.childCount()):
                        child_item = parent_item.child(j)
                        if child_item.text(self.COLUMN_VARIABLE) == attribute:
                            self.table_widget.setCurrentItem(child_item)
                            return
                return

    def get_variable(self) -> tuple[str, str] | tuple[str, None] | tuple[None, None]:
        """
        Retrieves the selected variable and attribute.

        :return: A tuple containing the selected variable and attribute.
        """
        selected_items = self.table_widget.selectedItems()
        if selected_items:
            item = selected_items[0]
            parent = item.parent()
            if parent:
                return parent.text(self.COLUMN_VARIABLE), item.text(self.COLUMN_VARIABLE)
            return item.text(self.COLUMN_VARIABLE), None
        return None, None
