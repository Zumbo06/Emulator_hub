# EmulatorHub

EmulatorHub is a modern, cross-platform graphical frontend for managing and launching your video game emulator collection. It scans your game libraries, organizes your titles by platform, and provides a clean, user-friendly interface to browse and play your games.

## Features

*   **Unified Game Library:** All your games from different platforms in one beautiful, browsable interface.
*   **Emulator Management:** Add, configure, and manage all your emulators from a single tab.
*   **Smart Auto-Detection:** Automatically detects popular emulators for 5th and 6th generation consoles (and beyond), including Dolphin, PCSX2, Xenia, Redream, Project64, and more.
*   **Rich User Interface:**
    *   Choose between a modern Grid View with box art or a detailed List View.
    *   Customizable icon sizes to fit your preference.
    *   Light and Dark themes.
    *   On-demand details panel shows game info at a glance.
*   **Game Information:**
    *   Tracks and displays playtime for each game.
    *   Displays file size and platform information.
    *   Favorites and Recently Played categories for quick access.
*   **Per-Game Customization:**
    *   Set custom cover art for any game via file browser or drag-and-drop.
    *   Override the default emulator for a specific game that requires a different one.
*   **Efficient & Fast:**
    *   Library scanning runs in the background, keeping the UI fully responsive.
    *   Game library data is cached for near-instantaneous application startup.
*   **Powerful Management Tools:**
    *   Right-click to show a game in your file explorer.
    *   Right-click to permanently delete game files from your drive (with confirmation).

## Installation

### 1. Prerequisites
*   Python 3.8 or newer.
*   Your own game files and emulators. This application is a launcher and does not provide any games or emulators.

### 2. Setup
1.  Clone this repository or download the source code as a ZIP file.
    ```bash
    git clone https://github.com/Zumbo06/Emulator_hub
    cd EmulatorHub
    ```
2.  Install the required Python packages using the `requirements.txt` file. It's recommended to do this in a virtual environment.
    ```bash
    # Create and activate a virtual environment (optional but recommended)
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`

    # Install dependencies
    pip install -r requirements.txt
    ```

## How to Run

Once the dependencies are installed, you can run the application with the following command:

```bash
python emulator_hub_app.py
```

## First-Time Setup

1.  **Add Game Folders:** On first launch, your library will be empty. Click the "folder" icon in the top-left toolbar or go to `File > Manage Game Folders...` to add the directories where you store your game files. The app will automatically scan them.
2.  **Add Emulators:**
    *   Go to the **Emulators** tab.
    *   Click the **"Scan Folder for Emulators..."** button and select the directory where you keep your emulator executables. The app will attempt to auto-detect and configure them.
    *   Alternatively, click the **"Add..."** button to manually configure an emulator by pointing to its executable.
3.  **Play!** Go back to the Library tab, select a game, and double-click to play.


_This project is created for educational and personal use. Please support game developers and publishers by purchasing games legally._
