from pathlib import Path
import hashlib


def validate_dirs(dir1: Path, dir2: Path):
    """Проверяем, что директории не совпадают и не вложены друг в друга."""
    dir1 = dir1.resolve()
    dir2 = dir2.resolve()
    if dir1 == dir2:
        raise ValueError("Директории совпадают!")
    if dir1 in dir2.parents:
        raise ValueError("Директория 1 вложена в директорию 2!")
    if dir2 in dir1.parents:
        raise ValueError("Директория 2 вложена в директорию 1!")


def file_hash(path: Path, algo="sha256", chunk_size=8192):
    """Вычисляем хеш файла."""
    h = hashlib.new(algo)
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_directory(path: Path):
    """Возвращает список файлов с их размерами."""
    return [(p, p.stat().st_size) for p in path.rglob("*") if p.is_file()]


def find_duplicates_between(dir1: Path, dir2: Path):
    """
    Находит файлы из dir1, которые дублируются в dir2.
    Возвращает список путей-дубликатов из dir1.
    """
    validate_dirs(dir1, dir2)

    # Сканируем вторую директорию и строим таблицу {размер: [хеши]}
    table = {}
    for path, size in scan_directory(dir2):
        h = file_hash(path)
        table.setdefault(size, set()).add(h)

    # Проверяем файлы из первой директории
    duplicates = []
    for path, size in scan_directory(dir1):
        if size in table:
            h = file_hash(path)
            if h in table[size]:
                duplicates.append(path)

    return duplicates
