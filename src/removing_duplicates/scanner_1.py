# Реализация Scanner‑1 с кэшированием и графическим интерфейсом.
# Использует JSON для хранения данных, работает в отдельном потоке,
# чтобы GUI оставался отзывчивым.

import os
import json
import hashlib
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from src.removing_duplicates.utils import file_hash

CACHE_FILE = "scanner1_cache.json"


class Scanner1:
    """
    Класс Scanner‑1:
    - хранит таблицы:
        files_info: {путь: (размер, хеш)}
        size_map: {размер: {хеши}}
        hash_map: {хеш: {пути}}
        unreadable_files: [пути файлов, которые не удалось прочитать]
    - умеет загружать/сохранять данные в JSON
    - сканирует директорию, пропуская уже обработанные файлы
    """

    def __init__(self):
        self.files_info = {}
        self.size_map = {}
        self.hash_map = {}
        self.unreadable_files = []  # список проблемных файлов

    def get_cache_path(self, dir_path: Path) -> Path:
        """Возвращает путь к файлу кэша внутри эталонной директории."""
        return dir_path / CACHE_FILE

    def load_cache(self, dir_path: Path):
        """Загружает кэш из JSON, если он существует."""
        cache_file = self.get_cache_path(dir_path)
        if cache_file.exists():
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.files_info = {
                k: tuple(v) for k, v in data.get("files_info", {}).items()
            }
            self.size_map = {
                int(k): set(v) for k, v in data.get("size_map", {}).items()
            }
            self.hash_map = {k: set(v) for k, v in data.get("hash_map", {}).items()}
            self.unreadable_files = data.get("unreadable_files", [])

    def save_cache(self, dir_path: Path):
        """Сохраняет кэш в JSON, включая список непрочитанных файлов."""
        cache_file = self.get_cache_path(dir_path)
        data = {
            "files_info": {k: list(v) for k, v in self.files_info.items()},
            "size_map": {str(k): list(v) for k, v in self.size_map.items()},
            "hash_map": {k: list(v) for k, v in self.hash_map.items()},
            "unreadable_files": self.unreadable_files,
        }
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def scan_directory(
        self, dir_path: Path, stop_flag: threading.Event, progress_callback=None
    ):
        """
        Рекурсивно сканирует директорию:
        - пропускает файлы, которые уже есть в кэше (имя+размер совпадают);
        - для новых файлов считает хеш и добавляет в таблицы;
        - если хеш не удалось получить (None) — добавляет путь в unreadable_files;
        - проверяет stop_flag, чтобы можно было прервать процесс.
        """

        self.load_cache(dir_path)
        all_files = list(dir_path.rglob("*"))
        total = len([f for f in all_files if f.is_file()])
        processed = 0

        for f in all_files:
            if stop_flag.is_set():
                break
            if f.is_file():
                key = str(f)
                try:
                    size = f.stat().st_size
                    if key in self.files_info and self.files_info[key][0] == size:
                        pass
                    else:
                        h = file_hash(
                            f
                        )  # если не удастся прочитать, выбросит исключение
                        self.files_info[key] = (size, h)
                        self.size_map.setdefault(size, set()).add(h)
                        self.hash_map.setdefault(h, set()).add(key)
                except (PermissionError, FileNotFoundError, OSError):
                    self.unreadable_files.append(key)

                processed += 1
                if progress_callback:
                    progress_callback(processed, total)

        self.save_cache(dir_path)
