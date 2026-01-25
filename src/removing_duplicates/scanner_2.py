# Scanner‑2: сравнивает очищаемую директорию с эталонной по кэшу Scanner‑1.
# Экономит ресурсы: сначала фильтрует по размеру, хеш считает только при совпадении размера.
# Перемещение уникальных файлов выполняет батчем (создаёт папку один раз).
# Удаление пустых папок вынесено в отдельный метод и вызывается только из GUI по команде.

from pathlib import Path
import json
import shutil
from typing import Callable, Optional
from src.removing_duplicates.utils import file_hash


class Scanner2:
    """
    Потокобезопасная логика не требуется — предполагается вызов из рабочего потока GUI.
    Публичные атрибуты:
      - duplicates: список путей дубликатов (в очищаемой директории)
      - unique_files: список путей уникальных файлов (в очищаемой директории)
    """

    def __init__(
        self,
        reference_dir: Path,
        target_dir: Path,
        *,
        delete_duplicates: bool = False,
        collect_only: bool = True,  # страховка, если включен - пофик
        # как настроены delete_duplicates и move_uniques
        move_uniques: bool = False,
        uniques_subdir_name: str = "non_duplicates",
    ):
        """
        :param reference_dir: эталонная директория (где лежит кэш Scanner1)
        :param target_dir: очищаемая директория
        :param delete_duplicates: удалять ли найденные дубликаты сразу
        :param collect_only: если True — только собирать списки, без действий (удалений/перемещений)
        :param move_uniques: переносить ли уникальные файлы в reference_dir/uniques_subdir_name
        :param uniques_subdir_name: имя подпапки для уникальных файлов внутри эталонной директории
        """
        self.reference_dir = Path(reference_dir)
        self.target_dir = Path(target_dir)
        self.delete_duplicates = bool(delete_duplicates)
        self.collect_only = bool(collect_only)
        self.move_uniques = bool(move_uniques)
        self.uniques_subdir_name = uniques_subdir_name

        # Результаты работы
        self.duplicates: list[str] = []
        self.unique_files: list[str] = []

        # Данные из кэша Scanner‑1
        # size_map: {size: set(hashes)}
        # hash_map: {hash: set(paths)}
        self.size_map: dict[int, set[str]] = {}
        self.hash_map: dict[str, set[str]] = {}

        # Папка назначения для уникальных файлов (создаём один раз при необходимости)
        self._uniques_dest_dir: Optional[Path] = None

    # ---------------------------
    # Вспомогательные проверки
    # ---------------------------

    def check_dirs(self) -> None:
        """Проверяет, что директории существуют и не вложены друг в друга."""
        if not self.reference_dir.exists() or not self.reference_dir.is_dir():
            raise ValueError(
                "Эталонная директория не существует или не является директорией."
            )
        if not self.target_dir.exists() or not self.target_dir.is_dir():
            raise ValueError(
                "Очищаемая директория не существует или не является директорией."
            )

        # Вложенность: одна не должна быть предком другой
        if (
            self.reference_dir in self.target_dir.parents
            or self.target_dir in self.reference_dir.parents
        ):
            raise ValueError(
                "Эталонная и очищаемая директории не должны быть вложенными."
            )

    def load_cache(self) -> None:
        """Загружает кэш Scanner‑1 из reference_dir/scanner1_cache.json."""
        cache_file = self.reference_dir / "scanner1_cache.json"
        if not cache_file.exists():
            raise FileNotFoundError("Кэш Scanner‑1 не найден в эталонной директории.")

        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Восстанавливаем структуры
        self.size_map = {int(k): set(v) for k, v in data.get("size_map", {}).items()}
        self.hash_map = {h: set(paths) for h, paths in data.get("hash_map", {}).items()}

    # ---------------------------
    # Основная логика сканирования
    # ---------------------------

    def scan_target(
        self,
        *,
        stop_flag=None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> None:
        """
        Сканирует очищаемую директорию:
        - сначала фильтрует по размеру (экономия: хеш считаем только при совпадении размера);
        - если хеш найден в hash_map — это дубликат;
            - либо удаляем (если delete_duplicates и не collect_only),
            - либо добавляем в список duplicates;
        - если хеш не найден — это уникальный файл;
            - либо переносим (если move_uniques и не collect_only),
            - либо добавляем в список unique_files.

        :param stop_flag: threading.Event или совместимый объект с методом is_set()
        :param progress_callback: функция (processed, total) для обновления прогресса
        """
        # Подготовка списка файлов
        all_paths = [p for p in self.target_dir.rglob("*") if p.is_file()]
        total = len(all_paths)
        processed = 0

        # Создаём папку для уникальных файлов один раз, если понадобится
        if self.move_uniques and not self.collect_only:
            self._uniques_dest_dir = self.reference_dir / self.uniques_subdir_name
            self._uniques_dest_dir.mkdir(exist_ok=True)

        for f in all_paths:
            if stop_flag is not None and getattr(stop_flag, "is_set", lambda: False)():
                break

            size = f.stat().st_size

            # Экономия: считаем хеш только если размер есть в эталонном кэше
            hashes_for_size = self.size_map.get(size)
            if hashes_for_size:
                # Размер совпал — считаем хеш и проверяем наличие в hash_map
                h = file_hash(f)
                if h in self.hash_map:
                    # Дубликат
                    self.duplicates.append(str(f))
                    if self.delete_duplicates and not self.collect_only:
                        try:
                            f.unlink()
                        except Exception as e:
                            # В реальном приложении — логировать
                            pass
                else:
                    # Уникальный (по содержимому)
                    self._handle_unique(f)
            else:
                # Размер не встречается в эталонной папке — точно уникальный
                self._handle_unique(f)

            processed += 1
            if progress_callback:
                progress_callback(processed, total)

    # ---------------------------
    # Действия над уникальными файлами
    # ---------------------------

    def _handle_unique(self, f: Path) -> None:
        """Обрабатывает уникальный файл: переносит или добавляет в список."""
        self.unique_files.append(str(f))
        if self.move_uniques and not self.collect_only and self._uniques_dest_dir:
            dest = self._safe_destination(self._uniques_dest_dir, f.name)
            try:
                shutil.move(str(f), str(dest))
            except Exception:
                # В реальном приложении — логировать
                pass

    @staticmethod
    def _safe_destination(dest_dir: Path, filename: str) -> Path:
        """
        Возвращает безопасный путь назначения:
        - если файл уже существует, добавляет суффикс (1), (2), ...
        """
        base = dest_dir / filename
        if not base.exists():
            return base

        stem = base.stem
        suffix = base.suffix
        i = 1
        while True:
            candidate = dest_dir / f"{stem} ({i}){suffix}"
            if not candidate.exists():
                return candidate
            i += 1

    # ---------------------------
    # Удаление пустых папок (по команде из GUI)
    # ---------------------------

    def delete_empty_dirs(self) -> int:
        """
        Удаляет пустые директории внутри target_dir.
        Возвращает количество удалённых папок.
        Вызывать ТОЛЬКО по явной команде из GUI.
        """
        removed = 0
        # Идём снизу вверх, чтобы корректно удалять вложенные пустые папки
        for d in sorted(self.target_dir.rglob("*"), reverse=True):
            if d.is_dir():
                try:
                    # Если нет ни одного элемента — папка пустая
                    if not any(d.iterdir()):
                        d.rmdir()
                        removed += 1
                except Exception:
                    # В реальном приложении — логировать
                    pass
        return removed
