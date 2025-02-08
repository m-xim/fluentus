import logging

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QPainter, QColor, QIcon, QPalette

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def tint_pixmap(pixmap: QPixmap, tint_color: QColor) -> QPixmap:
    """
    Tints the given QPixmap with the provided tint_color.
    Uses CompositionMode_SourceIn to apply the tint only to non-transparent areas.

    Parameters:
        pixmap (QPixmap): The source image.
        tint_color (QColor): The color used for tinting.

    Returns:
        QPixmap: The tinted image.

    Raises:
        ValueError: If the provided pixmap is null.
    """
    if pixmap.isNull():
        raise ValueError("Provided QPixmap is null.")

    # Create a new pixmap of the same size with a transparent background.
    tinted = QPixmap(pixmap.size())
    tinted.fill(Qt.GlobalColor.transparent)

    painter = QPainter(tinted)
    try:
        painter.drawPixmap(0, 0, pixmap)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(tinted.rect(), tint_color)
    except Exception as e:
        logger.exception("Error tinting pixmap: %s", e)
        raise
    finally:
        painter.end()

    return tinted


def get_color_from_object(source, role=QPalette.ColorRole.WindowText) -> QColor:
    """
    Extracts and returns a QColor from the provided source object.

    If the source has a palette (e.g. a QWidget), it retrieves the color for the given role.
    If the source has a 'color' attribute or method returning a QColor, that is used.

    Parameters:
        source: The object from which to extract the color.
        role: The palette color role to use (default is WindowText).

    Returns:
        QColor: The extracted color.

    Raises:
        ValueError: If a color cannot be extracted.
    """
    try:
        if hasattr(source, "palette"):
            color = source.palette().color(role)
            if isinstance(color, QColor):
                return color

        if hasattr(source, "color"):
            color = source.color() if callable(source.color) else source.color
            if isinstance(color, QColor):
                return color

        raise ValueError(f"Cannot extract color from: {source}")
    except Exception as e:
        logger.exception("Error extracting color: %s", e)
        raise


def get_tinted_icon(
    icon_path: str, widget, role=QPalette.ColorRole.WindowText
) -> QIcon:
    """
    Loads an icon from the specified path, tints it using a color extracted from the provided widget,
    and returns a QIcon.

    Parameters:
        icon_path (str): The path to the icon image.
        widget: The widget (or any object) from which to extract the tint color.
        role: The palette color role to extract (default is WindowText).

    Returns:
        QIcon: The tinted icon.

    Raises:
        ValueError: If the icon cannot be loaded.
    """
    pixmap = QPixmap(icon_path)
    if pixmap.isNull():
        raise ValueError(f"Cannot load icon from {icon_path}")

    tint_color = get_color_from_object(widget, role)
    tinted_pixmap = tint_pixmap(pixmap, tint_color)
    return QIcon(tinted_pixmap)
