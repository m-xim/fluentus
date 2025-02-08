import os
import sys

from PyQt6 import uic
from PyQt6.QtCore import Qt, QModelIndex, QEvent
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QResizeEvent, QShortcut
from PyQt6.QtSql import QSqlTableModel
from PyQt6.QtWidgets import (
    QApplication,
    QMessageBox,
    QFileDialog,
    QMainWindow,
    QPushButton,
    QTableView,
)
from loguru import logger

from src.database.manager import DatabaseManager
from src.editor import FluentusEditor
from src.logger import configure_logger
from src.utils.config_reader import get_config, DatabaseConfig
from src.utils.icon_utils import get_tinted_icon
from src.utils.resource_path import resource_path
from src.widgets.drag_overlay import DragOverlay


class FluentusStart(QMainWindow):
    """
    The main application window for the Fluent Localization Editor.
    """

    def __init__(self) -> None:
        super().__init__()

        # Initialize database config
        db_config: DatabaseConfig = get_config(
            model=DatabaseConfig, root_key="database"
        )

        # Create database manager
        self.db_manager = DatabaseManager(
            db_name=db_config.name, table_name=db_config.tables.projects
        )

        # Load UI
        uic.loadUi(resource_path("resource/ui/start_window.ui"), self)

        # Set theme
        self.new_project: QPushButton
        self.new_project.setIcon(
            get_tinted_icon("resource/icons/new_folder.png", self.new_project)
        )

        # Retrieve required widgets
        self.projects: QTableView = self.findChild(QTableView, "projects")
        self.new_project: QPushButton = self.findChild(QPushButton, "new_project")

        # Create drag overlay
        self.overlay = DragOverlay(self)

        # Initialize database (create table if it doesn't exist)
        if not self.db_manager.initialize_database():
            logger.error("Database initialization failed.")
            QMessageBox.critical(
                self, "Database Error", "Failed to initialize database."
            )
            sys.exit(1)

        # Connect to the database
        if not self.db_manager.create_connection():
            logger.error("Database connection failed.")
            QMessageBox.critical(
                self, "Database Error", "Failed to connect to database."
            )
            sys.exit(1)

        # Set up the model and link it to the table view
        self.model = QSqlTableModel(self)
        self.model.setTable(db_config.tables.projects)
        self.model.setEditStrategy(QSqlTableModel.EditStrategy.OnFieldChange)
        self.model.select()
        self.model.setHeaderData(
            self.model.fieldIndex("folder"), Qt.Orientation.Horizontal, "Folder"
        )

        # Configure the projects table view
        self.projects.setModel(self.model)
        self.projects.resizeColumnsToContents()
        self.projects.setSortingEnabled(True)
        self.projects.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.projects.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.projects.doubleClicked.connect(self.open_editor)

        shortcut_delete = QShortcut(Qt.Key.Key_Delete, self.projects)
        shortcut_delete.activated.connect(
            lambda: self.delete_rows(self.model, self.projects)
        )

        # Connect the "New Project" button click event
        self.new_project.clicked.connect(self.create_new_project)

    def open_editor(self, index: QModelIndex) -> None:
        """
        Opens the FluentusEditor for the selected project (double-click on a row).

        :param index: The index of the selected row.
        """
        folder = index.data()
        if folder:
            editor = FluentusEditor(folder=folder)
            editor.show()
            self.close()

    def create_new_project(self) -> None:
        """
        Creates a new project by asking the user to select a folder.
        """
        folder = QFileDialog.getExistingDirectory(self, "Select locales folder")
        logger.info(f"Selected folder: {folder}")

        if not folder:
            return  # User canceled folder selection

        self.add_project(folder)

    def add_project(self, folder: str) -> None:
        """
        Adds a project to the database if it doesn't already exist.
        Displays appropriate messages on failure or if the project exists.

        :param folder: Path to the project folder.
        """
        if self.db_manager.project_exists(folder):
            QMessageBox.warning(
                self, "Warning", "A project with this path already exists."
            )
            return

        if not self.db_manager.add_project(folder):
            QMessageBox.critical(
                self, "Error", "Failed to add the project to the database."
            )
            return

        # Refresh the model to display the new record
        self.model.select()

    @staticmethod
    def delete_rows(model: QSqlTableModel, table_view: QTableView) -> None:
        selected_indexes = table_view.selectionModel().selectedRows()
        if not selected_indexes:
            return

        # Remove each row from the model
        for index in selected_indexes:
            model.removeRow(index.row())

        if not model.submitAll():
            QMessageBox.critical(
                table_view,
                "Deletion Error",
                f"Unable to delete rows:" f"\n{model.lastError().text()}",
            )
        else:
            model.select()

    def resizeEvent(self, event: QResizeEvent) -> None:
        """
        Adjusts overlay geometry when the window is resized.

        :param event: QResizeEvent instance.
        """
        self.overlay.update_overlay_geometry()
        super().resizeEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """
        Accepts the drag event if it contains a folder URL and shows the overlay.

        :param event: QDragEnterEvent instance.
        """
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                folder = url.toLocalFile()
                if os.path.isdir(folder):
                    event.acceptProposedAction()
                    self.overlay.fade_in()
                    return
        event.ignore()

    def dragLeaveEvent(self, event: QEvent) -> None:
        """
        Hides the overlay when the drag leaves the window.

        :param event: QEvent instance.
        """
        self.overlay.fade_out()
        event.accept()

    def dropEvent(self, event: QDropEvent) -> None:
        """
        Handles the drop event by adding the dropped folder as a new project.

        :param event: QDropEvent instance.
        """
        self.overlay.fade_out()
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                folder = url.toLocalFile()
                if os.path.isdir(folder):
                    self.add_project(folder)
                    event.acceptProposedAction()
                    return
        event.ignore()


if __name__ == "__main__":
    configure_logger()
    app = QApplication(sys.argv)
    start = FluentusStart()
    start.show()
    sys.exit(app.exec())
