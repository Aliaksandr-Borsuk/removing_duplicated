from pathlib import Path


def main():
    print("Привет! Утилита для поиска дубликатов готова к работе.")
    print("Текущая папка проекта:", Path(__file__).resolve().parent)


if __name__ == "__main__":
    main()
