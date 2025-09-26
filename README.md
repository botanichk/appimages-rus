# 🐧 Void Community AppImage Helper 

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

## 🚀 Установка и удаление — всё просто
```
git clone https://github.com/botanichk/appimages-rus.git

cd appimages-rus

chmod +x install.sh

sudo ./install.sh
```

## После установки запускай:
```
appimages-helper
```

### Или найди в меню:
### Void Community AppImage Helper

## 🧹 Полное удаление:
> неыозможно (шутка ,ниже все есть )
--- 
# 🧠  А это для тех, кто ценит время  😎

## 🚀 Установка

```
sudo rm -rf appimages-rus && git clone https://github.com/botanichk/appimages-rus.git && cd appimages-rus && chmod +x install.sh && sudo ./install.sh
```
---
## 🧹 Удаление

```
sudo bash -c 'rm -rf /usr/local/bin/appimages /usr/local/bin/appimages-helper /usr/share/applications/appimages.desktop && rm -rf ~/.config/appimages' && rm -rf ~/appimages-rus
```
> Удалит всё: бинарники, ярлык, конфиги и даже папку с исходниками. Терминал снова чист, как после дождя.


