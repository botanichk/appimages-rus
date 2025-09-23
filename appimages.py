#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Void Community AppImage Helper (VCAH) – überarbeitete Version
- Logo im "Über"-Dialog hinzugefügt
- Verbesserte GitHub-Suche, um mehr Apps wie "bauh" zu finden
- Mehrere Suchquellen (AppImageHub, GitHub)
- Robustere Fehlerbehandlung
- Statusleiste (Gtk.Statusbar)
- Sichere Auswahl-Handler
- Slugify für Dateinamen / Desktop-Dateien
- (Optional) Icon-Download & -Registrierung
- Fortschrittsanzeige mit Drosselung
- Transparenz via CSS, wenn Compositor verfügbar ist
"""

import gi
gi.require_version('Gtk', '3.0')
# --- NEUER IMPORT FÜR DAS LOGO ---
from gi.repository import Gtk, Gdk, GLib, GdkPixbuf

import os
import re
import time
import json
import stat
import threading
import subprocess

# Falls 'requests' nicht vorhanden ist, bitte nachinstallieren:
#   sudo xbps-install -S python3-requests   (Void)
import requests

# --- Globale Konstanten ---
DESIGNER_TEXT = "designed by armin@Pinguin-TV"
LOGO_PATH = "/usr/local/bin/appimages/icons/logo.png" # --- PFAD ZUM LOGO ---

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "appimage-helper")
CONFIG_FILE = os.path.join(CONFIG_DIR, "settings.json")

APP_DIR = os.path.expanduser("~/.local/share/applications/")
ICON_BASE_DIR = os.path.expanduser("~/.local/share/icons/hicolor")
ICON_SIZES_PREFERRED = ["256x256", "128x128", "64x64", "48x48", "32x32"]

APP_ICON_PATH = "/usr/local/bin/appimages/icons/appimages.png"


def slugify(text: str) -> str:
    """Einfaches Slugify: Kleinbuchstaben, Leerzeichen/Unterstrich → Bindestrich, Sonderzeichen entfernen."""
    if not text:
        return "appimage"
    text = text.lower()
    text = text.replace("_", "-").replace(" ", "-")
    text = re.sub(r"[^a-z0-9\-]+", "", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text or "appimage"


def ensure_dir(path: str):
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        pass


class AppImageManager:

    def __init__(self):
        self.all_apps_data = []
        self._progress_last_ui_update = 0.0
        self.load_settings()
        self.initialize_app_directory()

        self.window = Gtk.Window(title="Void Community AppImage Helper")
        try:
            Gtk.Window.set_default_icon_from_file(APP_ICON_PATH)
            self.window.set_icon_from_file(APP_ICON_PATH)
        except Exception as e:
            print(f"Warnung: Konnte App-Icon nicht laden: {e}")
        
        self.window.set_default_size(self.settings['width'], self.settings['height'])
        self.window.set_position(Gtk.WindowPosition.CENTER)
        self.window.connect("destroy", self.on_quit)
        self.apply_transparency()

        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.window.add(main_vbox)

        main_vbox.pack_start(self.create_menubar(), False, False, 0)

        self.notebook = Gtk.Notebook()
        main_vbox.pack_start(self.notebook, True, True, 0)

        self.notebook.append_page(self.create_search_tab(), Gtk.Label(label="Suchen & Installieren"))
        self.notebook.append_page(self.create_installed_tab(), Gtk.Label(label="Installierte Apps"))
        self.notebook.connect("switch-page", self.on_tab_switched)

        footer_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8, margin=6)
        designer_label = Gtk.Label(label=DESIGNER_TEXT, xalign=0)
        designer_label.get_style_context().add_class("dim-label")
        footer_box.pack_start(designer_label, False, False, 6)

        self.statusbar = Gtk.Statusbar()
        self.status_ctx = self.statusbar.get_context_id("vcah-status")
        footer_box.pack_end(self.statusbar, True, True, 0)

        main_vbox.pack_end(footer_box, False, True, 0)

        self.update_status("Bereit. Bitte Suchbegriff eingeben.")

    # --- UI Erstellung ---

    def create_search_tab(self):
        main_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10, margin=10)
        vbox_left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        main_hbox.pack_start(vbox_left, True, True, 0)

        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.search_entry = Gtk.SearchEntry(placeholder_text="Anwendung suchen…")
        self.search_entry.connect("search-changed", self.on_search_changed)
        search_box.pack_start(self.search_entry, True, True, 0)
        
        self.source_combo = Gtk.ComboBoxText()
        self.source_combo.append_text("AppImageHub")
        self.source_combo.append_text("GitHub")
        self.source_combo.set_active(0)
        search_box.pack_start(self.source_combo, False, False, 0)

        vbox_left.pack_start(search_box, False, True, 0)

        scrolled_window = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        vbox_left.pack_start(scrolled_window, True, True, 0)

        self.list_store = Gtk.ListStore(str, str, object)
        self.tree_view = Gtk.TreeView(model=self.list_store)
        scrolled_window.add(self.tree_view)

        for i, col_title in enumerate(["Name", "Beschreibung"]):
            renderer = Gtk.CellRendererText(ellipsize=3)
            column = Gtk.TreeViewColumn(col_title, renderer, text=i)
            column.set_resizable(True)
            column.set_expand(i == 1)
            self.tree_view.append_column(column)

        self.selection = self.tree_view.get_selection()
        self.selection.connect("changed", self.on_search_selection_changed)

        self.download_button = Gtk.Button(label="Ausgewähltes AppImage herunterladen", sensitive=False)
        self.download_button.connect("clicked", self.on_download_clicked)

        self.progress_bar = Gtk.ProgressBar(show_text=True, visible=False)

        bottom_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        bottom_box.pack_start(self.download_button, False, True, 0)
        bottom_box.pack_start(self.progress_bar, False, True, 0)
        vbox_left.pack_start(bottom_box, False, True, 0)

        self.detail_frame = Gtk.Frame(label="Details", shadow_type=Gtk.ShadowType.IN, visible=False)
        self.detail_frame.set_size_request(280, -1)
        
        detail_grid = Gtk.Grid(column_spacing=6, row_spacing=8, margin=10)
        self.detail_frame.add(detail_grid)

        self.detail_author = Gtk.Label(xalign=0, selectable=True)
        self.detail_license = Gtk.Label(xalign=0, selectable=True)
        self.detail_homepage = Gtk.LinkButton(uri="", label="Homepage besuchen")

        detail_grid.attach(Gtk.Label(label="<b>Autor:</b>", use_markup=True, xalign=0), 0, 0, 1, 1)
        detail_grid.attach(self.detail_author, 1, 0, 1, 1)
        detail_grid.attach(Gtk.Label(label="<b>Lizenz:</b>", use_markup=True, xalign=0), 0, 1, 1, 1)
        detail_grid.attach(self.detail_license, 1, 1, 1, 1)
        detail_grid.attach(Gtk.Label(label="<b>Homepage:</b>", use_markup=True, xalign=0), 0, 2, 1, 1)
        detail_grid.attach(self.detail_homepage, 1, 2, 1, 1)

        main_hbox.pack_start(self.detail_frame, False, False, 0)
        return main_hbox
    
    def create_installed_tab(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, margin=10)
        scrolled_window = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        vbox.pack_start(scrolled_window, True, True, 0)
        self.installed_store = Gtk.ListStore(str, str)
        self.installed_view = Gtk.TreeView(model=self.installed_store)
        scrolled_window.add(self.installed_view)
        for i, title in enumerate(["Name", "Pfad"]):
            col = Gtk.TreeViewColumn(title, Gtk.CellRendererText(), text=i)
            col.set_resizable(True)
            col.set_expand(i==1)
            self.installed_view.append_column(col)
        self.installed_selection = self.installed_view.get_selection()
        self.installed_selection.connect("changed", self.on_installed_selection_changed)
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.start_button = Gtk.Button(label="Starten", sensitive=False)
        self.delete_button = Gtk.Button(label="Löschen", sensitive=False)
        self.start_button.connect("clicked", self.on_start_clicked)
        self.delete_button.connect("clicked", self.on_delete_clicked)
        hbox.pack_start(self.start_button, True, True, 0)
        hbox.pack_start(self.delete_button, True, True, 0)
        vbox.pack_start(hbox, False, True, 0)
        return vbox

    def create_menubar(self):
        menubar = Gtk.MenuBar()

        file_menu = Gtk.Menu()
        file_item = Gtk.MenuItem(label="Datei")
        file_item.set_submenu(file_menu)
        settings_item = Gtk.MenuItem(label="Einstellungen")
        settings_item.connect("activate", self.on_settings_clicked)
        quit_item = Gtk.MenuItem(label="Beenden")
        quit_item.connect("activate", self.on_quit)
        file_menu.append(settings_item)
        file_menu.append(Gtk.SeparatorMenuItem())
        file_menu.append(quit_item)
        menubar.append(file_item)

        tools_menu = Gtk.Menu()
        tools_item = Gtk.MenuItem(label="Werkzeuge")
        tools_item.set_submenu(tools_menu)
        cleanup_item = Gtk.MenuItem(label="Verwaiste Einträge bereinigen")
        cleanup_item.connect("activate", self.cleanup_orphans)
        tools_menu.append(cleanup_item)
        menubar.append(tools_item)

        info_menu = Gtk.Menu()
        info_item = Gtk.MenuItem(label="Info")
        info_item.set_submenu(info_menu)
        about_item = Gtk.MenuItem(label="Über…")
        about_item.connect("activate", self.on_about_clicked)
        info_menu.append(about_item)
        menubar.append(info_item)

        return menubar
        
    # --- Kernfunktionalität ---

    def start_search(self, search_term):
        self.list_store.clear()
        self.update_status(f"Suche nach '{search_term}'…")
        self.download_button.set_sensitive(False)
        self.detail_frame.set_visible(False)
        
        source = self.source_combo.get_active_text()
        if source == "GitHub":
            thread = threading.Thread(target=self.fetch_github_worker, args=(search_term,), daemon=True)
        else:
            thread = threading.Thread(target=self.fetch_appimagehub_worker, args=(search_term,), daemon=True)
        thread.start()

    def fetch_appimagehub_worker(self, search_term):
        try:
            url = "https://appimage.github.io/feed.json"
            headers = {"User-Agent": "VCAH/2.2"}
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json().get("items", [])
            st = search_term.lower()
            results = [item for item in data if st in (item.get("name") or "").lower() or st in (item.get("description") or "").lower()]
            self.all_apps_data = results
            GLib.idle_add(self.populate_list)
        except Exception as e:
            GLib.idle_add(self.update_status, f"Fehler bei AppImageHub-Suche: {e}")

    def fetch_github_worker(self, search_term):
        try:
            query = f'q={search_term} in:name,description&sort=stars&order=desc'
            url = f"https://api.github.com/search/repositories?{query}"
            headers = {"User-Agent": "VCAH/2.2", "Accept": "application/vnd.github.v3+json"}
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            repos = response.json().get("items", [])
            
            results = []
            for repo in repos[:20]:
                releases_url = repo["releases_url"].replace("{/id}", "")
                res_response = requests.get(f"{releases_url}?per_page=5", headers=headers, timeout=20)
                if res_response.status_code != 200: continue
                
                for release in res_response.json():
                    for asset in release.get("assets", []):
                        if asset["name"].lower().endswith(".appimage"):
                            app_data = {
                                "name": repo.get("name"),
                                "description": repo.get("description"),
                                "authors": [{"name": repo.get("owner", {}).get("login")}],
                                "license": (repo.get("license") or {}).get("name"),
                                "links": [
                                    {"type": "homepage", "url": repo.get("html_url")},
                                    {"type": "download", "url": asset.get("browser_download_url")}
                                ]
                            }
                            results.append(app_data)
                            break
            
            self.all_apps_data = results
            GLib.idle_add(self.populate_list)
        except Exception as e:
            GLib.idle_add(self.update_status, f"Fehler bei GitHub-Suche: {e}")

    def download_worker(self, app_data, url):
        try:
            filename = os.path.basename(url.split('?', 1)[0]) or f"{slugify(app_data['name'])}.AppImage"
            if not filename.lower().endswith(".appimage"): filename += ".AppImage"
            destination_path = os.path.join(self.settings['appimage_dir'], filename)
            headers = {"User-Agent": "VCAH/2.2"}
            with requests.get(url, headers=headers, stream=True, timeout=60) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                bytes_dl = 0
                with open(destination_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                        bytes_dl += len(chunk)
                        if total_size > 0:
                            frac = min(1.0, bytes_dl / float(total_size))
                            text = f"{bytes_dl/1e6:.1f}/{total_size/1e6:.1f} MB"
                            GLib.idle_add(self.progress_bar.set_fraction, frac)
                            GLib.idle_add(self.progress_bar.set_text, text)
            st = os.stat(destination_path)
            os.chmod(destination_path, st.st_mode | stat.S_IEXEC)
            icon_name = self.download_icon(app_data.get("name", ""), app_data)
            self.create_desktop_file(app_data, destination_path, icon_name)
            GLib.idle_add(self.on_download_finished, f"{app_data.get('name')} installiert!", True)
        except Exception as e:
            GLib.idle_add(self.on_download_finished, f"Fehler: {e}", False)
            
    # --- Event-Handler ---

    def on_search_changed(self, widget):
        search_term = widget.get_text().strip()
        if len(search_term) >= 3:
            self.start_search(search_term)
        else:
            self.list_store.clear()
            self.update_status("Bitte mindestens 3 Zeichen eingeben.")

    def on_search_selection_changed(self, selection):
        model, treeiter = selection.get_selected()
        if treeiter:
            app_data = model[treeiter][2] or {}
            author_text = "Unbekannt"
            authors = app_data.get("authors", [])
            if authors:
                first_author = authors[0]
                author_text = first_author.get("name") or "Unbekannt" if isinstance(first_author, dict) else first_author
            self.detail_author.set_text(author_text)
            self.detail_license.set_text(app_data.get("license") or "Unbekannt")
            homepage_url = next((link["url"] for link in app_data.get("links", []) if link.get("type") == "homepage" and link.get("url")), None)
            self.detail_homepage.set_uri(homepage_url or "about:blank")
            self.detail_homepage.set_sensitive(bool(homepage_url))
            self.detail_frame.set_visible(True)
            self.download_button.set_sensitive(True)
        else:
            self.detail_frame.set_visible(False)
            self.download_button.set_sensitive(False)

    def on_download_clicked(self, _widget):
        model, treeiter = self.selection.get_selected()
        if not treeiter: return
        app_data = model[treeiter][2] or {}
        download_link = next((link["url"] for link in app_data.get("links", []) if link.get("type") == "download" and link.get("url")), None)
        if not download_link:
            self.update_status("Fehler: Kein Download-Link gefunden.")
            return
        self.download_button.set_sensitive(False)
        self.progress_bar.set_fraction(0.0)
        self.progress_bar.set_text("0 %")
        self.progress_bar.set_visible(True)
        threading.Thread(target=self.download_worker, args=(app_data, download_link), daemon=True).start()

    def on_download_finished(self, message, success: bool):
        self.update_status(message)
        self.download_button.set_sensitive(True)
        self.progress_bar.set_visible(False)
        if success: self.populate_installed_list()

    def on_quit(self, *_args):
        try:
            self.settings['width'], self.settings['height'] = self.window.get_size()
            self.save_settings()
        finally:
            Gtk.main_quit()

    def on_tab_switched(self, _notebook, _page, page_num):
        if page_num == 1: self.populate_installed_list()

    def on_installed_selection_changed(self, selection):
        is_selected = selection.get_selected()[1] is not None
        self.start_button.set_sensitive(is_selected)
        self.delete_button.set_sensitive(is_selected)
        
    def on_start_clicked(self, _widget):
        model, treeiter = self.installed_selection.get_selected()
        if treeiter:
            try: subprocess.Popen([model[treeiter][1]])
            except Exception as e: self.update_status(f"Fehler beim Starten: {e}")

    def on_delete_clicked(self, _widget):
        model, treeiter = self.installed_selection.get_selected()
        if not treeiter: return
        app_name, appimage_path = model[treeiter]
        if self.confirm_dialog("Löschen", f"Soll '{app_name}' wirklich gelöscht werden?"):
            desktop_file = os.path.join(APP_DIR, f"appimage-{slugify(app_name)}.desktop")
            try:
                if os.path.exists(appimage_path): os.remove(appimage_path)
                if os.path.exists(desktop_file): os.remove(desktop_file)
                self.installed_store.remove(treeiter)
                self.update_status(f"'{app_name}' entfernt.")
            except OSError as e: self.update_status(f"Fehler beim Löschen: {e}")
                
    def on_settings_clicked(self, _widget):
        dialog = Gtk.Dialog(title="Einstellungen", transient_for=self.window, modal=True)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
        grid = Gtk.Grid(column_spacing=10, row_spacing=10, margin=10)
        dialog.get_content_area().add(grid)
        grid.attach(Gtk.Label(label="AppImage-Ordner:"), 0, 0, 1, 1)
        folder_chooser = Gtk.FileChooserButton(title="AppImage-Ordner auswählen", action=Gtk.FileChooserAction.SELECT_FOLDER)
        folder_chooser.set_current_folder(self.settings['appimage_dir'])
        grid.attach(folder_chooser, 1, 0, 1, 1)
        dialog.show_all()
        if dialog.run() == Gtk.ResponseType.OK:
            chosen = folder_chooser.get_filename()
            if chosen: self.settings['appimage_dir'] = chosen
            self.save_settings()
            self.initialize_app_directory()
            self.update_status("Einstellungen gespeichert.")
        dialog.destroy()

    # --- GEÄNDERT: "Über"-Dialog mit Logo ---
    def on_about_clicked(self, _widget):
        dialog = Gtk.AboutDialog(transient_for=self.window, modal=True)
        dialog.set_program_name("Void Community AppImage Helper")
        
        # Versuche, das Logo zu laden
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(LOGO_PATH, 128, 128)
            dialog.set_logo(pixbuf)
        except GLib.Error as e:
            print(f"Warnung: Konnte Logo nicht laden: {e}")
        
        dialog.set_comments(
            "Dieses Werkzeug hilft beim Suchen, Herunterladen und Verwalten von AppImages.\n\n"
            "Entwickelt im Rahmen des Void-Gemeni Projektes."
        )
        dialog.set_copyright(DESIGNER_TEXT)
        dialog.set_website("https://void-linux.org") # Optional: eine Webseite hinzufügen
        
        dialog.run()
        dialog.destroy()

    # --- Hilfsfunktionen ---
    
    def populate_list(self):
        self.list_store.clear()
        for item in self.all_apps_data:
            self.list_store.append([item.get("name", "Unbekannt"), item.get("description", ""), item])
        self.update_status(f"{len(self.all_apps_data)} Anwendungen gefunden.")

    def update_status(self, text: str):
        self.statusbar.pop(self.status_ctx)
        self.statusbar.push(self.status_ctx, text)
        print(f"[Status] {text}")
        
    def populate_installed_list(self):
        self.installed_store.clear()
        if not os.path.isdir(APP_DIR): return
        for filename in os.listdir(APP_DIR):
            if not filename.endswith(".desktop"): continue
            filepath, appimage_path, app_name, is_managed = os.path.join(APP_DIR, filename), "", "", False
            try:
                with open(filepath, 'r', encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if line.strip().startswith("X-AppImage-Path="): appimage_path = line.strip().split("=", 1)[1]
                        elif line.strip().startswith("Name="): app_name = line.strip().split("=", 1)[1]
                        elif line.strip() == "# Managed by VCAH": is_managed = True
            except Exception: continue
            if is_managed and appimage_path and os.path.exists(appimage_path):
                self.installed_store.append([app_name or "(ohne Name)", appimage_path])

    def choose_best_icon_from_item(self, item: dict):
        icons = item.get("icons", [])
        if isinstance(icons, list) and icons:
            by_size = {str(ic.get("sizes", "")).lower(): ic for ic in icons if isinstance(ic, dict)}
            for sz in ICON_SIZES_PREFERRED:
                if sz in by_size and by_size[sz].get("src"): return by_size[sz]["src"]
            if icons[0].get("src"): return icons[0]["src"]
        return None

    def download_icon(self, app_name: str, item: dict) -> str:
        try:
            icon_url = self.choose_best_icon_from_item(item)
            if not icon_url: return ""
            icon_slug = slugify(app_name)
            size_dir = next((sz for sz in ICON_SIZES_PREFERRED if sz in icon_url), "128x128")
            icon_dir = os.path.join(ICON_BASE_DIR, size_dir, "apps")
            ensure_dir(icon_dir)
            ext = os.path.splitext(icon_url)[1].lower() or ".png"
            icon_filename = f"{icon_slug}{ext if ext in ['.png', '.svg'] else '.png'}"
            icon_path = os.path.join(icon_dir, icon_filename)
            with requests.get(icon_url, headers={"User-Agent": "VCAH/2.2"}, stream=True, timeout=30) as r:
                r.raise_for_status()
                with open(icon_path, "wb") as f:
                    for chunk in r.iter_content(8192): f.write(chunk)
            return os.path.splitext(icon_filename)[0]
        except Exception: return ""

    def create_desktop_file(self, app_data, appimage_path, icon_name: str = ""):
        app_name = app_data.get("name", "AppImage")
        desktop_content = (f"[Desktop Entry]\nVersion=1.0\nName={app_name}\n"
                           f'Exec="{appimage_path}" %U\nIcon={icon_name or slugify(app_name)}\n'
                           f"Type=Application\nTerminal=false\n"
                           f"Categories={';'.join(app_data.get('categories', ['Utility']))};\n"
                           f"X-AppImage-Path={appimage_path}\n# Managed by VCAH\n")
        try:
            with open(os.path.join(APP_DIR, f"appimage-{slugify(app_name)}.desktop"), 'w', encoding="utf-8") as f:
                f.write(desktop_content)
        except Exception as e: self.update_status(f"Fehler bei .desktop-Datei: {e}")

    def cleanup_orphans(self, _widget=None):
        if not os.path.isdir(APP_DIR): return
        orphans = []
        for filename in os.listdir(APP_DIR):
            if not filename.endswith(".desktop"): continue
            filepath, appimage_path, is_managed = os.path.join(APP_DIR, filename), None, False
            try:
                with open(filepath, 'r', encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if line.strip().startswith("X-AppImage-Path="): appimage_path = line.strip().split("=", 1)[1]
                        elif line.strip() == "# Managed by VCAH": is_managed = True
            except Exception: continue
            if is_managed and appimage_path and not os.path.exists(appimage_path):
                orphans.append(filepath)
        if not orphans: self.info_dialog("Bereinigung", "Keine verwaisten Einträge gefunden."); return
        if self.confirm_dialog("Bereinigung", f"{len(orphans)} verwaiste Einträge gefunden. Löschen?"):
            removed = sum(1 for path in orphans if self.try_remove(path))
            self.info_dialog("Bereinigung", f"{removed} Einträge gelöscht.")

    def try_remove(self, path):
        try: os.remove(path); return True
        except Exception: return False

    def load_settings(self):
        defaults = {"width": 1000, "height": 660, "opacity": 0.97, "appimage_dir": os.path.join(os.path.expanduser("~"), "AppImages")}
        try:
            with open(CONFIG_FILE, 'r') as f: self.settings = json.load(f)
            self.settings = {**defaults, **self.settings}
        except (FileNotFoundError, json.JSONDecodeError): self.settings = defaults

    def save_settings(self):
        try:
            ensure_dir(CONFIG_DIR)
            with open(CONFIG_FILE, 'w') as f: json.dump(self.settings, f, indent=4)
        except IOError as e: self.update_status(f"Einstellungen konnten nicht gespeichert werden: {e}")

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

    def info_dialog(self, title, text):
        dialog = Gtk.MessageDialog(transient_for=self.window, modal=True, message_type=Gtk.MessageType.INFO, buttons=Gtk.ButtonsType.OK, text=title)
        dialog.format_secondary_text(text)
        dialog.run(); dialog.destroy()

    def confirm_dialog(self, title, text) -> bool:
        dialog = Gtk.MessageDialog(transient_for=self.window, modal=True, message_type=Gtk.MessageType.QUESTION, buttons=Gtk.ButtonsType.YES_NO, text=title)
        dialog.format_secondary_text(text)
        resp = dialog.run()
        dialog.destroy()
        return resp == Gtk.ResponseType.YES

if __name__ == "__main__":
    app = AppImageManager()
    app.window.show_all()
    Gtk.main()
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
