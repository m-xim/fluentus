from typing import Optional

from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QGraphicsOpacityEffect


class DragOverlay(QWidget):
    """
    Overlay widget with elegant fade in/out animation and a semi-transparent background.

    When visible, the overlay dims the parent widget with a semi-transparent area and
    displays a centered instruction.
    """

    ANIMATION_DURATION = 300  # Animation duration in milliseconds

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        # Set a semi-transparent background color for the overlay.
        # Here, rgba(0, 0, 0, 120) produces a semi-transparent black color.
        self.setStyleSheet("background-color: rgba(0, 0, 0, 120);")

        # Allow mouse events to pass through to underlying widgets.
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setVisible(False)

        # Main layout with no margins so the overlay covers the entire widget.
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        # Create a centered label with instructions.
        self.label = QLabel("Drag your project folder here", self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet(
            "color: white;"
            "font-size: 20px;"
            "font-weight: bold;"
        )
        layout.addWidget(self.label)

        # Apply an opacity effect to the overlay for fade animations.
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)

        # Animation for the opacity effect.
        self.opacity_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.opacity_animation.setDuration(self.ANIMATION_DURATION)
        self.opacity_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

    def update_overlay_geometry(self) -> None:
        """Update the overlay's geometry to cover the entire parent widget."""
        parent = self.parentWidget()
        if parent is not None:
            self.setGeometry(0, 0, parent.width(), parent.height())

    def fade_in(self) -> None:
        """Smoothly fade in the overlay."""
        self.opacity_animation.stop()
        self.setVisible(True)
        self.opacity_animation.setStartValue(0.0)
        self.opacity_animation.setEndValue(1.0)
        self.opacity_animation.start()

    def fade_out(self) -> None:
        """Smoothly fade out the overlay."""
        self.opacity_animation.stop()
        self.opacity_animation.setStartValue(self.opacity_effect.opacity())
        self.opacity_animation.setEndValue(0.0)
        self.opacity_animation.finished.connect(self._on_fade_out_finished)
        self.opacity_animation.start()

    def _on_fade_out_finished(self) -> None:
        """Hide the overlay after fade-out animation finishes."""
        self.setVisible(False)
        try:
            self.opacity_animation.finished.disconnect(self._on_fade_out_finished)
        except Exception:
            pass
