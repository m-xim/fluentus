import os
import sys


def resource_path(relative_path: str) -> str:
    """
    Returns the absolute path to the given resource. This function works both
    in a development environment and in a compiled application (e.g., PyInstaller).

    :param relative_path: The relative path of the resource.
    :return: The absolute path to the resource.
    """
    try:
        base_path = sys._MEIPASS  # Used by PyInstaller
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)
