# Графическая оболочка для поиска дубликатов между двумя директориями.
# Использует функцию find_duplicates_between(dir1, dir2) из модуля scanner.
# Скрипт можно запускать напрямую: python gui.py

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

# --- Импорт функции поиска дубликатов ---
# scanner.py находится в пакете src/removing_duplicated/scanner.py
try:
    from src.removing_duplicated.scanner import (
        find_duplicates_between,
    )  # модуль сканирования
except ImportError:
    # Если оба импорта не удались — показываем понятное сообщение и завершаем работу.
    # В реальном приложении можно предложить пользователю выбрать путь к модулю.
    raise ImportError(
        "Не удалось импортировать find_duplicates_between.\n"
        "Убедитесь, что scanner.py лежит  в src/removing_duplicated/scanner.py."
    )


def validate_dir(path_str: str) -> Path:
    """
    Проверяет, что строка непустая и указывает на существующую директорию.
    Возвращает Path, если всё ок; иначе выбрасывает ValueError с понятным текстом.
    """
    if not path_str:
        raise ValueError("Путь к директории не указан.")
    p = Path(path_str)
    if not p.exists():
        raise ValueError(f"Директория не существует: {p}")
    if not p.is_dir():
        raise ValueError(f"Это не директория: {p}")
    return p


class DuplicateFinderGUI:
    """
    Класс-обёртка над интерфейсом:
    - создаёт элементы управления;
    - обрабатывает выбор директорий;
    - запускает поиск и показывает результаты.
    """

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Поиск дубликатов между директориями")

        # Фиксируем минимальный размер окна, чтобы элементы не сжимались слишком сильно
        self.root.minsize(640, 420)

        # Основной контейнер с отступами
        container = ttk.Frame(self.root, padding=12)
        container.pack(fill="both", expand=True)

        # --- Поля ввода для первой директории ---
        self.dir1_var = tk.StringVar()
        dir1_row = ttk.Frame(container)
        dir1_row.pack(fill="x", pady=(0, 8))

        ttk.Label(dir1_row, text="Первая директория:").pack(side="left")
        self.dir1_entry = ttk.Entry(dir1_row, textvariable=self.dir1_var)
        self.dir1_entry.pack(side="left", fill="x", expand=True, padx=8)

        dir1_btn = ttk.Button(dir1_row, text="Выбрать…", command=self.choose_dir1)
        dir1_btn.pack(side="left")

        # --- Поля ввода для второй директории ---
        self.dir2_var = tk.StringVar()
        dir2_row = ttk.Frame(container)
        dir2_row.pack(fill="x", pady=(0, 12))

        ttk.Label(dir2_row, text="Вторая директория:").pack(side="left")
        self.dir2_entry = ttk.Entry(dir2_row, textvariable=self.dir2_var)
        self.dir2_entry.pack(side="left", fill="x", expand=True, padx=8)

        dir2_btn = ttk.Button(dir2_row, text="Выбрать…", command=self.choose_dir2)
        dir2_btn.pack(side="left")

        # --- Кнопка запуска поиска ---
        actions_row = ttk.Frame(container)
        actions_row.pack(fill="x", pady=(0, 8))

        self.search_btn = ttk.Button(
            actions_row, text="Найти дубликаты", command=self.run_search
        )
        self.search_btn.pack(side="left")

        # --- Статусная строка для сообщений пользователю ---
        self.status_var = tk.StringVar(value="Готово.")
        status_label = ttk.Label(
            container, textvariable=self.status_var, foreground="#555"
        )
        status_label.pack(fill="x", pady=(0, 8))

        # --- Список результатов (Listbox) с прокруткой ---
        results_frame = ttk.LabelFrame(container, text="Дубликаты в первой директории")
        results_frame.pack(fill="both", expand=True)

        self.results_list = tk.Listbox(results_frame, height=12)
        self.results_list.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(
            results_frame, orient="vertical", command=self.results_list.yview
        )
        scrollbar.pack(side="right", fill="y")
        self.results_list.configure(yscrollcommand=scrollbar.set)

        # --- Нижняя панель с кнопками для работы с результатами ---
        bottom_row = ttk.Frame(container)
        bottom_row.pack(fill="x", pady=(8, 0))

        self.copy_paths_btn = ttk.Button(
            bottom_row, text="Скопировать пути", command=self.copy_results_to_clipboard
        )
        self.copy_paths_btn.pack(side="left")

        self.clear_btn = ttk.Button(
            bottom_row, text="Очистить", command=self.clear_results
        )
        self.clear_btn.pack(side="left", padx=(8, 0))

    def choose_dir1(self):
        """
        Открывает диалог выбора директории и записывает путь в поле dir1.
        """
        selected = filedialog.askdirectory(title="Выберите первую директорию")
        if selected:
            self.dir1_var.set(selected)

    def choose_dir2(self):
        """
        Открывает диалог выбора директории и записывает путь в поле dir2.
        """
        selected = filedialog.askdirectory(title="Выберите вторую директорию")
        if selected:
            self.dir2_var.set(selected)

    def run_search(self):
        """
        Валидирует пути, запускает поиск дубликатов и отображает результат.
        Важно: поиск выполняется синхронно — для больших директорий можно
        вынести в отдельный поток, чтобы не блокировать интерфейс.
        """
        # Очищаем предыдущие результаты и статус
        self.results_list.delete(0, tk.END)
        self.status_var.set("Выполняется поиск…")
        self.search_btn.configure(state="disabled")

        try:
            # Валидируем директории (покажем понятные ошибки, если что-то не так)
            dir1 = validate_dir(self.dir1_var.get())
            dir2 = validate_dir(self.dir2_var.get())

            # Запускаем основную функцию поиска
            duplicates = find_duplicates_between(dir1, dir2)

            # Если список пуст — сообщаем пользователю
            if not duplicates:
                self.status_var.set("Дубликатов не найдено.")
            else:
                self.status_var.set(f"Найдено дубликатов: {len(duplicates)}")
                # Заполняем Listbox строковыми путями
                for p in duplicates:
                    self.results_list.insert(tk.END, str(p))

        except ValueError as ve:
            # Ошибки валидации директорий показываем в диалоге
            messagebox.showerror("Ошибка ввода", str(ve))
            self.status_var.set("Исправьте пути к директориям и повторите.")
        except Exception as e:
            # Любые неожиданные ошибки — тоже показываем
            messagebox.showerror("Ошибка", f"Во время поиска произошла ошибка:\n{e}")
            self.status_var.set("Ошибка выполнения.")
        finally:
            # Возвращаем кнопку в активное состояние
            self.search_btn.configure(state="normal")

    def copy_results_to_clipboard(self):
        """
        Копирует все строки из списка результатов в буфер обмена (по одной строке на путь).
        """
        items = self.results_list.get(0, tk.END)
        if not items:
            messagebox.showinfo("Копирование", "Список результатов пуст.")
            return
        text = "\n".join(items)
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.status_var.set("Пути скопированы в буфер обмена.")

    def clear_results(self):
        """
        Очищает список результатов и сбрасывает статус.
        """
        self.results_list.delete(0, tk.END)
        self.status_var.set("Готово.")


def main():
    """
    Точка входа: создаём окно и запускаем главный цикл обработки событий.
    """
    root = tk.Tk()
    app = DuplicateFinderGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
