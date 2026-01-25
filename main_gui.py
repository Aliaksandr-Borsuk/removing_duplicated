# main_gui.py
# Общий GUI для Scanner‑1 и Scanner‑2
# Использует вкладки (Notebook), чтобы запускать оба интерфейса из одного окна.

import tkinter as tk
from tkinter import ttk
from src.removing_duplicates.gui_for_scanner_1 import Scanner1GUI
from src.removing_duplicates.gui_for_scanner_2 import Scanner2GUI


def main():
    # Создаём главное окно
    root = tk.Tk()
    root.title("Duplicate Scanner Suite")
    root.minsize(800, 600)

    # Notebook — это виджет вкладок
    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True)

    # Вкладка Scanner‑1
    frame1 = ttk.Frame(notebook)
    # Передаём frame1 как root для Scanner1GUI
    Scanner1GUI(frame1)
    notebook.add(frame1, text="Эталонная папка (Scanner‑1)")

    # Вкладка Scanner‑2
    frame2 = ttk.Frame(notebook)
    # Передаём frame2 как root для Scanner2GUI
    Scanner2GUI(frame2)
    notebook.add(frame2, text="Очистка папки (Scanner‑2)")

    # Запускаем главный цикл
    root.mainloop()


if __name__ == "__main__":
    main()
