#!/bin/bash

# Void Community AppImage Helper — УНИВЕРСАЛЬНЫЙ ИСПРАВЛЕННЫЙ УСТАНОВЩИК
# Автор: Pinguin-TV (исправления: твой братик 🐧)
# Работает на Void, Ubuntu, Fedora, Arch и др.

APP_NAME="appimages"
APP_DEST_DIR="/usr/local/bin/$APP_NAME"
APP_LAUNCHER="/usr/local/bin/${APP_NAME}-helper"
DESKTOP_FILE="applications/${APP_NAME}.desktop"
DESKTOP_DEST="/usr/share/applications/${APP_NAME}.desktop"

# Источник — текущая папка (где лежит appimages.py)
APP_SRC_DIR="$PWD"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}>> $1${NC}"; }
error() { echo -e "${RED}FEHLER: $1${NC}" >&2; exit 1; }
warn() { echo -e "${YELLOW}WARNUNG: $1${NC}" >&2; }

# -----------------------------
# Универсальная установка зависимостей
# -----------------------------
install_dependencies() {
  log "Проверка и установка зависимостей..."

  if command -v xbps-install >/dev/null 2>&1; then
    # Void Linux
    log "Обнаружен Void Linux"
    local pkgs=("python3" "python3-requests" "python3-gobject" "gtk+3" "desktop-file-utils" "hicolor-icon-theme" "adwaita-icon-theme")
    local missing=()
    for p in "${pkgs[@]}"; do
      if ! xbps-query -i "$p" >/dev/null 2>&1; then missing+=("$p"); fi
    done
    [[ ${#missing[@]} -gt 0 ]] && xbps-install -Sy "${missing[@]}" || log "Все зависимости установлены."

  elif command -v apt >/dev/null 2>&1; then
    # Debian/Ubuntu/Mint
    log "Обнаружен Debian/Ubuntu"
    apt update
    apt install -y python3 python3-gi python3-requests gir1.2-gtk-3.0 desktop-file-utils hicolor-icon-theme adwaita-icon-theme

  elif command -v dnf >/dev/null 2>&1; then
    # Fedora
    log "Обнаружен Fedora"
    dnf install -y python3 python3-gobject python3-requests gtk3 desktop-file-utils hicolor-icon-theme

  elif command -v pacman >/dev/null 2>&1; then
    # Arch/Manjaro
    log "Обнаружен Arch Linux"
    pacman -Sy --noconfirm python python-gobject python-requests gtk3 desktop-file-utils hicolor-icon-theme

  else
    warn "Не удалось определить пакетный менеджер. Убедитесь, что установлены: python3, gtk3, pygobject, requests"
  fi
}

# -----------------------------
# Основная установка
# -----------------------------
main() {
  log "Создание целевой директории: $APP_DEST_DIR"
  install -d -m 0755 "$APP_DEST_DIR" || error "Не удалось создать директорию"

  # Проверка основного файла
  [[ ! -f "${APP_SRC_DIR}/appimages.py" ]] && error "appimages.py не найден! Запускайте из правильной папки."

  # Копирование файлов
  log "Копирование appimages.py..."
  install -m 0755 "${APP_SRC_DIR}/appimages.py" "${APP_DEST_DIR}/" || error "Ошибка копирования appimages.py"

  log "Копирование icons и applications..."
  cp -r "${APP_SRC_DIR}/icons" "$APP_DEST_DIR/" || error "Ошибка копирования icons"
  cp -r "${APP_SRC_DIR}/applications" "$APP_DEST_DIR/" || error "Ошибка копирования applications"

  # Создание лаунчера
  log "Создание лаунчера: $APP_LAUNCHER"
  cat > "$APP_LAUNCHER" << 'EOF'
#!/bin/bash
exec python3 /usr/local/bin/appimages/appimages.py "$@"
EOF
  chmod +x "$APP_LAUNCHER" || error "Не удалось сделать лаунчер исполняемым"

  # Копирование .desktop файла
  log "Установка .desktop файла: $DESKTOP_DEST"
  install -D -m 0644 "$DESKTOP_FILE" "$DESKTOP_DEST" || error "Ошибка установки .desktop файла"

  # Обновление кэшей
  log "Обновление кэшей..."
  update-desktop-database &>/dev/null || warn "Не удалось обновить desktop-кэш"
  gtk-update-icon-cache -f /usr/share/icons/hicolor &>/dev/null || true

  log "✅ Установка завершена!"
  log "Запуск: ${YELLOW}appimages-helper${NC}"
  log "Или найдите в меню: ${YELLOW}Void Community AppImage Helper${NC}"
}

# -----------------------------
# Запуск
# -----------------------------

[[ $EUID -ne 0 ]] && error "Запустите через sudo"

install_dependencies
main
