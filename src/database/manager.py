from PyQt6.QtSql import QSqlDatabase, QSqlQuery
from PyQt6.QtWidgets import QMessageBox
from loguru import logger


class DatabaseManager:
    """
    A class to manage the SQLite database using QSqlDatabase.
    """

    def __init__(self, db_name: str, table_name: str) -> None:
        """
        :param db_name: The name of the database (without the .db extension).
        :param table_name: The name of the projects table.
        """
        self.db_name = db_name
        self.table_name = table_name

    def initialize_database(self) -> bool:
        """
        Creates the table if it does not already exist.
        Returns False if an error occurs.

        :return: Whether the table creation was successful.
        """
        db = QSqlDatabase.addDatabase("QSQLITE", "init_connection")
        db.setDatabaseName(f"{self.db_name}.db")
        if not db.open():
            error = db.lastError().text()
            logger.error(f"Failed to open the database for initialization: {error}")
            return False

        query = QSqlQuery(db)
        sql_create = f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                folder TEXT PRIMARY KEY
            )
        """
        if not query.exec(sql_create):
            error = query.lastError().text()
            logger.error(f"Error creating the table: {error}")
            db.close()
            return False

        db.close()
        logger.info("The database has been successfully initialized.")
        return True

    def create_connection(self) -> bool:
        """
        Establishes a connection to the database, to be used by QSql* classes throughout the application.
        Returns True on success.

        :return: Whether the connection was successfully established.
        """
        db = QSqlDatabase.addDatabase("QSQLITE")
        db.setDatabaseName(f"{self.db_name}.db")
        if not db.open():
            error = db.lastError().text()
            logger.error(f"Failed to connect to the database: {error}")
            QMessageBox.critical(None, "Database Error", f"Failed to connect to the database: {error}")
            return False

        logger.info("Database connection established.")
        return True

    def project_exists(self, folder: str) -> bool:
        """
        Checks whether a project with the given folder path exists in the database.

        :param folder: The folder path of the project.
        :return: True if the project exists, otherwise False.
        """
        query = QSqlQuery()
        query.prepare(f"SELECT COUNT(*) FROM {self.table_name} WHERE folder = :folder")
        query.bindValue(":folder", folder)
        if not query.exec():
            logger.error(f"Failed to check project existence: {query.lastError().text()}")
            return False

        if query.next():
            return query.value(0) > 0
        return False

    def add_project(self, folder: str) -> bool:
        """
        Inserts a new project record into the database.

        :param folder: The folder path of the project.
        :return: True if the project is added successfully, otherwise False.
        """
        query = QSqlQuery()
        query.prepare(f"INSERT INTO {self.table_name} (folder) VALUES (:folder)")
        query.bindValue(":folder", folder)
        if not query.exec():
            logger.error(f"Error adding project: {query.lastError().text()}")
            return False

        logger.info(f"Project '{folder}' has been added successfully.")
        return True
