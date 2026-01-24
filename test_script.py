from src.removing_duplicated.scanner import find_duplicates_between
from pathlib import Path

d1 = Path("D:/тест1")
d2 = Path("D:/тест2")
print(d1, d2)
duplicates = find_duplicates_between(d1, d2)
print("Дубликаты в dir1:")
for f in duplicates:
    print(f)
