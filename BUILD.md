# Сборка SmallCaps C++

## 1. Сборка в облаке через GitHub Actions (Рекомендуется для слабого ПК)
Сборка происходит автоматически в GitHub Actions на Windows runners при каждом коммите/пуше в ветку `main`, при создании тега `v*` или вручную через вкладку **Actions** -> **Run workflow**.

- Готовый артефакт `SmallCaps.exe` доступен для скачивания в разделе запусков Actions.
- При тегах релиза бинарник автоматически публикуется в раздел **Releases**.

## 2. Локальная сборка (MinGW C++17)
Требования: `g++` и `windres` (MinGW-w64).

```cmd
windres.exe resource.rc -O coff -o resource.res
g++.exe -O3 -mwindows -s -static -std=c++17 main.cpp resource.res -luser32 -lgdi32 -lshell32 -lcomctl32 -lpsapi -ldwmapi -o SmallCaps.exe
```

Размер бинарника: ~218 КБ. Потребление ОЗУ: ~1-2 МБ в работе, < 500 КБ при сворачивании в трей.
