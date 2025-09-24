markdown
# 🐧 Void Community AppImage Helper — МОЯ ИСПРАВЛЕННАЯ ВЕРСИЯ

> *«Начало чего-то нового и лучшего»* — как и задумывал автор, но теперь — на родном языке.

Это **моя личная, улучшенная версия** графического помощника для поиска, скачивания и управления AppImage-приложениями на Void Linux (и не только!).

✅ **Полностью на русском**  
✅ **Рабочий поиск и загрузка**  
✅ **Своя иконка**  
✅ **Универсальный install.sh**  
✅ **Без багов, без мусора**

---

## ✨ Функции

- 🔍 **Поиск** AppImage’ов на **AppImageHub** и **GitHub** (только прямые ссылки!)
- ⬇️ **Скачивание** с прогресс-баром
- 🚀 **Установка** — создаётся `.desktop` файл, можно запускать из меню
- 🗑️ **Удаление** — убери ненужное
- 🖼️ **Иконки** — автоматически скачиваются и регистрируются (если есть на AppImageHub)
- 🎨 **Прозрачный интерфейс** (если включён композитор)
- ⚙️ **Настройки** — папка загрузки, прозрачность
- 📂 **Меню** — Файл, Инструменты, О программе

---

## 🚀 Установка и удаление — всё просто

```bash
git clone https://github.com/botanichk/appimages-rus.git
cd appimages-rus
chmod +x install.sh
sudo ./install.sh
После установки запускай:

bash
appimages-helper
Или найди в меню:

Void Community AppImage Helper

⚠️ Для пользователей Arch-based систем (CachyOS, Arch, EndeavourOS)
На данный момент Python 3.13 не полностью совместим с PyGObject, из-за чего приложение не запускается.

🔧 Решение:

bash
yay -S python312 --noconfirm
sudo pacman -S python-gobject python-requests gtk3 --needed
sudo nano /usr/local/bin/appimages/appimages.py
🔁 Замени первую строку на:

python
#!/usr/bin/env python3.12
💡 Сохрани и запусти:

bash
appimages-helper
Это временная мера — проблема исчезнет после обновления python-gobject.

🧹 Полное удаление
Чтобы полностью удалить приложение со всеми следами:

bash
sudo rm -rf /usr/local/bin/appimages
sudo rm -f /usr/local/bin/appimages-helper
sudo rm -f /usr/share/applications/appimages.desktop
rm -rf 
