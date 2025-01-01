import sys

from PyQt6 import uic
from PyQt6.QtCore import Qt, QModelIndex
from PyQt6.QtSql import QSqlTableModel
from PyQt6.QtWidgets import QApplication, QMessageBox, QFileDialog, QMainWindow, QPushButton, QTableView
from loguru import logger

from src.database.manager import DatabaseManager
from src.editor import FluentusEditor
from src.logger import configure_logger
from src.utils.config_reader import get_config, DatabaseConfig
from src.utils.resource_path import resource_path


class FluentusStart(QMainWindow):
    """
    The main application window for the Fluent Localization Editor.
    """

    def __init__(self) -> None:
        super().__init__()

        # Initialize database config
        db_config: DatabaseConfig = get_config(model=DatabaseConfig, root_key='database')

        # Create database manager
        self.db_manager = DatabaseManager(db_name=db_config.name, table_name=db_config.tables.projects)

        # Load UI
        uic.loadUi(resource_path("resource/ui/start_window.ui"), self)

        # Find the required widgets
        self.projects: QTableView = self.findChild(QTableView, "projects")
        self.new_project: QPushButton = self.findChild(QPushButton, "new_project")

        # Initialize the database (create table if it doesn't exist)
        if not self.db_manager.initialize_database():
            sys.exit(1)

        # Connect to the database
        if not self.db_manager.create_connection():
            sys.exit(1)

        # Set up the model and link it to the table view
        self.model = QSqlTableModel(self)
        self.model.setTable(db_config.tables.projects)
        self.model.setEditStrategy(QSqlTableModel.EditStrategy.OnFieldChange)
        self.model.select()
        self.model.setHeaderData(self.model.fieldIndex("folder"), Qt.Orientation.Horizontal, "Folder")

        self.projects.setModel(self.model)
        self.projects.resizeColumnsToContents()
        self.projects.setSortingEnabled(True)
        self.projects.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.projects.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.projects.doubleClicked.connect(self.open_editor)

        # Connect the button for creating a new project
        self.new_project.clicked.connect(self.new_project_set)

    def open_editor(self, index: QModelIndex) -> None:
        """
        Opens the FluentusEditor for the selected project (double-click on a row in the table).

        :param index: The index of the selected row.
        """
        folder = index.data()
        if folder:
            editor = FluentusEditor(folder=folder)
            editor.show()
            self.close()

    def new_project_set(self) -> None:
        """
        Creates a new project by asking the user to select a folder and adds a record to the 'projects' table.
        """
        folder = QFileDialog.getExistingDirectory(self, "Select locales folder")
        logger.info(f"Selected folder: {folder}")
        if not folder:
            return  # The user canceled the folder selection

        # Check if the project already exists
        if self.db_manager.project_exists(folder):
            QMessageBox.warning(self, "Warning", "A project with this path already exists.")
            return

        # Add the project to the database
        if not self.db_manager.add_project(folder):
            QMessageBox.critical(self, "Error", "Failed to add the project to the database.")
            return

        # Refresh the model to display the new record
        self.model.select()


if __name__ == "__main__":
    configure_logger()
    app = QApplication(sys.argv)
    start = FluentusStart()
    start.show()
    sys.exit(app.exec())
