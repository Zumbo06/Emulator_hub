import sys
import os
import subprocess
import json
import shutil
from pathlib import Path
import hashlib
import re
import shlex
import time
from datetime import timedelta

# Optional dependency
try:
    import psutil
except ImportError:
    psutil = None

# --- PyQt6 Imports ---
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QListWidget, QStatusBar, QListWidgetItem, QPushButton, QMessageBox,
    QFileDialog, QLabel, QDialog, QLineEdit, QDialogButtonBox,
    QSplitter, QTabWidget, QMenu, QStyle, QStyledItemDelegate, QSlider, QComboBox,
    QTreeWidget, QTreeWidgetItem, QHeaderView, QCheckBox, QFormLayout, QGroupBox,
    QSizePolicy
)
from PyQt6.QtGui import QFont, QIcon, QPixmap, QAction, QPainter, QColor, QBrush, QPen, QFontDatabase, QPainterPath
from PyQt6.QtCore import Qt, QSize, QStandardPaths, QRect, QTimer, QByteArray, pyqtSignal, QThread

# =============================================================================
# --- APPLICATION CONSTANTS & UTILITIES ---
# =============================================================================

class Constants:
    C_BACKGROUND_DARK = "#2D2D30"; C_BACKGROUND_LIGHT = "#3F3F46"; C_BACKGROUND_WIDGET = "#1E1E1E"
    C_BORDER = "#555555"; C_TEXT_PRIMARY = "#F1F1F1"; C_TEXT_SECONDARY = "#CCCCCC"
    C_HIGHLIGHT_BLUE = "#007ACC"; C_HIGHLIGHT_CYAN = "#00BFFF"
    ALL_GAMES_CATEGORY = "All Games"; FAVORITES_CATEGORY = "Favorites"; RECENTS_CATEGORY = "Recently Played"
    DEFAULT_GRID_ICON_SIZE = 150; MIN_GRID_ICON_SIZE = 100; MAX_GRID_ICON_SIZE = 300
    DEFAULT_LIST_ICON_SIZE = 48;  MIN_LIST_ICON_SIZE = 32;  MAX_LIST_ICON_SIZE = 96

def format_size(size_bytes):
    if size_bytes == 0: return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB"); i = 0
    while size_bytes >= 1024 and i < len(size_name) - 1:
        size_bytes /= 1024.0; i += 1
    return f"{size_bytes:.2f} {size_name[i]}"

def format_playtime(seconds):
    if seconds == 0: return "Never Played"
    return str(timedelta(seconds=int(seconds)))

# =============================================================================
# --- BACKGROUND WORKER THREADS ---
# =============================================================================

class GameScanner(QThread):
    progress_update = pyqtSignal(str)
    scan_finished = pyqtSignal(dict, dict)

    def __init__(self, backend):
        super().__init__()
        self.backend = backend

    def run(self):
        games_by_platform = {}
        all_games_map = {}
        self.progress_update.emit("Starting library scan...")
        game_paths = []
        for lib_path in self.backend.config_manager.config["game_library_paths"]:
            for root, dirs, files in os.walk(lib_path, topdown=True):
                game_paths.extend([os.path.join(root, f) for f in files])
                game_paths.extend([os.path.join(root, d) for d in dirs])
        
        total_items = len(game_paths)
        processed_items = 0

        for lib_path in self.backend.config_manager.config["game_library_paths"]:
            for root, dirs, files in os.walk(lib_path, topdown=True):
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                current_dirs = dirs[:]
                for dir_name in current_dirs:
                    processed_items += 1
                    self.progress_update.emit(f"Scanning... ({processed_items}/{total_items})")
                    if os.path.isdir(os.path.join(root, dir_name, 'PS3_GAME')):
                        self._add_game("PlayStation 3", dir_name, os.path.join(root, dir_name), games_by_platform, all_games_map)
                        dirs.remove(dir_name)
                for file_name in files:
                    processed_items += 1
                    self.progress_update.emit(f"Scanning... ({processed_items}/{total_items})")
                    platform = self.backend.get_platform_from_path(root) or self.backend.GAME_EXTENSIONS.get(Path(file_name).suffix.lower())
                    if platform:
                        self._add_game(platform, file_name, os.path.join(root, file_name), games_by_platform, all_games_map)
        self.scan_finished.emit(games_by_platform, all_games_map)

    def _add_game(self, platform, title_source, path, games_by_platform, all_games_map):
        if platform == "Game Boy Color":
            platform = "Game Boy"
        if platform not in games_by_platform: games_by_platform[platform] = []
        path_hash = hashlib.md5(str(Path(path).resolve()).encode()).hexdigest()
        if path_hash not in all_games_map:
            clean_title = self.backend._clean_game_title(title_source)
            try:
                size = (sum(f.stat().st_size for f in Path(path).glob('**/*') if f.is_file())) if os.path.isdir(path) else os.path.getsize(path)
            except FileNotFoundError: size = 0
            metadata = self.backend.config_manager.config.get("game_metadata", {}).get(path_hash, {})
            game_data = {"title": clean_title, "path": path, "hash": path_hash, "size": size, "platform": platform, **metadata}
            games_by_platform[platform].append(game_data)
            all_games_map[path_hash] = game_data

# =============================================================================
# --- CUSTOM UI DELEGATES ---
# =============================================================================

class GridItemDelegate(QStyledItemDelegate):
    def __init__(self, backend, parent=None):
        super().__init__(parent); self.backend = backend; self.TEXT_PADDING = 5
        self.TEXT_AREA_HEIGHT = 40; self.FAVORITE_STAR = QPixmap(":/qt-project.org/styles/commonstyle/images/star-on-16.png")
    def sizeHint(self, option, index):
        icon_size = option.decorationSize; return QSize(icon_size.width(), icon_size.height() + self.TEXT_AREA_HEIGHT)
    def paint(self, painter, option, index):
        rect = option.rect; game_data = index.data(Qt.ItemDataRole.UserRole)
        colors = self.parent().window().themes[self.parent().window().current_theme_name]
        if option.state & QStyle.StateFlag.State_Selected:
            painter.save(); pen = QPen(QColor(colors['C_HIGHLIGHT_CYAN'])); pen.setWidth(2)
            painter.setPen(pen); painter.setBrush(Qt.BrushStyle.NoBrush); painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 4, 4); painter.restore()
        icon_area = QRect(rect.x(), rect.y(), rect.width(), rect.height() - self.TEXT_AREA_HEIGHT); icon = index.data(Qt.ItemDataRole.DecorationRole)
        if isinstance(icon, QIcon):
            pixmap = icon.pixmap(icon_area.size()); x = icon_area.x() + (icon_area.width() - pixmap.width()) // 2
            y = icon_area.y() + (icon_area.height() - pixmap.height()) // 2; painter.drawPixmap(x, y, pixmap)
        if self.backend.is_favorite(game_data['hash']): painter.drawPixmap(rect.x() + 5, rect.y() + 5, self.FAVORITE_STAR)
        text_area = QRect(rect.x() + self.TEXT_PADDING, icon_area.bottom(), rect.width() - 2 * self.TEXT_PADDING, self.TEXT_AREA_HEIGHT)
        text = index.data(Qt.ItemDataRole.DisplayRole); painter.setPen(option.palette.color(option.palette.ColorRole.Text))
        painter.drawText(text_area, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, text)

class SpacedListItemDelegate(QStyledItemDelegate):
    def __init__(self, spacing=8, parent=None): super().__init__(parent); self.spacing = spacing
    def sizeHint(self, option, index):
        size = super().sizeHint(option, index); icon_height = option.decorationSize.height()
        size.setHeight(max(size.height(), icon_height) + self.spacing); return size

# =============================================================================
# --- CONFIGURATION MANAGER ---
# =============================================================================
class ConfigManager:
    def __init__(self):
        config_dir = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)) / "EmulatorHub"
        self.covers_dir = config_dir / "covers"; self.cache_dir = self.covers_dir / "cache"
        config_dir.mkdir(parents=True, exist_ok=True); self.covers_dir.mkdir(exist_ok=True)
        self.cache_dir.mkdir(exist_ok=True)
        self.config_path = config_dir / "config.json"
        self.config = {
            "game_library_paths": [], "emulators": {}, "custom_covers": {},
            "game_metadata": {}, "theme": "Modern Dark", "view_mode": "grid",
            "grid_icon_size": 150, "list_icon_size": 48, "favorites": [],
            "recently_played": [], "window_geometry": "", "window_state": "",
            "splitter_state": "", "sort_order": "Name", "platform_defaults": {},
            "details_panel_visible": True
        }
        self.load_config()
    def load_config(self):
        if self.config_path.exists():
            with open(self.config_path, 'r') as f: self.config.update(json.load(f))
    def save_config(self):
        with open(self.config_path, 'w') as f: json.dump(self.config, f, indent=4)

# =============================================================================
# --- BACKEND LOGIC ---
# =============================================================================
class EmulatorHubBackend:
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager; self.games_by_platform = {}; self.all_games_map = {}
        self.cache_path = self.config_manager.covers_dir.parent / "game_cache.json"
        self.PLATFORM_FOLDER_MAP = {"gamecube": "GameCube", "gc": "GameCube", "wii": "Wii", "playstation 2": "PlayStation 2", "ps2": "PlayStation 2", "playstation 3": "PlayStation 3", "ps3": "PlayStation 3", "nintendo switch": "Nintendo Switch", "switch": "Nintendo Switch", "playstation": "PlayStation", "psx": "PlayStation", "ps1": "PlayStation", "psp": "PSP", "playstation portable": "PSP", "xbox": "Xbox", "xbox 360": "Xbox 360", "x360": "Xbox 360", "nintendo 3ds": "Nintendo 3DS", "3ds": "Nintendo 3DS", "nintendo ds": "Nintendo DS", "ds": "Nintendo DS", "dreamcast": "Dreamcast", "dc": "Dreamcast", "super nintendo": "Super Nintendo", "snes": "Super Nintendo", "sega genesis": "Sega Genesis", "genesis": "Sega Genesis", "mega drive": "Sega Genesis", "turbografx-16": "TurboGrafx-16", "pc engine": "TurboGrafx-16", "game boy": "Game Boy", "gb": "Game Boy", "game boy color": "Game Boy Color", "gbc": "Game Boy Color", "game boy advance": "Game Boy Advance", "gba": "Game Boy Advance", "sega game gear": "Sega Game Gear", "gg": "Sega Game Gear", "atari lynx": "Atari Lynx", "lynx": "Atari Lynx"}
        self.GAME_EXTENSIONS = {
            ".iso": "PlayStation 2", 
            ".pkg": "PlayStation 3",
            ".xiso.iso": "Xbox", 
            ".gcz": "GameCube", 
            ".rvz": "GameCube", 
            ".wbfs": "Wii", 
            ".xci": "Nintendo Switch", 
            ".nsp": "Nintendo Switch", 
            ".chd": "PlayStation", 
            ".cue": "PlayStation", 
            ".bin": "PlayStation", 
            ".cso": "PSP", 
            ".3ds": "Nintendo 3DS", 
            ".cci": "Nintendo 3DS", 
            ".nds": "Nintendo DS", 
            ".gdi": "Dreamcast", 
            ".cdi": "Dreamcast",
            ".z64": "Nintendo 64",
            ".sfc": "Super Nintendo",
            ".smc": "Super Nintendo",
            ".md": "Sega Genesis",
            ".smd": "Sega Genesis",
            ".gen": "Sega Genesis",
            ".pce": "TurboGrafx-16",
            ".gb": "Game Boy",
            ".gbc": "Game Boy Color",
            ".gba": "Game Boy Advance",
            ".gg": "Sega Game Gear",
            ".lnx": "Atari Lynx"
        }
        self.KNOWN_EMULATORS = {
            # Handhelds
            "mGBA": {"executables": ["mgba"], "systems": ["Game Boy", "Game Boy Color", "Game Boy Advance"]},
            "VisualBoyAdvance-M": {"executables": ["visualboyadvance-m", "vbam"], "systems": ["Game Boy", "Game Boy Color", "Game Boy Advance"]},
            "SameBoy": {"executables": ["sameboy"], "systems": ["Game Boy", "Game Boy Color"]},
            # 4th Generation
            "Snes9x": {"executables": ["snes9x"], "systems": ["Super Nintendo"]},
            "Mesen": {"executables": ["mesen"], "systems": ["Super Nintendo"]},
            "Kega Fusion": {"executables": ["fusion"], "systems": ["Sega Genesis", "Sega Game Gear"]},
            "BlastEm": {"executables": ["blastem"], "systems": ["Sega Genesis"]},
            # 6th Generation
            "Dolphin": {"executables": ["dolphin"], "systems": ["GameCube", "Wii"]}, 
            "PCSX2": {"executables": ["pcsx2", "pcsx2-qt"], "systems": ["PlayStation 2"]}, 
            "Xemu": {"executables": ["xemu"], "systems": ["Xbox"]},
            "Redream": {"executables": ["redream"], "systems": ["Dreamcast"]},
            "Flycast": {"executables": ["flycast"], "systems": ["Dreamcast"]},
            
            # 5th Generation
            "DuckStation": {"executables": ["duckstation-qt", "duckstation-nogui"], "systems": ["PlayStation"]}, 
            "Project64": {"executables": ["project64"], "systems": ["Nintendo 64"]},
            "simple64": {"executables": ["simple64-gui", "simple64-cli"], "systems": ["Nintendo 64"]},
            "Mednafen": {"executables": ["mednafen"], "systems": ["PlayStation", "Sega Saturn", "Super Nintendo", "Sega Genesis", "TurboGrafx-16", "Atari Lynx"]},
            "YabaSanshiro": {"executables": ["yabasanshiro"], "systems": ["Sega Saturn"]},
            "Kronos": {"executables": ["kronos"], "systems": ["Sega Saturn"]},
            
            # Other Previously Added Emulators
            "RPCS3": {"executables": ["rpcs3"], "systems": ["PlayStation 3"]}, 
            "Xenia": {"executables": ["xenia"], "systems": ["Xbox 360"]}
        }

    def load_from_cache(self):
        if not self.cache_path.exists():
            return False
        try:
            with open(self.cache_path, 'r') as f:
                cached_data = json.load(f)
            self.all_games_map = cached_data
            self.games_by_platform.clear()
            for game in self.all_games_map.values():
                platform = game['platform']
                if platform not in self.games_by_platform:
                    self.games_by_platform[platform] = []
                self.games_by_platform[platform].append(game)
            return True
        except (json.JSONDecodeError, KeyError):
            self.clear_cache()
            return False

    def save_to_cache(self):
        with open(self.cache_path, 'w') as f:
            json.dump(self.all_games_map, f)

    def clear_cache(self):
        if self.cache_path.exists():
            self.cache_path.unlink()

    def set_custom_game_image(self, game_hash, image_path):
        try:
            from PIL import Image
        except ImportError:
            return False, "Pillow library is required. Please run: pip install Pillow"
        source_path = Path(image_path)
        if source_path.suffix.lower() not in ['.png', '.jpg', '.jpeg', '.webp']:
             return False, "Unsupported image format."
        try:
            new_name = f"{game_hash}{source_path.suffix}"; dest_path = self.config_manager.covers_dir / new_name
            shutil.copy(source_path, dest_path); thumb_path = self.config_manager.cache_dir / new_name
            with Image.open(dest_path) as img:
                img.thumbnail((300, 300)); img.save(thumb_path, quality=85)
            self.config_manager.config["custom_covers"][game_hash] = new_name; self.config_manager.save_config()
            return True, "Set new custom cover image."
        except Exception as e:
            return False, f"Could not save image cover: {e}"
            
    def _clean_game_title(self, filename):
        title = Path(filename).stem; title = re.sub(r'\.xiso$', '', title, flags=re.IGNORECASE)
        title = re.sub(r'\[.*?\]', '', title); title = re.sub(r'\(.*?\)', '', title)
        title = title.replace('.', ' ').replace('_', ' '); return title.strip()
    def launch_game(self, game_hash, chosen_emulator_config):
        game_data = self.all_games_map.get(game_hash);
        if not game_data: return None, "Game data not found."
        emulator_path = chosen_emulator_config['path']; launch_args = chosen_emulator_config.get('args', '')
        path_to_launch = self._get_launchable_path(game_data)
        if not path_to_launch: return None, "Could not determine a launchable file for this game."
        command = self._build_launch_command(emulator_path, launch_args, path_to_launch)
        try:
            process = subprocess.Popen(command); self.add_to_recently_played(game_data['hash']); return process, f"Launching {game_data['title']}..."
        except Exception as e:
            return None, f"Failed to start emulator: {e}"
    def _get_launchable_path(self, game_data):
        if game_data['platform'] == "PlayStation 3":
            path_obj = Path(game_data['path'])
            if path_obj.is_dir():
                eboot_path = path_obj / 'PS3_GAME' / 'USRDIR' / 'EBOOT.BIN'
                if eboot_path.exists():
                    return str(eboot_path)
                if (path_obj / 'PS3_GAME').exists():
                    return str(path_obj)
                return None
        return game_data['path']
    def _build_launch_command(self, emulator_path, args_str, game_path):
        norm_emulator_path = os.path.normpath(emulator_path); norm_game_path = os.path.normpath(game_path)
        command = [norm_emulator_path]
        if args_str:
            if '%ROM%' in args_str:
                full_args_str = args_str.replace('%ROM%', f'"{norm_game_path}"'); command.extend(shlex.split(full_args_str))
            else:
                command.extend(shlex.split(args_str)); command.append(norm_game_path)
        else:
            command.append(norm_game_path)
        return command
    def is_favorite(self, game_hash): return game_hash in self.config_manager.config['favorites']
    def toggle_favorite(self, game_hash):
        favorites = self.config_manager.config['favorites']
        if game_hash in favorites: favorites.remove(game_hash)
        else: favorites.append(game_hash)
        self.config_manager.save_config()
    def add_to_recently_played(self, game_hash):
        recents = self.config_manager.config.get('recently_played', [])
        if game_hash in recents: recents.remove(game_hash)
        recents.insert(0, game_hash); self.config_manager.config['recently_played'] = recents[:20]; self.config_manager.save_config()
    def get_favorite_games(self): return [self.all_games_map[h] for h in self.config_manager.config['favorites'] if h in self.all_games_map]
    def get_recently_played_games(self): return [self.all_games_map[h] for h in self.config_manager.config['recently_played'] if h in self.all_games_map]
    def get_emulators_for_system(self, system: str) -> list:
        found_emulators = [];
        for name, data in self.config_manager.config["emulators"].items():
            if system.lower() in [s.lower() for s in data.get("systems", [])]: found_emulators.append({"name": name, "config": data})
        return found_emulators

    # --- FIX: New, simpler, name-only detection logic ---
    def detect_emulator_from_exe(self, exe_path):
        """Detects an emulator by checking if known names are part of the exe filename."""
        selected_exe_name = Path(exe_path).name.lower()

        for emu_name, emu_data in self.KNOWN_EMULATORS.items():
            for known_exe in emu_data["executables"]:
                # Check if a known name (e.g., "dolphin") is in the filename ("Dolphin-x64.exe")
                if known_exe in selected_exe_name:
                    return {
                        "name": f"[Auto] {emu_name}", 
                        "data": {
                            "path": exe_path, 
                            "systems": emu_data["systems"], 
                            "args": emu_data.get("default_args", "")
                        }
                    }
        return None
        
    def get_platform_from_path(self, path):
        p = Path(path);
        while p.parent != p:
            platform = self.PLATFORM_FOLDER_MAP.get(p.name.lower());
            if platform: return platform
            p = p.parent
        return None

# =============================================================================
# --- UI DIALOGS ---
# =============================================================================
class EmulatorEditDialog(QDialog):
    def __init__(self, emu_name="", emu_data=None, parent=None):
        super().__init__(parent); self.setWindowTitle("Add/Edit Emulator")
        emu_data = emu_data or {"path": "", "systems": [], "args": ""}; layout = QVBoxLayout(self); layout.addWidget(QLabel("Emulator Name:")); self.name_edit = QLineEdit(emu_name); layout.addWidget(self.name_edit)
        layout.addWidget(QLabel("Executable Path:")); path_layout = QHBoxLayout(); self.path_edit = QLineEdit(emu_data["path"]); btn_browse = QPushButton("Browse..."); btn_browse.clicked.connect(self.browse_for_exe); path_layout.addWidget(self.path_edit); path_layout.addWidget(btn_browse); layout.addLayout(path_layout)
        layout.addWidget(QLabel("Supported Systems (comma-separated):")); self.systems_edit = QLineEdit(", ".join(emu_data.get("systems", []))); layout.addWidget(self.systems_edit)
        layout.addWidget(QLabel("Launch Arguments (use %ROM% for game path):")); self.args_edit = QLineEdit(emu_data.get("args", "")); layout.addWidget(self.args_edit)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel); buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); layout.addWidget(buttons)
    def browse_for_exe(self): path, _ = QFileDialog.getOpenFileName(self, "Select Executable"); self.path_edit.setText(path) if path else None
    def get_data(self): return {"name": self.name_edit.text().strip(), "data": {"path": self.path_edit.text().strip(), "systems": [s.strip() for s in self.systems_edit.text().split(",") if s.strip()], "args": self.args_edit.text().strip()}}

class GameInfoDialog(QDialog):
    def __init__(self, info, parent=None):
        super().__init__(parent); self.setWindowTitle(info.get('title', 'Game Info')); self.setMinimumSize(400, 150); layout = QVBoxLayout(self)
        for key, title in [("title", "Title:"), ("platform", "Platform:"), ("size", "Size:"), ("playtime", "Time Played:")]:
            layout.addWidget(QLabel(f"<b>{title}</b> {info.get(key, 'N/A')}"))
        layout.addStretch(); close_btn = QPushButton("Close"); close_btn.clicked.connect(self.accept); layout.addWidget(close_btn, 0, Qt.AlignmentFlag.AlignRight)

class EmulatorChoiceDialog(QDialog):
    def __init__(self, emulators, platform_name, parent=None):
        super().__init__(parent); self.setWindowTitle("Choose Emulator")
        layout = QVBoxLayout(self); layout.addWidget(QLabel("Multiple emulators found. Please choose one:"))
        self.list_widget = QListWidget()
        for emu_name in emulators:
            self.list_widget.addItem(emu_name)
        self.list_widget.setCurrentRow(0); layout.addWidget(self.list_widget)
        self.set_default_checkbox = QCheckBox(f"Always use this choice for {platform_name}")
        layout.addWidget(self.set_default_checkbox)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); layout.addWidget(buttons)
    
    def get_selected_emulator_name(self):
        return self.list_widget.currentItem().text() if self.list_widget.currentItem() else None

    def get_set_as_default(self):
        return self.set_default_checkbox.isChecked()

class LibraryManagerDialog(QDialog):
    def __init__(self, config_manager, parent=None):
        super().__init__(parent); self.config_manager = config_manager; self.setWindowTitle("Manage Game Folders"); self.setMinimumSize(600, 400)
        layout = QVBoxLayout(self); layout.addWidget(QLabel("Game Library Folders:"))
        self.path_list = QListWidget(); self.populate_list(); layout.addWidget(self.path_list)
        button_layout = QHBoxLayout(); btn_add = QPushButton("Add Folder..."); btn_add.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder))
        self.btn_remove = QPushButton("Remove Selected"); self.btn_remove.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
        btn_add.clicked.connect(self.add_path); self.btn_remove.clicked.connect(self.remove_path)
        button_layout.addStretch(); button_layout.addWidget(btn_add); button_layout.addWidget(self.btn_remove); layout.addLayout(button_layout)
        self.path_list.currentItemChanged.connect(lambda item: self.btn_remove.setEnabled(item is not None)); self.btn_remove.setEnabled(False)
    def populate_list(self):
        self.path_list.clear(); self.path_list.addItems(self.config_manager.config["game_library_paths"])
    def add_path(self):
        path = QFileDialog.getExistingDirectory(self, "Select Game Folder")
        if path and path not in self.config_manager.config["game_library_paths"]:
            self.config_manager.config["game_library_paths"].append(path); self.config_manager.save_config(); self.populate_list()
    def remove_path(self):
        selected_item = self.path_list.currentItem()
        if not selected_item: return
        path_to_remove = selected_item.text()
        if QMessageBox.question(self, "Confirm Removal", f"Are you sure you want to remove this folder from the library?\n\n{path_to_remove}") == QMessageBox.StandardButton.Yes:
            self.config_manager.config["game_library_paths"].remove(path_to_remove); self.config_manager.save_config(); self.populate_list()

# =============================================================================
# --- MAIN APPLICATION WINDOW ---
# =============================================================================
class EmulatorHubWindow(QMainWindow):
    def __init__(self, backend, config_manager):
        super().__init__()
        self.backend = backend; self.config_manager = config_manager
        self.themes = {
            "Modern Dark": {"C_BACKGROUND_DARK": "#2D2D30", "C_BACKGROUND_LIGHT": "#3F3F46", "C_BACKGROUND_WIDGET": "#1E1E1E", "C_BORDER": "#555555", "C_TEXT_PRIMARY": "#F1F1F1", "C_TEXT_SECONDARY": "#CCCCCC", "C_HIGHLIGHT_BLUE": "#007ACC", "C_HIGHLIGHT_CYAN": "#00BFFF"},
            "Modern Light": {"C_BACKGROUND_DARK": "#F0F0F0", "C_BACKGROUND_LIGHT": "#E1E1E1", "C_BACKGROUND_WIDGET": "#FFFFFF", "C_BORDER": "#C0C0C0", "C_TEXT_PRIMARY": "#000000", "C_TEXT_SECONDARY": "#404040", "C_HIGHLIGHT_BLUE": "#0078D7", "C_HIGHLIGHT_CYAN": "#3399FF"}
        }
        self.current_theme_name = self.config_manager.config.get("theme", "Modern Dark")
        self.is_grid_mode = self.config_manager.config.get("view_mode", "grid") == "grid"
        self.current_grid_icon_size = self.config_manager.config.get("grid_icon_size", 150)
        self.current_list_icon_size = self.config_manager.config.get("list_icon_size", 48)
        self.grid_delegate = GridItemDelegate(self.backend, self); self.list_delegate = SpacedListItemDelegate(parent=self)
        self.setWindowTitle("EmulatorHub"); self.setGeometry(100, 100, 1280, 800)
        self.process_timers = {}
        self.scanner_thread = None

        self.search_debounce_timer = QTimer(self)
        self.search_debounce_timer.setSingleShot(True)
        self.search_debounce_timer.setInterval(300)
        self.search_debounce_timer.timeout.connect(self.repopulate_games_list)

        self.setAcceptDrops(True)
        
        self.setup_ui()
        self.apply_theme()
        self.restore_window_state()
        QTimer.singleShot(50, self.initial_load)
        
    def setup_ui(self):
        self.create_toolbar(); central_widget = QWidget(); self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget); self.tabs = QTabWidget(); main_layout.addWidget(self.tabs)
        self.library_tab = self._create_library_tab(); self.emulators_tab = self._create_emulators_tab()
        self.tabs.addTab(self.library_tab, "Library"); self.tabs.addTab(self.emulators_tab, "Emulators")
        self.setStatusBar(QStatusBar(self))

    def create_toolbar(self):
        toolbar = self.addToolBar("Main")
        toolbar.setObjectName("MainToolBar")
        toolbar.setMovable(False)
        manage_folder_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon), "Manage Game Folders...", self)
        manage_folder_action.triggered.connect(self.open_library_manager); toolbar.addAction(manage_folder_action)
        toolbar.addSeparator()
        self.refresh_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload), "Refresh Library", self)
        self.refresh_action.triggered.connect(self.start_full_scan); toolbar.addAction(self.refresh_action)
        toolbar.addSeparator()
        self.theme_toggle_action = QAction(self.create_theme_icon(), "Toggle Theme", self)
        self.theme_toggle_action.triggered.connect(self.toggle_theme); toolbar.addAction(self.theme_toggle_action)
        toolbar.addSeparator()
        self.toggle_details_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView), "Toggle Details Panel", self)
        self.toggle_details_action.setCheckable(True)
        self.toggle_details_action.toggled.connect(self.on_toggle_details_panel)
        toolbar.addAction(self.toggle_details_action)

    def _create_library_tab(self):
        library_widget = QWidget(); layout = QHBoxLayout(library_widget)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.systems_list = QListWidget()
        self.systems_list.currentItemChanged.connect(self.repopulate_games_list)
        self.main_splitter.addWidget(self.systems_list)
        
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0,0,0,0)
        
        self.games_list = QListWidget()
        self._setup_common_list_properties()
        right_layout.addLayout(self._create_view_options_bar())
        right_layout.addWidget(self.games_list)
        
        # ++++++++++++++ THE FIX IS HERE ++++++++++++++
        # 1. Create the details panel and assign it to the instance variable.
        self.details_panel = self._create_details_panel()
        # 2. Add the created panel to the layout.
        right_layout.addWidget(self.details_panel)
        # 3. NOW that self.details_panel exists, we can safely call a method that uses it.
        self.update_details_panel(None)

        self.main_splitter.addWidget(right_panel)
        self.main_splitter.setSizes([250, 1030])
        layout.addWidget(self.main_splitter)
        return library_widget
    def _create_view_options_bar(self):
        layout = QHBoxLayout()
        self.btn_list_view = QPushButton(self.create_view_switcher_icon('list'), ""); self.btn_list_view.setCheckable(True)
        self.btn_grid_view = QPushButton(self.create_view_switcher_icon('grid'), ""); self.btn_grid_view.setCheckable(True)
        self.btn_list_view.clicked.connect(lambda: self.set_view_mode(False)); self.btn_grid_view.clicked.connect(lambda: self.set_view_mode(True))
        layout.addWidget(self.btn_list_view); layout.addWidget(self.btn_grid_view)
        layout.addWidget(QLabel("Icon Size:"))
        self.icon_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.icon_size_slider.valueChanged.connect(self.on_icon_size_changed)
        layout.addWidget(self.icon_size_slider); layout.addStretch()
        layout.addWidget(QLabel("Sort:"))
        self.sort_combo = QComboBox(); self.sort_combo.addItems(["Name", "File Size (Asc)", "File Size (Desc)", "Time Played"])
        self.sort_combo.setCurrentText(self.config_manager.config.get("sort_order", "Name"))
        self.sort_combo.currentTextChanged.connect(self.on_sort_order_changed)
        layout.addWidget(self.sort_combo)
        self.search_bar = QLineEdit(); self.search_bar.setPlaceholderText("Search...");
        self.search_bar.textChanged.connect(self.on_search_text_changed)
        layout.addWidget(self.search_bar)
        return layout

    def _create_details_panel(self):
        details_box = QGroupBox("Details")
        main_layout = QHBoxLayout(details_box)
        self.details_cover_label = QLabel()
        self.details_cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.details_cover_label.setMinimumSize(200, 200)
        self.details_cover_label.setMaximumSize(200, 200)
        self.details_cover_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        
        info_layout = QFormLayout()
        self.details_title_label = QLabel()
        self.details_title_label.setWordWrap(True)
        self.details_title_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.details_platform_label = QLabel()
        self.details_size_label = QLabel()
        self.details_playtime_label = QLabel()
        info_layout.addRow(self.details_title_label)
        info_layout.addRow(QLabel())
        info_layout.addRow("<b>Platform:</b>", self.details_platform_label)
        info_layout.addRow("<b>File Size:</b>", self.details_size_label)
        info_layout.addRow("<b>Time Played:</b>", self.details_playtime_label)

        main_layout.addWidget(self.details_cover_label)
        main_layout.addLayout(info_layout)
        
        self.details_placeholder_label = QLabel("Select a game to see details here.")
        self.details_placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.details_placeholder_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        
        details_widget_stack = QWidget()
        stack_layout = QVBoxLayout(details_widget_stack)
        stack_layout.setContentsMargins(0,0,0,0)
        stack_layout.addWidget(details_box)
        stack_layout.addWidget(self.details_placeholder_label)
        
        # ++++++++++++++ THE FIX IS HERE ++++++++++++++
        # The problematic call is REMOVED from this method.
        # self.update_details_panel(None) 
        
        return details_widget_stack

    def _create_emulators_tab(self):
        emulators_widget = QWidget(); layout = QVBoxLayout(emulators_widget)
        search_and_scan_layout = QHBoxLayout()
        self.emu_search_bar = QLineEdit(); self.emu_search_bar.setPlaceholderText("Search emulators...")
        self.emu_search_bar.textChanged.connect(self.update_emulator_list); search_and_scan_layout.addWidget(self.emu_search_bar)
        btn_scan_emus = QPushButton("Scan Folder for Emulators..."); btn_scan_emus.clicked.connect(self.scan_for_emulators)
        search_and_scan_layout.addWidget(btn_scan_emus); layout.addLayout(search_and_scan_layout)
        
        self.emulators_tree = QTreeWidget()
        self.emulators_tree.setHeaderHidden(True)
        self.emulators_tree.itemDoubleClicked.connect(self.launch_selected_emulator); self.emulators_tree.currentItemChanged.connect(self.on_emulator_selection_changed)
        
        button_layout = QHBoxLayout()
        self.btn_add_emu = QPushButton(self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon), "Add..."); self.btn_edit_emu = QPushButton(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogYesButton), "Edit...")
        self.btn_remove_emu = QPushButton(self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon), "Remove"); self.btn_start_emu = QPushButton(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay), "Start")
        self.btn_add_emu.clicked.connect(self.add_emulator); self.btn_edit_emu.clicked.connect(self.edit_emulator); self.btn_remove_emu.clicked.connect(self.remove_emulator); self.btn_start_emu.clicked.connect(self.launch_selected_emulator)
        button_layout.addWidget(self.btn_add_emu); button_layout.addWidget(self.btn_edit_emu); button_layout.addWidget(self.btn_remove_emu); button_layout.addStretch(); button_layout.addWidget(self.btn_start_emu)
        layout.addWidget(self.emulators_tree); layout.addLayout(button_layout)
        self.on_emulator_selection_changed(None)
        return emulators_widget

    def apply_theme(self):
        colors = self.themes[self.current_theme_name]
        self.setStyleSheet(f"""
            QGroupBox {{ 
                font-weight: bold; 
                border: 1px solid {colors['C_BORDER']}; 
                border-radius: 4px; 
                margin-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
            }}
            QMainWindow, QWidget, QDialog {{ background-color: {colors['C_BACKGROUND_DARK']}; color: {colors['C_TEXT_PRIMARY']}; border: none; }}
            QToolBar {{ background-color: {colors['C_BACKGROUND_LIGHT']}; padding: 4px; border-bottom: 1px solid {colors['C_BACKGROUND_WIDGET']}; }}
            QTabWidget::pane {{ border-top: 1px solid {colors['C_BACKGROUND_LIGHT']}; }}
            QTabBar::tab {{ background: {colors['C_BACKGROUND_DARK']}; color: {colors['C_TEXT_SECONDARY']}; padding: 10px; border: 1px solid {colors['C_BACKGROUND_LIGHT']}; border-bottom: none; }}
            QTabBar::tab:selected, QTabBar::tab:hover {{ background: {colors['C_BACKGROUND_LIGHT']}; color: {colors['C_TEXT_PRIMARY']}; }}
            QSplitter::handle {{ background-color: {colors['C_BACKGROUND_LIGHT']}; }}
            QListWidget, QTreeWidget {{ background-color: {colors['C_BACKGROUND_WIDGET']}; border: none; padding: 5px; }}
            QListWidget::item:hover, QTreeWidget::item:hover {{ background-color: {colors['C_BACKGROUND_LIGHT']}; }}
            QListWidget::item:disabled {{ color: #888888; }}
            QHeaderView::section {{ background-color: {colors['C_BACKGROUND_LIGHT']}; padding: 4px; border: 1px solid {colors['C_BORDER']}; }}
            QPushButton {{ background-color: {colors['C_BACKGROUND_LIGHT']}; border: 1px solid {colors['C_BORDER']}; padding: 5px; min-width: 0; }}
            QPushButton:hover {{ background-color: {colors['C_BORDER']}; }} QPushButton:pressed {{ background-color: {colors['C_HIGHLIGHT_BLUE']}; }}
            QPushButton:disabled {{ background-color: {colors['C_BACKGROUND_DARK']}; border-color: {colors['C_BACKGROUND_LIGHT']}; color: {colors['C_BORDER']}; }}
            QPushButton:checkable:checked {{ background-color: {colors['C_HIGHLIGHT_BLUE']}; border-color: {colors['C_HIGHLIGHT_CYAN']}; }}
            QStatusBar {{ color: {colors['C_TEXT_PRIMARY']}; }}
            QLineEdit, QComboBox {{ border: 1px solid {colors['C_BORDER']}; padding: 5px; background-color: {colors['C_BACKGROUND_LIGHT']}; min-width: 120px; }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox QAbstractItemView {{ border: 1px solid {colors['C_BORDER']}; background-color: {colors['C_BACKGROUND_LIGHT']}; selection-background-color: {colors['C_HIGHLIGHT_BLUE']}; }}
            QSlider::groove:horizontal {{ border: 1px solid {Constants.C_BORDER}; height: 4px; background: {Constants.C_BORDER}; margin: 2px 0; border-radius: 2px; }}
            QSlider::handle:horizontal {{ background: {Constants.C_HIGHLIGHT_CYAN}; border: 1px solid {Constants.C_HIGHLIGHT_CYAN}; width: 14px; margin: -6px 0; border-radius: 8px; }}
            QToolTip {{ background-color: {colors['C_BACKGROUND_LIGHT']}; color: {colors['C_TEXT_PRIMARY']}; border: 1px solid {colors['C_BORDER']}; padding: 4px; }}
            QMenu {{ background-color: {colors['C_BACKGROUND_LIGHT']}; border: 1px solid {colors['C_BORDER']}; padding: 4px; }}
            QMenu::item {{ padding: 5px 25px 5px 25px; }}
            QMenu::item:selected {{ background-color: {colors['C_HIGHLIGHT_BLUE']}; color: {colors['C_TEXT_PRIMARY']}; }}
            QMenu::separator {{ height: 1px; background: {colors['C_BORDER']}; margin-left: 10px; margin-right: 5px; }}
        """); self.theme_toggle_action.setIcon(self.create_theme_icon())
    
    def toggle_theme(self):
        self.current_theme_name = "Modern Light" if self.current_theme_name == "Modern Dark" else "Modern Dark"
        self.apply_theme()
    def create_theme_icon(self):
        pixmap = QPixmap(24, 24); pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        colors = self.themes[self.current_theme_name]
        painter.setBrush(QColor(colors['C_TEXT_PRIMARY'])); painter.setPen(Qt.PenStyle.NoPen)
        if self.current_theme_name == "Modern Dark":
            painter.drawEllipse(6, 6, 12, 12)
        else:
            path = QPainterPath(); path.addEllipse(4, 4, 16, 16); path.addEllipse(8, 4, 16, 16); path.setFillRule(Qt.FillRule.OddEvenFill); painter.drawPath(path)
        painter.end(); return QIcon(pixmap)
        
    def create_view_switcher_icon(self, mode):
        pixmap = QPixmap(24, 24); pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap); painter.setRenderHint(QPainter.RenderHint.Antialiasing); painter.setPen(QPen(QColor(self.themes[self.current_theme_name]['C_TEXT_PRIMARY']), 2))
        if mode == 'list':
            for y in [6, 12, 18]: painter.drawLine(3, y, 21, y)
        elif mode == 'grid':
            painter.drawRect(4, 4, 7, 7); painter.drawRect(13, 4, 7, 7); painter.drawRect(4, 13, 7, 7); painter.drawRect(13, 13, 7, 7)
        painter.end(); return QIcon(pixmap)

    def set_view_mode(self, is_grid):
        self.is_grid_mode = is_grid; self._apply_view_mode_settings()
    def _apply_view_mode_settings(self):
        self.games_list.clear(); self.btn_grid_view.setChecked(self.is_grid_mode); self.btn_list_view.setChecked(not self.is_grid_mode)
        self.icon_size_slider.blockSignals(True)
        if self.is_grid_mode:
            self.games_list.setViewMode(QListWidget.ViewMode.IconMode); self.games_list.setFlow(QListWidget.Flow.LeftToRight); self.games_list.setWrapping(True)
            self.games_list.setResizeMode(QListWidget.ResizeMode.Adjust); self.games_list.setSpacing(15)
            self.games_list.setIconSize(QSize(self.current_grid_icon_size, int(self.current_grid_icon_size * 1.33))); self.games_list.setItemDelegate(self.grid_delegate)
            self.icon_size_slider.setRange(Constants.MIN_GRID_ICON_SIZE, Constants.MAX_GRID_ICON_SIZE); self.icon_size_slider.setValue(self.current_grid_icon_size)
        else:
            self.games_list.setViewMode(QListWidget.ViewMode.ListMode); self.games_list.setFlow(QListWidget.Flow.TopToBottom); self.games_list.setWrapping(False)
            self.games_list.setResizeMode(QListWidget.ResizeMode.Adjust); self.games_list.setSpacing(0)
            self.games_list.setIconSize(QSize(self.current_list_icon_size, self.current_list_icon_size)); self.games_list.setItemDelegate(self.list_delegate)
            self.icon_size_slider.setRange(Constants.MIN_LIST_ICON_SIZE, Constants.MAX_LIST_ICON_SIZE); self.icon_size_slider.setValue(self.current_list_icon_size)
        self.icon_size_slider.blockSignals(False); self.repopulate_games_list()
    def on_icon_size_changed(self, value):
        if self.is_grid_mode:
            self.current_grid_icon_size = value; self.games_list.setIconSize(QSize(value, int(value * 1.33)))
        else:
            self.current_list_icon_size = value; self.games_list.setIconSize(QSize(value, value))
        self.games_list.doItemsLayout()

    def on_search_text_changed(self):
        self.search_debounce_timer.start()

    def on_sort_order_changed(self, sort_text):
        self.config_manager.config['sort_order'] = sort_text
        self.repopulate_games_list()

    def repopulate_games_list(self):
        current_item_data = self.games_list.currentItem().data(Qt.ItemDataRole.UserRole) if self.games_list.currentItem() else None
        self.games_list.clear(); current_system = self.systems_list.currentItem()
        if not current_system: return
        system_name = current_system.text()
        if system_name == Constants.ALL_GAMES_CATEGORY: games = list(self.backend.all_games_map.values())
        elif system_name == Constants.FAVORITES_CATEGORY: games = self.backend.get_favorite_games()
        elif system_name == Constants.RECENTS_CATEGORY: games = self.backend.get_recently_played_games()
        else: games = self.backend.games_by_platform.get(system_name, [])
        sort_key = self.sort_combo.currentText()
        if sort_key == "Name": games.sort(key=lambda g: g['title'].lower())
        elif sort_key == "File Size (Asc)": games.sort(key=lambda g: g.get('size', 0))
        elif sort_key == "Time Played": games.sort(key=lambda g: g.get('playtime', 0), reverse=True)
        else: games.sort(key=lambda g: g.get('size', 0), reverse=True)
        search_text = self.search_bar.text().lower()
        if search_text: games = [g for g in games if search_text in g['title'].lower()]
        
        item_to_reselect = None
        for game_data in games: 
            item = self._add_game_item_to_view(game_data)
            if current_item_data and game_data['hash'] == current_item_data['hash']:
                item_to_reselect = item
        
        if item_to_reselect:
            self.games_list.setCurrentItem(item_to_reselect)
        elif self.games_list.count() > 0:
            self.games_list.setCurrentRow(0)
        else:
            self.update_details_panel(None)
        
    def _add_game_item_to_view(self, game_data):
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, game_data)
        item.setToolTip(game_data['title'])
        is_path_valid = os.path.exists(game_data['path'])
        if is_path_valid:
            item.setData(Qt.ItemDataRole.DisplayRole, game_data['title'])
        else:
            item.setData(Qt.ItemDataRole.DisplayRole, f"[MISSING] {game_data['title']}")
            item.setForeground(QColor("red"))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
        cover_path = self.get_cover_path_for_game(game_data)
        icon = QIcon(str(cover_path)) if cover_path and cover_path.is_file() else self.create_placeholder_icon(game_data['title'])
        item.setData(Qt.ItemDataRole.DecorationRole, icon); self.games_list.addItem(item)
        return item

    def create_placeholder_icon(self, text):
        size = self.games_list.iconSize()
        if not size.isValid() or size.width() <= 0 or size.height() <= 0: return QIcon()
        pixmap = QPixmap(size); pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap); painter.setRenderHint(QPainter.RenderHint.Antialiasing); painter.setBrush(QBrush(QColor(85, 85, 85, 100))); painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(pixmap.rect(), 10, 10)
        font_size = 12 if size.width() < 100 else 24; font = QFont("Segoe UI", font_size, QFont.Weight.Bold)
        painter.setFont(font); painter.setPen(QColor("#FFFFFF")); text_rect = pixmap.rect().adjusted(15, 15, -15, -15)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, text); painter.end()
        return QIcon(pixmap)

    def initial_load(self):
        self.statusBar().showMessage("Loading library from cache...")
        if self.backend.load_from_cache():
            self.update_system_list()
            self.update_emulator_list()
            self.statusBar().showMessage("Library loaded from cache. Ready.", 5000)
        else:
            self.statusBar().showMessage("No cache found. Performing initial library scan...")
            self.start_full_scan()

    def start_full_scan(self):
        if self.scanner_thread and self.scanner_thread.isRunning():
            return
        self.backend.clear_cache()
        self.refresh_action.setEnabled(False)
        self.scanner_thread = GameScanner(self.backend)
        self.scanner_thread.progress_update.connect(self.statusBar().showMessage)
        self.scanner_thread.scan_finished.connect(self.on_scan_finished)
        self.scanner_thread.finished.connect(lambda: self.refresh_action.setEnabled(True))
        self.scanner_thread.start()

    def on_scan_finished(self, games_by_platform, all_games_map):
        self.backend.games_by_platform = games_by_platform
        self.backend.all_games_map = all_games_map
        self.backend.save_to_cache()
        self.update_system_list()
        self.update_emulator_list()
        self.statusBar().showMessage("Library scan complete. Ready.", 5000)
        
    def update_system_list(self):
        current_text = self.systems_list.currentItem().text() if self.systems_list.currentItem() else None
        self.systems_list.clear()
        self.systems_list.addItem(QListWidgetItem(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon), Constants.ALL_GAMES_CATEGORY))
        if self.backend.get_favorite_games(): self.systems_list.addItem(QListWidgetItem(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton), Constants.FAVORITES_CATEGORY))
        if self.backend.get_recently_played_games(): self.systems_list.addItem(QListWidgetItem(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload), Constants.RECENTS_CATEGORY))
        if self.backend.games_by_platform:
            sep = QListWidgetItem("────────── PLATFORMS ──────────"); sep.setFlags(Qt.ItemFlag.NoItemFlags); self.systems_list.addItem(sep)
        for system in sorted(self.backend.games_by_platform.keys()):
            self.systems_list.addItem(system)
        items = self.systems_list.findItems(current_text, Qt.MatchFlag.MatchExactly) if current_text else []
        if items:
            self.systems_list.setCurrentItem(items[0])
        elif self.systems_list.count() > 0:
            self.systems_list.setCurrentRow(0)
    
    def update_emulator_list(self):
        search_text = self.emu_search_bar.text().lower()
        self.emulators_tree.clear()
        
        emulators_by_system = {}
        for name, data in self.config_manager.config["emulators"].items():
            for system in data.get("systems", []):
                if system not in emulators_by_system:
                    emulators_by_system[system] = []
                emulators_by_system[system].append({"name": name, "data": data})

        for system_name in sorted(emulators_by_system.keys()):
            child_items = []
            for emu in emulators_by_system[system_name]:
                emu_name_lower = emu["name"].lower()
                if search_text and search_text not in emu_name_lower:
                    continue
                
                child = QTreeWidgetItem([emu["name"]])
                child.setData(0, Qt.ItemDataRole.UserRole, emu["name"])
                child_items.append(child)

            if child_items:
                parent = QTreeWidgetItem(self.emulators_tree, [system_name])
                parent.addChildren(child_items)

        self.emulators_tree.expandAll()
    
    def _setup_common_list_properties(self):
        self.games_list.itemDoubleClicked.connect(self.launch_selected_game); self.games_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.games_list.customContextMenuRequested.connect(self.show_game_context_menu)
        self.games_list.currentItemChanged.connect(self.update_details_panel)

    def update_details_panel(self, current_item):
        details_box = self.details_panel.findChild(QGroupBox)
        if not details_box: return
        
        if not current_item or not current_item.data(Qt.ItemDataRole.UserRole):
            details_box.setVisible(False)
            self.details_placeholder_label.setVisible(True)
            return

        details_box.setVisible(True)
        self.details_placeholder_label.setVisible(False)
        game_data = current_item.data(Qt.ItemDataRole.UserRole)
        
        self.details_title_label.setText(game_data.get('title', 'N/A'))
        self.details_platform_label.setText(game_data.get('platform', 'N/A'))
        self.details_size_label.setText(format_size(game_data.get('size', 0)))
        self.details_playtime_label.setText(format_playtime(game_data.get('playtime', 0)))

        cover_path = self.get_cover_path_for_game(game_data)
        if cover_path:
            pixmap = QPixmap(str(cover_path))
            self.details_cover_label.setPixmap(pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            self.details_cover_label.setPixmap(self.create_placeholder_icon(game_data['title']).pixmap(200,200))

    def get_cover_path_for_game(self, game_data):
        custom_cover_name = self.config_manager.config["custom_covers"].get(game_data["hash"])
        if custom_cover_name:
            cached_cover = self.config_manager.cache_dir / custom_cover_name
            if cached_cover.is_file(): return cached_cover
            main_cover = self.config_manager.covers_dir / custom_cover_name
            if main_cover.is_file(): return main_cover
        return None

    def on_toggle_details_panel(self, checked):
        self.details_panel.setVisible(checked)
        self.config_manager.config['details_panel_visible'] = checked

    def open_library_manager(self):
        dialog = LibraryManagerDialog(self.config_manager, self);
        if dialog.exec():
            self.start_full_scan()

    # ++++++++++++++ THE FIX IS HERE (AGAIN) ++++++++++++++
    def add_emulator(self):
        exe_path, _ = QFileDialog.getOpenFileName(self, "Select Emulator Executable", "", "Executables (*.exe);;All Files (*)")
        if not exe_path:
            return

        detected = self.backend.detect_emulator_from_exe(exe_path)
        
        if detected:
            # Successfully auto-detected
            if detected['name'] not in self.config_manager.config["emulators"]:
                self.config_manager.config["emulators"][detected['name']] = detected['data']
                self.config_manager.save_config()
                self.update_emulator_list()
                QMessageBox.information(self, "Emulator Added", f"Successfully auto-detected and added '{detected['name']}'.")
            else:
                QMessageBox.warning(self, "Emulator Exists", f"An emulator named '{detected['name']}' is already configured.")
        else:
            # Detection failed, fall back to manual entry
            QMessageBox.information(self, "Unknown Emulator", "Could not identify this emulator. Please enter its details manually.")
            dialog = EmulatorEditDialog(emu_data={"path": exe_path}, parent=self)
            if dialog.exec():
                result = dialog.get_data()
                if result["name"] and result["data"]["path"]:
                    if result["name"] in self.config_manager.config["emulators"]:
                        QMessageBox.warning(self, "Emulator Exists", f"An emulator named '{result['name']}' is already configured.")
                    else:
                        self.config_manager.config["emulators"][result["name"]] = result["data"]
                        self.config_manager.save_config()
                        self.update_emulator_list()

    def scan_for_emulators(self):
        scan_path = QFileDialog.getExistingDirectory(self, "Select Folder to Scan for Emulators")
        if not scan_path: return
        found_count = 0
        for root, _, files in os.walk(scan_path):
            for file in files:
                full_path = os.path.join(root, file)
                detected = self.backend.detect_emulator_from_exe(full_path)
                if detected and detected['name'] not in self.config_manager.config['emulators']:
                    self.config_manager.config['emulators'][detected['name']] = detected['data']; found_count += 1
        if found_count > 0:
            self.config_manager.save_config(); self.update_emulator_list()
            QMessageBox.information(self, "Scan Complete", f"Found and added {found_count} new emulator(s).")
        else: QMessageBox.information(self, "Scan Complete", "No new emulators found in the selected folder.")
        
    def on_emulator_selection_changed(self, item):
        is_child = item is not None and item.parent() is not None
        self.btn_edit_emu.setEnabled(is_child)
        self.btn_remove_emu.setEnabled(is_child)
        self.btn_start_emu.setEnabled(is_child)

    def edit_emulator(self):
        item = self.emulators_tree.currentItem()
        if not item or not item.parent(): return
        name = item.data(0, Qt.ItemDataRole.UserRole); dialog = EmulatorEditDialog(name, self.config_manager.config["emulators"][name], self)
        if dialog.exec():
            result = dialog.get_data()
            if result["name"] and result["data"]["path"]:
                if name != result["name"]: del self.config_manager.config["emulators"][name]
                self.config_manager.config["emulators"][result["name"]] = result["data"]; self.config_manager.save_config(); self.update_emulator_list()
    def remove_emulator(self):
        item = self.emulators_tree.currentItem()
        if not item or not item.parent(): return
        name = item.data(0, Qt.ItemDataRole.UserRole)
        if QMessageBox.question(self, "Confirm", f"Remove '{name}'?") == QMessageBox.StandardButton.Yes:
            del self.config_manager.config["emulators"][name]; self.config_manager.save_config(); self.update_emulator_list()
    def launch_selected_game(self, item):
        game_data = item.data(Qt.ItemDataRole.UserRole)

        if game_data.get('platform') == 'PlayStation 3' and game_data.get('path', '').lower().endswith('.pkg'):
            QMessageBox.information(self, "Installation Required",
                                    "This is a PlayStation 3 package file (.pkg).\n\n"
                                    "It must be installed first using your emulator (e.g., RPCS3's 'File > Install Packages/Raps/Edats' option).\n\n"
                                    "You cannot launch this file directly from EmulatorHub.")
            return
            
        custom_emu_name = self.config_manager.config.get("game_metadata", {}).get(game_data['hash'], {}).get("custom_emulator")
        chosen_emulator_config = None
        system = game_data['platform']
        if custom_emu_name:
            chosen_emulator_config = self.config_manager.config["emulators"].get(custom_emu_name)
            if not chosen_emulator_config:
                QMessageBox.warning(self, "Launch Error", f"The custom emulator '{custom_emu_name}' is no longer configured."); return
        else:
            platform_defaults = self.config_manager.config.get("platform_defaults", {})
            default_emu_name = platform_defaults.get(system)
            if default_emu_name and default_emu_name in self.config_manager.config["emulators"]:
                 chosen_emulator_config = self.config_manager.config["emulators"][default_emu_name]
            else:
                available_emulators = self.backend.get_emulators_for_system(system)
                if not available_emulators:
                    QMessageBox.warning(self, "Launch Error", f"No emulator configured for {system}."); return
                if len(available_emulators) == 1:
                    chosen_emulator_config = available_emulators[0]['config']
                else:
                    dialog = EmulatorChoiceDialog([emu['name'] for emu in available_emulators], system, self)
                    if dialog.exec():
                        name = dialog.get_selected_emulator_name()
                        chosen_emulator_config = next((emu['config'] for emu in available_emulators if emu['name'] == name), None)
                        if dialog.get_set_as_default() and name:
                            self.config_manager.config["platform_defaults"][system] = name
                            self.config_manager.save_config()
                            self.statusBar().showMessage(f"Set {name} as default for {system}.")
                    else: return
        if chosen_emulator_config:
            process, message = self.backend.launch_game(game_data['hash'], chosen_emulator_config)
            self.statusBar().showMessage(message)
            if process: self.start_playtime_tracker(process, game_data['hash'])
            else: QMessageBox.warning(self, "Launch Error", message)

    def start_playtime_tracker(self, process, game_hash):
        if not psutil: return
        pid = process.pid; start_time = time.time()
        timer = QTimer(self); self.process_timers[pid] = timer
        def check_process():
            if not psutil.pid_exists(pid):
                elapsed_time = time.time() - start_time
                metadata = self.config_manager.config["game_metadata"].setdefault(game_hash, {})
                metadata['playtime'] = metadata.get('playtime', 0) + elapsed_time
                self.config_manager.save_config()
                if game_hash in self.backend.all_games_map:
                    self.backend.all_games_map[game_hash]['playtime'] = metadata['playtime']
                self.process_timers[pid].stop(); del self.process_timers[pid]
                self.repopulate_games_list()
        timer.timeout.connect(check_process); timer.start(5000)
        
    def launch_selected_emulator(self, item=None):
        if not item or not isinstance(item, QTreeWidgetItem): item = self.emulators_tree.currentItem()
        if not item or not item.parent(): return
        
        name = item.data(0, Qt.ItemDataRole.UserRole)
        path = self.config_manager.config["emulators"][name]['path']
        try: subprocess.Popen([os.path.normpath(path)])
        except Exception as e: QMessageBox.critical(self, "Launch Error", f"Failed to start emulator:\n{e}")
    
    def show_game_context_menu(self, pos):
        item = self.games_list.itemAt(pos)
        if not item: return
        game_data = item.data(Qt.ItemDataRole.UserRole)
        context_menu = QMenu(self)
        is_enabled = bool(item.flags() & Qt.ItemFlag.ItemIsEnabled)
        play_action = context_menu.addAction(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay), "Play Game")
        bold_font = QFont(); bold_font.setBold(True); play_action.setFont(bold_font)
        play_action.triggered.connect(lambda: self.launch_selected_game(item))
        play_action.setEnabled(is_enabled)
        context_menu.addSeparator()
        is_fav = self.backend.is_favorite(game_data['hash'])
        fav_text = "Remove from Favorites" if is_fav else "Add to Favorites"
        fav_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton if is_fav else QStyle.StandardPixmap.SP_DialogApplyButton)
        fav_action = context_menu.addAction(fav_icon, fav_text)
        fav_action.triggered.connect(lambda: self.toggle_favorite(game_data['hash']))
        context_menu.addSeparator()
        manage_menu = context_menu.addMenu("Manage...")
        custom_emu_menu = manage_menu.addMenu("Set Custom Emulator")
        game_metadata = self.config_manager.config.get("game_metadata", {}).get(game_data['hash'], {})
        current_custom_emu = game_metadata.get("custom_emulator")
        clear_action = custom_emu_menu.addAction("Use Platform Default"); clear_action.setCheckable(True)
        clear_action.setChecked(current_custom_emu is None); clear_action.triggered.connect(lambda: self.set_custom_emulator_for_game(game_data['hash'], None))
        custom_emu_menu.addSeparator()
        for emu_name in sorted(self.config_manager.config.get("emulators", {}).keys()):
            action = custom_emu_menu.addAction(emu_name); action.setCheckable(True)
            action.setChecked(emu_name == current_custom_emu)
            action.triggered.connect(lambda checked, name=emu_name: self.set_custom_emulator_for_game(game_data['hash'], name))
        cover_action = manage_menu.addAction("Set Custom Image...")
        cover_action.triggered.connect(lambda: self.set_custom_game_image(item))
        platform_defaults = self.config_manager.config.get("platform_defaults", {})
        if game_data['platform'] in platform_defaults:
            clear_default_action = manage_menu.addAction(f"Clear Default Emulator for {game_data['platform']}")
            clear_default_action.triggered.connect(lambda: self.clear_platform_default_emulator(game_data['platform']))
        
        manage_menu.addSeparator()
        delete_action = manage_menu.addAction(self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon), "Delete Files...")
        delete_action.triggered.connect(lambda: self.delete_game_files(item))
        delete_action.setEnabled(is_enabled)

        context_menu.addSeparator()
        show_folder_action = context_menu.addAction(self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon), "Show in Folder")
        show_folder_action.triggered.connect(lambda: self.show_game_in_explorer(item))
        show_folder_action.setEnabled(is_enabled)
        info_action = context_menu.addAction(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogHelpButton), "View Info...")
        info_action.triggered.connect(lambda: self.show_game_info(item))
        context_menu.exec(self.games_list.viewport().mapToGlobal(pos))
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            path = Path(event.mimeData().urls()[0].toLocalFile())
            if path.is_dir() or path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.webp']:
                event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if not urls:
            return
        path = Path(urls[0].toLocalFile())
        if path.is_dir():
            if str(path) not in self.config_manager.config["game_library_paths"]:
                reply = QMessageBox.question(self, "Add Library Folder", f"Do you want to add this folder to your game library?\n\n{path}")
                if reply == QMessageBox.StandardButton.Yes:
                    self.config_manager.config["game_library_paths"].append(str(path))
                    self.config_manager.save_config()
                    self.start_full_scan()
        elif path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.webp']:
            window_pos = event.position().toPoint()
            list_local_pos = self.games_list.mapFrom(self, window_pos)
            item = self.games_list.itemAt(list_local_pos)
            if item:
                self.set_custom_game_image(item, image_path=str(path))

    def show_game_in_explorer(self, item):
        game_data = item.data(Qt.ItemDataRole.UserRole)
        path = os.path.normpath(game_data['path'])
        try:
            if sys.platform == "win32":
                subprocess.Popen(['explorer', '/select,', path])
            elif sys.platform == "darwin": # macOS
                subprocess.Popen(['open', '-R', path])
            else: # Linux, etc.
                subprocess.Popen(['xdg-open', os.path.dirname(path)])
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open file location: {e}")

    def delete_game_files(self, item):
        game_data = item.data(Qt.ItemDataRole.UserRole)
        path_to_delete = Path(game_data['path'])
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Confirm Deletion")
        msg_box.setText(f"<h2>Permanently Delete Files?</h2>"
                        f"<p>This action cannot be undone. It will delete the following file or folder from your hard drive:</p>"
                        f"<p><b>{path_to_delete.resolve()}</b></p>")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        msg_box.setIcon(QMessageBox.Icon.Warning)

        if msg_box.exec() == QMessageBox.StandardButton.Yes:
            try:
                self.statusBar().showMessage(f"Deleting {path_to_delete.name}...")
                if path_to_delete.is_dir():
                    shutil.rmtree(path_to_delete)
                else:
                    path_to_delete.unlink()
                
                self.statusBar().showMessage(f"Successfully deleted {path_to_delete.name}.", 5000)
                self.start_full_scan()

            except Exception as e:
                QMessageBox.critical(self, "Deletion Error", f"Could not delete files.\n\nError: {e}")
                self.statusBar().showMessage("Deletion failed.", 5000)

    def clear_platform_default_emulator(self, platform_name):
        platform_defaults = self.config_manager.config.get("platform_defaults", {})
        if platform_name in platform_defaults:
            del platform_defaults[platform_name]
            self.config_manager.save_config()
            self.statusBar().showMessage(f"Cleared default emulator for {platform_name}. You will be prompted on next launch.")

    def set_custom_emulator_for_game(self, game_hash, emulator_name):
        metadata = self.config_manager.config["game_metadata"].setdefault(game_hash, {})
        if emulator_name:
            metadata["custom_emulator"] = emulator_name; self.statusBar().showMessage(f"Set {emulator_name} as custom emulator.")
        else:
            if "custom_emulator" in metadata: del metadata["custom_emulator"]
            self.statusBar().showMessage("Cleared custom emulator. Will use platform default.")
        self.config_manager.save_config()
        
    def toggle_favorite(self, game_hash):
        self.backend.toggle_favorite(game_hash)
        self.update_system_list()

    def set_custom_game_image(self, item, image_path=None):
        if not image_path:
            image_path, _ = QFileDialog.getOpenFileName(self, "Select Cover Image", "", "Images (*.png *.jpg *.jpeg *.webp)")
        if not image_path: return
        game_data = item.data(Qt.ItemDataRole.UserRole)
        success, message = self.backend.set_custom_game_image(game_data['hash'], image_path)
        if success:
            self.repopulate_games_list(); self.statusBar().showMessage(f"Set custom cover for {game_data['title']}")
        else:
            QMessageBox.critical(self, "Error", message)
    def show_game_info(self, item):
        game_data = item.data(Qt.ItemDataRole.UserRole)
        info = {"title": game_data.get('title', 'N/A'), "platform": game_data.get('platform', 'N/A'), "size": format_size(game_data.get('size', 0)), "playtime": format_playtime(game_data.get('playtime', 0))}
        GameInfoDialog(info, self).exec()
        self.statusBar().showMessage("Ready.")
    
    def restore_window_state(self):
        geo_hex = self.config_manager.config.get("window_geometry")
        if geo_hex: self.restoreGeometry(QByteArray.fromHex(bytes(geo_hex, 'ascii')))
        state_hex = self.config_manager.config.get("window_state")
        if state_hex: self.restoreState(QByteArray.fromHex(bytes(state_hex, 'ascii')))
        splitter_hex = self.config_manager.config.get("splitter_state")
        if splitter_hex: self.main_splitter.restoreState(QByteArray.fromHex(bytes(splitter_hex, 'ascii')))
        
        is_visible = self.config_manager.config.get("details_panel_visible", True)
        self.toggle_details_action.setChecked(is_visible)
        self.details_panel.setVisible(is_visible)

    def closeEvent(self, event):
        self.config_manager.config['view_mode'] = 'grid' if self.is_grid_mode else 'list'
        self.config_manager.config['grid_icon_size'] = self.current_grid_icon_size
        self.config_manager.config['list_icon_size'] = self.current_list_icon_size
        self.config_manager.config['theme'] = self.current_theme_name
        self.config_manager.config['window_geometry'] = self.saveGeometry().toHex().data().decode('ascii')
        self.config_manager.config['window_state'] = self.saveState().toHex().data().decode('ascii')
        self.config_manager.config['splitter_state'] = self.main_splitter.saveState().toHex().data().decode('ascii')
        self.config_manager.config['details_panel_visible'] = self.toggle_details_action.isChecked()
        self.config_manager.save_config(); event.accept()

# =============================================================================
# --- MAIN EXECUTION BLOCK ---
# =============================================================================
if __name__ == "__main__":
    app = QApplication(sys.argv); app.setFont(QFont("Segoe UI", 9))
    if psutil is None: print("WARNING: 'psutil' library not found. Playtime tracking will be disabled. Run 'pip install psutil' to enable it.")
    config = ConfigManager(); backend = EmulatorHubBackend(config); window = EmulatorHubWindow(backend, config)
    window.show(); sys.exit(app.exec())
