from pathlib import Path


def check_path_exists(file_path: str | Path) -> bool:
    return Path(file_path).exists()


def check_path_is_file(file_path: str | Path) -> bool:
    return Path(file_path).is_file()
