from PyQt6.QtCore import QObject, QEvent


class KeyPressFilter(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.last_key = {}

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress:
            self.last_key[obj] = event.key()

        return super().eventFilter(obj, event)

    def get_last_key(self, obj):
        return self.last_key.get(obj, None)
