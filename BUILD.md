# Сборка SmallCaps

## 1. Сборка в облаке через GitHub Actions (Рекомендуется для слабого ПК)
Сборка происходит автоматически в GitHub Actions на Windows runners при каждом коммите/пуше в ветку `main` или вручную через вкладку **Actions** -> **Run workflow**.

Артефакт `SmallCaps.exe` доступен для скачивания в разделе завершённого запуска Actions.

## 2. Локальная сборка (если требуется)
Требования: Python 3.10+ и PyInstaller.

```cmd
pip install pyinstaller
pyinstaller --noconsole --onefile --noupx --name "SmallCaps" --icon="app_icon.ico" --add-data "app_icon.ico;." app.py
```
Готовый файл появится в папке `dist/SmallCaps.exe`.
