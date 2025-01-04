from functools import partial
from typing import Optional, Union

from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QMessageBox, QFileDialog, QPlainTextEdit, QCheckBox, QComboBox

from src.fluent_api.FluentAPI import FluentAPI
from src.utils.config_reader import get_config, Program
from src.utils.resource_path import resource_path
from src.widgets.add_press_key_filter import KeyPressFilter
from src.widgets.qt_close_dialog import CloseDialog
from src.widgets.table_manager import TableManager


class FluentusEditor(QWidget):
    """Main application window for Fluent Localization Editor."""

    def __init__(self, folder: Optional[str] = None):
        super().__init__()

        self.window_editor = None
        self.fluent_api = FluentAPI()

        # Load UI
        uic.loadUi(resource_path('resource/ui/editor_window.ui'), self)

        self.editors = [
            (self.value_1, "value", self.lang_1),
            (self.comment_1, "comment", self.lang_1),
            (self.check_1, "check", self.lang_1),
            (self.value_2, "value", self.lang_2),
            (self.comment_2, "comment", self.lang_2),
            (self.check_2, "check", self.lang_2),
        ]

        self.key_press_filter = KeyPressFilter()

        for editor, field, lang in self.editors:
            if isinstance(editor, QPlainTextEdit) and field == 'value':
                editor.installEventFilter(self.key_press_filter)

        # Connect buttons and language selectors
        self.folder_button.clicked.connect(self.select_folder)
        self.lang_1.activated.connect(self.on_language_changed)
        self.lang_2.activated.connect(self.on_language_changed)

        # Initialize table manager
        self.table_manager = TableManager(self.table, self.fluent_api, self.load_variable)

        # Connect save button
        self.save_button.clicked.connect(self.save_all_changes)

        # Connect editor signals dynamically
        for editor, field, lang in self.editors:
            if isinstance(editor, QPlainTextEdit):
                editor.textChanged.connect(partial(self.update_cache, editor, field, lang))
            elif isinstance(editor, QCheckBox):
                editor.stateChanged.connect(partial(self.update_cache, editor, field, lang))

        # Initialize with folder if provided
        if folder:
            self._initialize_folder(folder)

    def on_language_changed(self) -> None:
        """Handle language selection changes."""
        # TODO: Instead of creating a new table, update the current ones
        self.load_table()
        self.load_variable()

    def _initialize_folder(self, folder: str) -> None:
        """Initializes the editor with a specified folder."""
        self.fluent_api.load_ftl_files(folder)
        self.folder_text.setText(folder)
        self.refresh_editing_state()
        self.set_language_selectors()
        self.load_table()

    def save_all_changes(self):
        """Save all changes and notify the user."""
        if self.fluent_api.edited:
            self.fluent_api.save_all_files()
            QMessageBox.information(self, "Save Changes", "All changes have been saved successfully!")
            self.refresh_editing_state(False)
        else:
            QMessageBox.information(self, "No Changes", "No changes have been made.")

    def select_folder(self):
        """Select folder and load .ftl files."""
        folder = QFileDialog.getExistingDirectory(self, "Select locales folder")
        if folder:
            self._initialize_folder(folder)

    def set_language_selectors(self):
        """Populate language selectors with available languages."""
        languages = self.fluent_api.get_languages()
        self.lang_1.clear()
        self.lang_2.clear()
        self.lang_1.addItems(languages)
        self.lang_2.addItems(languages)

        # Set default selections
        self.lang_1.setCurrentIndex(0)
        self.lang_2.setCurrentIndex(1 if len(languages) >= 2 else 0)

    def set_current_item(self):
        lang_1, lang_2 = self.lang_1.currentText(), self.lang_2.currentText()
        if not lang_1 or not lang_2:
            return

        self.table_manager.set_current_item(lang_1, lang_2)

    def load_table(self):
        """Update the table based on selected languages."""
        lang_1, lang_2 = self.lang_1.currentText(), self.lang_2.currentText()
        if not lang_1 or not lang_2:
            return

        self.table_manager.populate_table(lang_1, lang_2)

    def load_variable(self):
        variable, attribute = self.table_manager.get_variable()
        if not variable:
            return

        selected_items = self.table.selectedItems()
        if selected_items:
            self.table_manager.current_item = selected_items[0]

        for editor, field, lang in self.editors:
            language = lang.currentText()
            data = self.fluent_api.get_translation(variable, language)

            if attribute and field == 'value':
                content = data.attributes.get(attribute, '')
            else:
                content = getattr(data, field, None)

            if isinstance(editor, QPlainTextEdit):
                value_new = content or ""
                value_old = editor.toPlainText()
                if value_old != value_new:
                    cursor = editor.textCursor()
                    position = cursor.position()

                    editor.blockSignals(True)
                    editor.setPlainText(value_new)
                    editor.blockSignals(False)

                    if field == 'value':
                        last_key = self.key_press_filter.get_last_key(editor)
                        if last_key not in (Qt.Key.Key_Backspace, Qt.Key.Key_Space):
                            position = min(position + 1, len(value_new))
                        else:
                            position = min(position, len(value_new))

                        cursor.setPosition(position)
                        editor.setTextCursor(cursor)

            elif isinstance(editor, QCheckBox):
                new_checked = bool(content)
                editor.blockSignals(True)
                editor.setChecked(new_checked)
                editor.blockSignals(False)

    def _open_start_window(self):
        """Open the start window and close the current editor."""
        from src.app import FluentusStart

        self.window_editor = FluentusStart()
        self.window_editor.show()

        self.close()

    def update_cache(self, editor: Union[QPlainTextEdit, QCheckBox], field: str, lang: QComboBox):
        """Update the cache when an editor field is modified."""

        variable, attribute = self.table_manager.get_variable()
        if not variable:
            return

        new_content = editor.toPlainText() if isinstance(editor, QPlainTextEdit) else editor.isChecked()

        if self.fluent_api.update(variable, lang.currentText(), field, new_content, attribute):
            self.set_current_item()

        self.load_variable()

        # Update title
        self.refresh_editing_state()

    def refresh_editing_state(self, edit_status: Optional[bool] = None) -> None:
        """Refreshes the editing status in 'fluent_api' and updates the window title."""
        
        if edit_status is not None:
            self.fluent_api.edited = edit_status

        folder_suffix = f" - {self.fluent_api.folder_path}" if self.fluent_api.folder_path else ""
        program = get_config(Program, 'program')

        if self.fluent_api.edited:
            window_title = f"*{program.title}{folder_suffix}"
        else:
            window_title = f"{program.title}{folder_suffix}"

        self.setWindowTitle(window_title)

    def closeEvent(self, event):
        """Handle the close event with unsaved changes."""
        if self.fluent_api.edited:
            dialog = CloseDialog(self)
            result = dialog.exec()

            if dialog.choice == "save":
                self.fluent_api.save_all_files()
                event.accept()
            elif dialog.choice == "save_in_custom_folder":
                folder = QFileDialog.getExistingDirectory(self, "Select locales folder")
                if folder:
                    self.fluent_api.save_all_files(folder)
                event.accept()
            elif dialog.choice == "discard":
                self._open_start_window()
                event.accept()
            else:
                event.ignore()
        else:
            self._open_start_window()
            event.accept()
