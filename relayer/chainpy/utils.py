def ensure_path_endswith_slash_char(target_path: str) -> str:
    return target_path if target_path.endswith("/") else target_path + "/"


def ensure_path_not_endswith_slash_char(target_path: str) -> str:
    return target_path[-1:] if target_path.endswith("/") else target_path


def add_file_name_to_path(target_path: str, file_name: str) -> str:
    target_path = ensure_path_endswith_slash_char(target_path)
    return target_path + file_name
