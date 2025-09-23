# 🐧 Void Community AppImage Helper — МОЯ ИСПРАВЛЕННАЯ ВЕРСИЯ

Это моя личная, улучшенная версия помощника — с **рабочим поиском, загрузкой, русским интерфейсом и иконкой**.

## ✅ Что исправлено:
- Полностью русский интерфейс
- Рабочий поиск на GitHub (только прямые ссылки .AppImage)
- Универсальный `install.sh` для всех дистрибутивов
- Исправлены ошибки загрузки и установки
- Добавлена красивая иконка
- ⚠️ Для пользователей Arch-based систем (CachyOS, Arch, EndeavourOS)
На данный момент Python 3.13 не полностью совместим с PyGObject.

Решение:

bash

yay -S python312 --noconfirm
sudo pacman -S python-gobject python-requests gtk3 --needed
sudo nano /usr/local/bin/appimages/appimages.py
# Замени первую строку на: #!/usr/bin/env python3.12
appimages-helper
💡 Это временная мера — скоро всё заработает и на Python 3.13. 

## 🚀 Установка:
```bash
git clone https://github.com/botanichk/appimages-rus.git
cd appimages-rus
chmod +x install.sh
sudo ./install.sh
🐧 🐧 🐧 🐧 🐧

