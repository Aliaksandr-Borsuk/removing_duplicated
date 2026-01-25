# scanner1_gui.py
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
    - хранит две таблицы:
        files_info: {имя файла: (размер, хеш)}
        size_map: {размер: {хеши}}
    - умеет загружать/сохранять данные в JSON
    - сканирует директорию, пропуская уже обработанные файлы
    """

    def __init__(self):
        self.files_info = {}
        self.size_map = {}
        self.hash_map = {}

    def get_cache_path(self, dir_path: Path) -> Path:
        """Возвращает путь к файлу кэша внутри эталонной директории."""
        return dir_path / "scanner1_cache.json"

    def load_cache(self, dir_path: Path):
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

    def save_cache(self, dir_path: Path):
        cache_file = self.get_cache_path(dir_path)
        data = {
            "files_info": {k: list(v) for k, v in self.files_info.items()},
            "size_map": {str(k): list(v) for k, v in self.size_map.items()},
            "hash_map": {k: list(v) for k, v in self.hash_map.items()},
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
        - проверяет stop_flag, чтобы можно было прервать процесс.
        """
        self.load_cache(dir_path)  # загружаем кэш именно из этой папки
        all_files = list(dir_path.rglob("*"))
        total = len([f for f in all_files if f.is_file()])
        processed = 0

        for f in all_files:
            if stop_flag.is_set():
                break
            if f.is_file():
                size = f.stat().st_size
                key = str(f)

                # Проверяем: если файл уже есть в кэше и размер совпадает — пропускаем
                if key in self.files_info and self.files_info[key][0] == size:
                    pass
                else:
                    h = file_hash(f)
                    self.files_info[key] = (size, h)
                    self.size_map.setdefault(size, set()).add(h)
                    self.hash_map.setdefault(h, set()).add(key)

                processed += 1
                if progress_callback:
                    progress_callback(processed, total)

        # После завершения или прерывания сохраняем кэш
        self.save_cache(dir_path)
