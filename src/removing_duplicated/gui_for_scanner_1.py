import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import threading
from scanner_1 import Scanner1
from utils import find_internal_duplicates


class Scanner1GUI:
    """
    Графический интерфейс для Scanner‑1:
    - поле выбора директории;
    - кнопка запуска сканирования;
    - прогресс‑бар;
    - кнопка «Прервать».
    """

    def __init__(self, root):
        self.root = root
        self.root.title("Scanner‑1 (Эталонная папка)")
        self.root.minsize(600, 300)

        container = ttk.Frame(root, padding=12)
        container.pack(fill="both", expand=True)

        # Поле выбора директории
        self.dir_var = tk.StringVar()
        dir_row = ttk.Frame(container)
        dir_row.pack(fill="x", pady=(0, 8))
        ttk.Label(dir_row, text="Эталонная директория:").pack(side="left")
        ttk.Entry(dir_row, textvariable=self.dir_var).pack(
            side="left", fill="x", expand=True, padx=8
        )
        ttk.Button(dir_row, text="Выбрать…", command=self.choose_dir).pack(side="left")

        # Кнопки управления
        actions_row = ttk.Frame(container)
        actions_row.pack(fill="x", pady=(0, 8))
        self.start_btn = ttk.Button(
            actions_row, text="Сканировать", command=self.run_scan
        )
        self.start_btn.pack(side="left")
        self.stop_btn = ttk.Button(actions_row, text="Прервать", command=self.stop_scan)
        self.stop_btn.pack(side="left", padx=8)
        # кнопка для показа дубликатов изначально выключена
        self.show_dupes_btn = ttk.Button(
            actions_row, text="Показать дубликаты", command=self.show_duplicates
        )
        self.show_dupes_btn.pack(side="left", padx=8)
        self.show_dupes_btn.configure(state="disabled")  # изначально выключена

        # Прогресс‑бар
        self.progress = ttk.Progressbar(
            container, orient="horizontal", mode="determinate"
        )
        self.progress.pack(fill="x", pady=(0, 8))

        # Статус
        self.status_var = tk.StringVar(value="Готово.")
        ttk.Label(container, textvariable=self.status_var).pack(fill="x")

        # Служебные переменные
        self.scanner = Scanner1()
        # self.scanner.load_cache()
        self.stop_flag = threading.Event()
        self.worker_thread = None

    def show_duplicates(self):
        """
        Показывает найденные дубликаты внутри эталонной директории.
        Использует hash_map из Scanner1.
        """
        duplicates = find_internal_duplicates(self.scanner.hash_map)

        if not duplicates:
            messagebox.showinfo(
                "Дубликаты", "Внутри эталонной директории дубликатов не найдено."
            )
        else:
            # Формируем текст для вывода
            text = ""
            for h, paths in duplicates.items():
                text += f"Хеш: {h}\n"
                for p in paths:
                    text += f"  {p}\n"
                text += "\n"

            # Показываем в отдельном окне
            dup_win = tk.Toplevel(self.root)
            dup_win.title("Найденные дубликаты")
            txt = tk.Text(dup_win, wrap="none")
            txt.insert("1.0", text)
            txt.pack(fill="both", expand=True)

    def choose_dir(self):
        selected = filedialog.askdirectory(title="Выберите эталонную директорию")
        if selected:
            self.dir_var.set(selected)

    def run_scan(self):
        dir_path = Path(self.dir_var.get())
        if not dir_path.exists() or not dir_path.is_dir():
            messagebox.showerror("Ошибка", "Укажите корректную директорию.")
            return

        self.stop_flag.clear()
        self.start_btn.configure(state="disabled")
        self.status_var.set("Сканирование запущено…")

        self.worker_thread = threading.Thread(
            target=self._scan_worker, args=(dir_path,), daemon=True
        )
        self.worker_thread.start()

    def stop_scan(self):
        self.stop_flag.set()
        self.status_var.set("Остановка по запросу…")

    def _scan_worker(self, dir_path: Path):
        def progress_callback(processed, total):
            self.root.after(
                0, lambda: self.progress.configure(maximum=total, value=processed)
            )

        self.scanner.scan_directory(dir_path, self.stop_flag, progress_callback)

        if self.stop_flag.is_set():
            self.root.after(0, lambda: self.status_var.set("Сканирование прервано."))
        else:
            self.root.after(0, lambda: self.status_var.set("Сканирование завершено."))

        # включаем кнопки после сканирования
        self.root.after(0, lambda: self.show_dupes_btn.configure(state="normal"))
        self.root.after(0, lambda: self.start_btn.configure(state="normal"))


def main():
    root = tk.Tk()
    app = Scanner1GUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
