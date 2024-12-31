from PyQt6.QtWidgets import QPushButton, QLabel, QHBoxLayout, QVBoxLayout, QDialog


class CloseDialog(QDialog):
    """
    A dialog for confirming whether to save changes, save them to a different folder,
    discard them, or cancel the close operation.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Close Confirmation")
        self.setModal(True)

        label = QLabel("You have unsaved changes. Would you like to save them?")

        save_button = QPushButton("Save")
        save_custom_button = QPushButton("Save to a different location")
        no_button = QPushButton("No")
        cancel_button = QPushButton("Cancel")

        save_button.clicked.connect(self.save)
        save_custom_button.clicked.connect(self.save_in_custom_folder)
        no_button.clicked.connect(self.discard)
        cancel_button.clicked.connect(self.cancel)

        # Arrange buttons in a horizontal layout
        button_layout = QHBoxLayout()
        button_layout.addWidget(save_button)
        button_layout.addWidget(save_custom_button)
        button_layout.addWidget(no_button)
        button_layout.addWidget(cancel_button)

        # Main layout with a label and buttons
        main_layout = QVBoxLayout()
        main_layout.addWidget(label)
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

        self.choice = None

    def save(self) -> None:
        self.choice = "save"
        self.accept()

    def save_in_custom_folder(self) -> None:
        self.choice = "save_in_custom_folder"
        self.accept()

    def discard(self) -> None:
        self.choice = "discard"
        self.accept()

    def cancel(self) -> None:
        self.choice = "cancel"
        self.reject()
