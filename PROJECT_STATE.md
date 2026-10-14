# Состояние проекта: SmallCaps Tool

## Структура
- `app.py`: Главный файл приложения (Tkinter, тёмная тема, Windows Job Objects ограничения, двусторонняя конвертация Small Caps).
- `app_icon.ico`: Иконка приложения для EXE и окна.
- `.github/workflows/build.yml`: CI/CD сборка исполняемого файла SmallCaps.exe в облаке.
- `BUILD.md`: Инструкция по сборке.

## Принятые решения
- Язык: Python 3 + нативный Tkinter (потребление ОЗУ ~6.5 МБ, нагрузка в простое 0%).
- Лимиты ресурсов: Windows Job Object (CPU hard cap 20%, RAM hard cap 256 МБ, приоритет BELOW_NORMAL).
- Автораспознавание: кириллица -> small caps кириллица, латиница -> small caps латиница, mixed -> оба, small caps -> обычный текст.
- Сборка перенесена в приватный репозиторий GitHub Actions, чтобы не нагружать слабый локальный ПК (Pentium P4600 / 4GB RAM).
- Токены и секреты НЕ сохраняются в файлы проекта.
