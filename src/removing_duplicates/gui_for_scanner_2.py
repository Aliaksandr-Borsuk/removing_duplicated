# gui_for_scanner_2.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import threading
from src.removing_duplicates.scanner_2 import Scanner2


class Scanner2GUI:
    """
    Графический интерфейс для Scanner‑2:
    - выбор эталонной и очищаемой директорий;
    - настройки (удалять дубликаты, переносить уникальные, только анализ);
    - запуск сканирования с прогресс‑баром;
    - просмотр результатов;
    - отдельная кнопка для удаления пустых папок.
    """

    def __init__(self, root):
        self.root = root
        # self.root.title("Scanner‑2 (Очистка папки)")
        # self.root.minsize(700, 400)

        container = ttk.Frame(root, padding=12)
        container.pack(fill="both", expand=True)

        # Выбор эталонной директории
        self.ref_var = tk.StringVar()
        ref_row = ttk.Frame(container)
        ref_row.pack(fill="x", pady=(0, 8))
        ttk.Label(ref_row, text="Эталонная директория:").pack(side="left")
        ttk.Entry(ref_row, textvariable=self.ref_var).pack(
            side="left", fill="x", expand=True, padx=8
        )
        ttk.Button(ref_row, text="Выбрать…", command=self.choose_ref).pack(side="left")

        # Выбор очищаемой директории
        self.target_var = tk.StringVar()
        tgt_row = ttk.Frame(container)
        tgt_row.pack(fill="x", pady=(0, 8))
        ttk.Label(tgt_row, text="Очищаемая директория:").pack(side="left")
        ttk.Entry(tgt_row, textvariable=self.target_var).pack(
            side="left", fill="x", expand=True, padx=8
        )
        ttk.Button(tgt_row, text="Выбрать…", command=self.choose_target).pack(
            side="left"
        )

        # Настройки
        opts_row = ttk.LabelFrame(container, text="Настройки")
        opts_row.pack(fill="x", pady=(0, 8))
        self.delete_dupes = tk.BooleanVar(value=False)
        self.move_uniques = tk.BooleanVar(value=False)
        self.collect_only = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            opts_row, text="Удалять дубликаты", variable=self.delete_dupes
        ).pack(anchor="w")
        ttk.Checkbutton(
            opts_row, text="Переносить уникальные", variable=self.move_uniques
        ).pack(anchor="w")
        ttk.Checkbutton(
            opts_row, text="Только анализ (без действий)", variable=self.collect_only
        ).pack(anchor="w")

        # Кнопки управления
        actions_row = ttk.Frame(container)
        actions_row.pack(fill="x", pady=(0, 8))
        self.start_btn = ttk.Button(
            actions_row, text="Сканировать", command=self.run_scan
        )
        self.start_btn.pack(side="left")
        self.stop_btn = ttk.Button(actions_row, text="Прервать", command=self.stop_scan)
        self.stop_btn.pack(side="left", padx=8)
        self.empty_btn = ttk.Button(
            actions_row, text="Удалить пустые папки", command=self.delete_empty_dirs
        )
        self.empty_btn.pack(side="left", padx=8)

        # Прогресс‑бар
        self.progress = ttk.Progressbar(
            container, orient="horizontal", mode="determinate"
        )
        self.progress.pack(fill="x", pady=(0, 8))

        # Статус
        self.status_var = tk.StringVar(value="Готово.")
        ttk.Label(container, textvariable=self.status_var).pack(fill="x")

        # Результаты
        self.result_box = tk.Text(container, height=10, wrap="none")
        self.result_box.pack(fill="both", expand=True, pady=(8, 0))

        # Служебные переменные
        self.scanner = None
        self.stop_flag = threading.Event()
        self.worker_thread = None

    def choose_ref(self):
        selected = filedialog.askdirectory(title="Выберите эталонную директорию")
        if selected:
            self.ref_var.set(selected)

    def choose_target(self):
        selected = filedialog.askdirectory(title="Выберите очищаемую директорию")
        if selected:
            self.target_var.set(selected)

    def run_scan(self):
        ref = Path(self.ref_var.get())
        tgt = Path(self.target_var.get())
        if not ref.exists() or not tgt.exists():
            messagebox.showerror("Ошибка", "Укажите корректные директории.")
            return

        self.scanner = Scanner2(
            reference_dir=ref,
            target_dir=tgt,
            delete_duplicates=self.delete_dupes.get(),
            move_uniques=self.move_uniques.get(),
            collect_only=self.collect_only.get(),
        )

        try:
            self.scanner.check_dirs()
            self.scanner.load_cache()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
            return

        self.stop_flag.clear()
        self.start_btn.configure(state="disabled")
        self.status_var.set("Сканирование запущено…")
        self.result_box.delete("1.0", "end")

        self.worker_thread = threading.Thread(
            target=self._scan_worker, args=(tgt,), daemon=True
        )
        self.worker_thread.start()

    def stop_scan(self):
        self.stop_flag.set()
        self.status_var.set("Остановка по запросу…")

    def _scan_worker(self, target_dir: Path):
        def progress_callback(processed, total):
            self.root.after(
                0, lambda: self.progress.configure(maximum=total, value=processed)
            )

        self.scanner.scan_target(
            stop_flag=self.stop_flag, progress_callback=progress_callback
        )

        if self.stop_flag.is_set():
            self.root.after(0, lambda: self.status_var.set("Сканирование прервано."))
        else:
            self.root.after(0, lambda: self.status_var.set("Сканирование завершено."))
            self.root.after(0, self._show_results)

        self.root.after(0, lambda: self.start_btn.configure(state="normal"))

    def _show_results(self):
        text = f"Дубликатов найдено: {len(self.scanner.duplicates)}\n"
        text += f"Уникальных файлов: {len(self.scanner.unique_files)}\n\n"
        if self.scanner.duplicates:
            text += "Дубликаты:\n" + "\n".join(self.scanner.duplicates[:20]) + "\n...\n"
        if self.scanner.unique_files:
            text += (
                "\nУникальные:\n"
                + "\n".join(self.scanner.unique_files[:20])
                + "\n...\n"
            )
        self.result_box.insert("1.0", text)

    def delete_empty_dirs(self):
        if not self.scanner:
            messagebox.showerror("Ошибка", "Сканирование ещё не выполнялось.")
            return
        removed = self.scanner.delete_empty_dirs()
        messagebox.showinfo(
            "Удаление пустых папок", f"Удалено {removed} пустых директорий."
        )


def main():
    root = tk.Tk()
    app = Scanner2GUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
