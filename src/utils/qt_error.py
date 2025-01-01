import sys

from PyQt6.QtWidgets import QMessageBox


def show_error(message):
    error_dialog = QMessageBox()
    error_dialog.setIcon(QMessageBox.Icon.Critical)
    error_dialog.setWindowTitle("Error")
    error_dialog.setText(message)
    error_dialog.exec()


def excepthook(exctype, value, traceback):
    show_error(f"{exctype.__name__}: {value}")
    sys.__excepthook__(exctype, value, traceback)
