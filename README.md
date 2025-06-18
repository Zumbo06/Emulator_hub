EmulatorHub
EmulatorHub is a sleek and modern graphical frontend for managing and launching your retro game collection. It scans your game libraries, organizes your collection by platform, and provides a beautiful, user-friendly interface to browse and play your favorite titles.

Features
Automatic Game Scanning: Point EmulatorHub to your game folders, and it will automatically scan and import your collection.
Platform Organization: Games are automatically sorted by their original console (e.g., PlayStation 2, Nintendo 64, Dreamcast).
Multiple Views: Browse your collection in a visually-rich Grid View with box art or a clean and simple List View.
Playtime Tracking: Automatically logs your playtime for each game.
Emulator Management:
Auto-Detection: Automatically detects a wide range of popular emulators for 5th and 6th generation consoles and beyond.
Manual Configuration: Easily add any emulator and configure its launch arguments.
Per-Game Emulators: Override the default emulator for specific games that need special handling.
Customization:
Custom Artwork: Set your own custom cover art for any game via a simple right-click or drag-and-drop.
Light & Dark Themes: Switch between modern light and dark themes to suit your preference.
User-Friendly Interface:
On-Demand Details: A clean details panel shows game information when you need it.
Favorites & Recents: Quickly access your favorite or recently played games.
Powerful Context Menus: Right-click a game to play, add to favorites, manage files, or delete it from your drive (with confirmation).
Getting Started
Prerequisites
Python 3.8 or newer.
pip (Python's package installer).
Installation
Clone the repository:
Generated bash
git clone https://github.com/Zumbo06/Emulator_hub
cd EmulatorHub
Use code with caution.
Bash
Install the required packages:
A requirements.txt file is included to make installation easy. Run the following command in your terminal:
Generated bash
pip install -r requirements.txt
Use code with caution.
Bash
Run the application:
Generated bash
python emulator_hub_app.py
Use code with caution.
Bash
How to Use
Add Your Game Folders: On first launch, or by clicking the "Manage Game Folders" icon in the toolbar, add the folders where you store your game ROMs.
Add Your Emulators:
Go to the Emulators tab.
Click "Scan Folder for Emulators..." to have the app automatically find and configure them.
Alternatively, click "Add..." to manually select an emulator's executable. The app will attempt to auto-detect its settings.
Browse and Play: Navigate your library on the Library tab and double-click any game to launch it with the configured emulator!
Supported Emulators (Auto-Detection)
EmulatorHub can auto-detect the following emulators:
Nintendo 64: Project64, simple64
Nintendo GameCube / Wii: Dolphin
Nintendo Switch: Ryujinx, Sudachi
PlayStation: DuckStation, Mednafen
PlayStation 2: PCSX2
PlayStation 3: RPCS3
PSP: (Add PPSSPP if desired)
Sega Dreamcast: Redream, Flycast
Sega Saturn: Mednafen, YabaSanshiro, Kronos
Xbox: Xemu
Xbox 360: Xenia
...and more can be added manually!
