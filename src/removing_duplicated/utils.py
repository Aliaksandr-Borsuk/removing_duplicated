# utils.py
import hashlib
from pathlib import Path


def file_hash(path: Path, chunk_size=8192) -> str:
    """Вычисляет SHA‑256 хеш файла, читая его кусками."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


# utils.py
def find_internal_duplicates(hash_map: dict) -> dict:
    """
    Находит дубликаты внутри эталонной директории.
    Принимает словарь {хеш: set(пути файлов)}.
    Возвращает словарь {хеш: [список путей]} только для тех хешей,
    где файлов больше одного.
    """
    duplicates = {}
    for h, paths in hash_map.items():
        if len(paths) > 1:
            duplicates[h] = list(paths)
    return duplicates


def scan_directory(dir_path: Path):
    """Рекурсивно обходит директорию и возвращает список (path, size)."""
    files = []
    for f in dir_path.rglob("*"):
        if f.is_file():
            files.append((f, f.stat().st_size))
    return files
