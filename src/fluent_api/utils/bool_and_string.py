def bool_to_string(value: bool):
    return str(value).lower()


def string_bool(value: str):
    return value.lower() in ("true", "t", "yes", "y", "1")