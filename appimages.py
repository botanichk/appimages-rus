#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Void Community AppImage Helper — Полная русская версия
# Автор: Pinguin-TV (исправления и перевод: твой братик 🐧)

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, Gio
import os
import json
import requests
import threading
import subprocess
import shutil
from urllib.parse import quote
from pathlib import Path

# --- Константы ---
CONFIG_DIR = os.path.expanduser("~/.config/appimages")
CONFIG_FILE = os.path.join(CONFIG_DIR, "settings.json")
APP_DIR = "/usr/local/bin/appimages"
ICON_BASE_DIR = os.path.expanduser("~/.local/share/icons/hicolor/128x128/apps")
DEFAULT_APPIMAGE_DIR = os.path.expanduser("~/AppImages")

def ensure_dir(path):
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return True
    except Exception:
        return False

class AppImageManager(Gtk.Window):
    def __init__(self):
        super().__init__(title="Void Community AppImage Helper")
        self.window = self
        self.set_default_size(800, 600)
        self.set_border_width(10)
        self.set_position(Gtk.WindowPosition.CENTER)

        defaults = {
            'appimage_dir': DEFAULT_APPIMAGE_DIR,
            'opacity': 0.95
        }
        try:
            with open(CONFIG_FILE, 'r') as f:
                self.settings = json.load(f)
            self.settings = {**defaults, **self.settings}
        except (FileNotFoundError, json.JSONDecodeError):
            self.settings = defaults

        self.apply_transparency()
        self.initialize_app_directory()
        self.download_active = False
        self.current_download_path = None
        self.setup_ui()
        self.connect("destroy", Gtk.main_quit)

    def setup_ui(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(vbox)

        menubar = Gtk.MenuBar()
        vbox.pack_start(menubar, False, False, 0)

        file_menu = Gtk.Menu()
        file_item = Gtk.MenuItem(label="Файл")
        file_item.set_submenu(file_menu)
        quit_item = Gtk.MenuItem(label="Выход")
        quit_item.connect("activate", Gtk.main_quit)
        file_menu.append(quit_item)
        menubar.append(file_item)

        tools_menu = Gtk.Menu()
        tools_item = Gtk.MenuItem(label="Инструменты")
        tools_item.set_submenu(tools_menu)
        settings_item = Gtk.MenuItem(label="Настройки")
        settings_item.connect("activate", self.open_settings)
        tools_menu.append(settings_item)
        menubar.append(tools_item)

        info_menu = Gtk.Menu()
        info_item = Gtk.MenuItem(label="Информация")
        info_item.set_submenu(info_menu)
        about_item = Gtk.MenuItem(label="О программе")
        about_item.connect("activate", self.show_about)
        info_menu.append(about_item)
        menubar.append(info_item)

        hbox_search = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        self.entry_search = Gtk.Entry()
        self.entry_search.set_placeholder_text("Введите название приложения...")
        self.button_search = Gtk.Button(label="Поиск")
        self.button_search.connect("clicked", self.on_search_clicked)
        hbox_search.pack_start(self.entry_search, True, True, 0)
        hbox_search.pack_start(self.button_search, False, False, 0)
        vbox.pack_start(hbox_search, False, False, 0)

        self.listbox_results = Gtk.ListBox()
        self.listbox_results.set_selection_mode(Gtk.SelectionMode.NONE)
        scrolled_results = Gtk.ScrolledWindow()
        scrolled_results.add(self.listbox_results)
        scrolled_results.set_size_request(-1, 300)
        vbox.pack_start(scrolled_results, True, True, 0)

        self.statusbar = Gtk.Label(label="Готов к поиску...")
        self.statusbar.set_halign(Gtk.Align.START)
        vbox.pack_start(self.statusbar, False, False, 5)

        self.button_download = Gtk.Button(label="Скачать")
        self.button_download.set_sensitive(False)
        self.button_download.connect("clicked", self.on_download_clicked)
        vbox.pack_start(self.button_download, False, False, 0)

        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_fraction(0.0)
        self.progress_bar.set_text("0%")
        self.progress_bar.set_show_text(True)
        vbox.pack_start(self.progress_bar, False, False, 0)

    def update_status(self, text):
        GLib.idle_add(self.statusbar.set_text, text)

    def on_search_clicked(self, widget):
        query = self.entry_search.get_text().strip()
        if not query:
            self.update_status("Введите запрос для поиска!")
            return

        self.update_status("Поиск... Пожалуйста, подождите.")
        self.listbox_results.foreach(lambda child: self.listbox_results.remove(child))
        self.button_download.set_sensitive(False)

        thread = threading.Thread(target=self.search_appimages, args=(query,))
        thread.daemon = True
        thread.start()

    def search_appimages(self, query):
        results = []
        try:
            hub_url = f"https://appimage.github.io/api/applications/?search={quote(query)}"
            response = requests.get(hub_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                for item in data.get('results', []):
                    name = item.get('name', 'Без названия')
                    description = item.get('description', 'Нет описания')
                    download_url = item.get('download_url', '')
                    icon_url = item.get('icon_url', '')
                    if download_url and download_url.endswith('.AppImage'):
                        results.append({
                            'name': name,
                            'description': description,
                            'url': download_url,
                            'icon_url': icon_url,
                            'source': 'AppImageHub'
                        })

            gh_url = f"https://api.github.com/search/repositories?q={quote(query)}+AppImage+in:name,description"
            response = requests.get(gh_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                for item in data.get('items', [])[:5]:
                    name = item.get('name', 'Без названия')
                    description = item.get('description', 'Нет описания') or 'Нет описания'
                    repo_url = item.get('html_url', '')
                    direct_url = self.get_github_appimage_link(repo_url)
                    if direct_url:
                        results.append({
                            'name': name,
                            'description': description,
                            'url': direct_url,
                            'icon_url': '',
                            'source': 'GitHub'
                        })
        except Exception as e:
            GLib.idle_add(self.update_status, f"Ошибка поиска: {e}")
            return

        GLib.idle_add(self.display_results, results)

    def get_github_appimage_link(self, repo_url):
        try:
            api_url = repo_url.replace('https://github.com', 'https://api.github.com/repos') + '/releases/latest'
            response = requests.get(api_url, timeout=10)
            if response.status_code == 200:
                release = response.json()
                assets = release.get('assets', [])
                for asset in assets:
                    download_url = asset.get('browser_download_url', '')
                    if download_url.endswith('.AppImage'):
                        return download_url
        except:
            pass
        return None

    def display_results(self, results):
        if not results:
            self.update_status("Ничего не найдено.")
            return

        for item in results:
            row = Gtk.ListBoxRow()
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            icon = Gtk.Image.new_from_icon_name("application-x-executable", Gtk.IconSize.DIALOG)
            hbox.pack_start(icon, False, False, 0)
            vbox_info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            label_name = Gtk.Label(label=f"<b>{item['name']}</b> ({item['source']})", use_markup=True)
            label_name.set_halign(Gtk.Align.START)
            label_desc = Gtk.Label(label=item['description'][:100] + "..." if len(item['description']) > 100 else item['description'])
            label_desc.set_halign(Gtk.Align.START)
            label_desc.get_style_context().add_class("dim-label")
            vbox_info.pack_start(label_name, False, False, 0)
            vbox_info.pack_start(label_desc, False, False, 0)
            hbox.pack_start(vbox_info, True, True, 0)
            button_select = Gtk.Button(label="Выбрать")
            button_select.connect("clicked", self.on_select_result, item)
            hbox.pack_start(button_select, False, False, 0)
            row.add(hbox)
            self.listbox_results.add(row)

        self.listbox_results.show_all()
        self.update_status(f"Найдено {len(results)} результатов.")

    def on_select_result(self, button, item):
        self.selected_item = item
        self.button_download.set_sensitive(True)
        self.update_status(f"Выбрано: {item['name']} — готово к скачиванию.")

    def on_download_clicked(self, widget):
        if not hasattr(self, 'selected_item'):
            self.update_status("Сначала выберите приложение для скачивания!")
            return

        item = self.selected_item
        url = item['url']
        if not url:
            self.update_status("Нет ссылки для скачивания!")
            return

        filename = url.split('/')[-1]
        if not filename.endswith('.AppImage'):
            filename = f"{item['name'].replace(' ', '_')}.AppImage"

        self.current_download_path = os.path.join(self.settings['appimage_dir'], filename)

        self.download_active = True
        self.button_download.set_sensitive(False)
        self.progress_bar.set_fraction(0.0)
        self.update_status("Начинаю загрузку...")

        thread = threading.Thread(target=self.download_appimage, args=(url, self.current_download_path))
        thread.daemon = True
        thread.start()

    def download_appimage(self, url, filepath):
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            ensure_dir(os.path.dirname(filepath))
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if not self.download_active:
                        GLib.idle_add(self.update_status, "Загрузка отменена.")
                        return
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            fraction = downloaded / total_size
                            GLib.idle_add(self.progress_bar.set_fraction, fraction)
                            GLib.idle_add(self.progress_bar.set_text, f"{int(fraction * 100)}%")

            os.chmod(filepath, 0o755)
            self.create_desktop_entry(filepath, self.selected_item['name'], self.selected_item.get('icon_url', ''))

            GLib.idle_add(self.update_status, "Загрузка завершена! Приложение установлено.")
            GLib.idle_add(self.progress_bar.set_fraction, 1.0)
            GLib.idle_add(self.progress_bar.set_text, "100% — Готово!")

        except Exception as e:
            GLib.idle_add(self.update_status, f"Ошибка загрузки: {e}")
        finally:
            self.download_active = False
            GLib.idle_add(self.button_download.set_sensitive, True)

    def create_desktop_entry(self, appimage_path, name, icon_url):
        desktop_filename = f"{name.replace(' ', '_').lower()}.desktop"
        desktop_path = os.path.expanduser(f"~/.local/share/applications/{desktop_filename}")

        icon_path = "application-x-executable"
        if icon_url:
            icon_filename = f"{name.replace(' ', '_').lower()}.png"
            icon_path = os.path.join(ICON_BASE_DIR, icon_filename)
            try:
                response = requests.get(icon_url, timeout=10)
                if response.status_code == 200:
                    ensure_dir(ICON_BASE_DIR)
                    with open(icon_path, 'wb') as f:
                        f.write(response.content)
                    subprocess.run(['gtk-update-icon-cache', '-f', os.path.expanduser('~/.local/share/icons/hicolor')], capture_output=True)
                    icon_path = icon_filename
            except Exception as e:
                print(f"Ошибка загрузки иконки: {e}")
                icon_path = "application-x-executable"

        desktop_content = f"""[Desktop Entry]
Name={name}
Exec={appimages.py}
Icon={icon_path}
Type=Application
Categories=Utility;
Comment=Запустить {name} через AppImage
Terminal=false
"""

        try:
            ensure_dir(os.path.dirname(desktop_path))
            with open(desktop_path, 'w') as f:
                f.write(desktop_content)
            subprocess.run(['update-desktop-database', os.path.expanduser('~/.local/share/applications')], capture_output=True)
        except Exception as e:
            self.update_status(f"Не удалось создать .desktop файл: {e}")

    def open_settings(self, widget):
        dialog = Gtk.Dialog(title="Настройки", transient_for=self, flags=0)
        dialog.add_buttons("OK", Gtk.ResponseType.OK, "Отмена", Gtk.ResponseType.CANCEL)
        dialog.set_default_size(400, 200)
        box = dialog.get_content_area()
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_border_width(10)
        box.add(vbox)

        hbox_dir = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        label_dir = Gtk.Label(label="Папка для AppImage:")
        self.entry_dir = Gtk.Entry()
        self.entry_dir.set_text(self.settings['appimage_dir'])
        button_browse = Gtk.Button(label="Обзор...")
        button_browse.connect("clicked", self.on_browse_folder, self.entry_dir)
        hbox_dir.pack_start(label_dir, False, False, 0)
        hbox_dir.pack_start(self.entry_dir, True, True, 0)
        hbox_dir.pack_start(button_browse, False, False, 0)
        vbox.pack_start(hbox_dir, False, False, 0)

        hbox_opacity = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        label_opacity = Gtk.Label(label="Прозрачность (0.0–1.0):")
        self.spin_opacity = Gtk.SpinButton()
        self.spin_opacity.set_range(0.0, 1.0)
        self.spin_opacity.set_increments(0.05, 0.1)
        self.spin_opacity.set_digits(2)
        self.spin_opacity.set_value(self.settings['opacity'])
        hbox_opacity.pack_start(label_opacity, False, False, 0)
        hbox_opacity.pack_start(self.spin_opacity, True, True, 0)
        vbox.pack_start(hbox_opacity, False, False, 0)

        dialog.show_all()
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            new_dir = self.entry_dir.get_text().strip()
            new_opacity = self.spin_opacity.get_value()

            if new_dir and (os.path.isdir(new_dir) or ensure_dir(new_dir)):
                self.settings['appimage_dir'] = new_dir
                self.settings['opacity'] = new_opacity
                self.save_settings()
                self.apply_transparency()
                self.update_status("Настройки сохранены.")
            else:
                self.update_status("Ошибка: папка не существует и не может быть создана.")

        dialog.destroy()

    def on_browse_folder(self, button, entry):
        dialog = Gtk.FileChooserDialog(
            title="Выберите папку для AppImage",
            parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER
        )
        dialog.add_buttons("Отмена", Gtk.ResponseType.CANCEL, "OK", Gtk.ResponseType.OK)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            entry.set_text(dialog.get_filename())
        dialog.destroy()

    def show_about(self, widget):
        dialog = Gtk.AboutDialog()
        dialog.set_program_name("Void Community AppImage Helper")
        dialog.set_version("1.0")
        dialog.set_authors(["Pinguin-TV"])
        dialog.set_comments("Графический помощник для поиска и управления AppImage-приложениями на Void Linux.")
        dialog.set_website("https://codeberg.org/pinguin-tv/appimages")
        dialog.set_website_label("Страница проекта")
        dialog.set_logo_icon_name("application-x-executable")
        dialog.set_license_type(Gtk.License.UNKNOWN)
        dialog.set_copyright("© 2025 Pinguin-TV\nЧасть проекта Void-Gemeni")
        dialog.run()
        dialog.destroy()

    def save_settings(self):
        try:
            ensure_dir(CONFIG_DIR)
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.settings, f, indent=4)
        except IOError as e:
            self.update_status(f"Настройки не удалось сохранить: {e}")

    def apply_transparency(self):
        screen = self.window.get_screen()
        if screen and screen.is_composited() and (visual := screen.get_rgba_visual()):
            self.window.set_visual(visual)
            provider = Gtk.CssProvider()
            css = (f"GtkWindow {{ background-color: rgba(45, 45, 45, {self.settings['opacity']}); }} "
                   f".dim-label {{ opacity: 0.7; font-size: 10pt; }}")
            provider.load_from_data(css.encode('utf-8'))
            Gtk.StyleContext.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def initialize_app_directory(self):
        ensure_dir(self.settings['appimage_dir'])
        ensure_dir(APP_DIR)
        ensure_dir(ICON_BASE_DIR)
    def create_desktop_entry(self, appimage_path, name, icon_url):
        desktop_filename = f"{name.replace(' ', '_').lower()}.desktop"
        desktop_path = os.path.expanduser(f"~/.local/share/applications/{desktop_filename}")

        icon_path = "application-x-executable"
        if icon_url:
            icon_filename = f"{name.replace(' ', '_').lower()}.png"
            icon_path = os.path.join(ICON_BASE_DIR, icon_filename)
            try:
                response = requests.get(icon_url, timeout=10)
                if response.status_code == 200:
                    ensure_dir(ICON_BASE_DIR)
                    with open(icon_path, 'wb') as f:
                        f.write(response.content)
                    subprocess.run(['gtk-update-icon-cache', '-f', os.path.expanduser('~/.local/share/icons/hicolor')], capture_output=True)
                    icon_path = icon_filename
            except Exception as e:
                print(f"Ошибка загрузки иконки: {e}")
                icon_path = "application-x-executable"

        desktop_content = f"""[Desktop Entry]
Name={name}
Exec={appimage_path}
Icon={icon_path}
Type=Application
Categories=Utility;
Comment=Запустить {name} через AppImage
Terminal=false
"""

        try:
            ensure_dir(os.path.dirname(desktop_path))
            with open(desktop_path, 'w') as f:
                f.write(desktop_content)
            subprocess.run(['update-desktop-database', os.path.expanduser('~/.local/share/applications')], capture_output=True)
        except Exception as e:
            self.update_status(f"Не удалось создать .desktop файл: {e}")

if __name__ == "__main__":
    app = AppImageManager()
    app.window.show_all()
    Gtk.main()
