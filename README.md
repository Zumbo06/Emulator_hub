# EmulatorHub v2.00 🎮

A modern, feature-rich game library manager for emulators with enhanced UI/UX and powerful management tools.

![Version](https://img.shields.io/badge/version-2.00-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)
![PyQt6](https://img.shields.io/badge/PyQt6-6.4+-orange)

## 🌟 What's New in v2.00

### 🎨 Modern UI Enhancements
- **Tokyo Night Color Scheme** - Beautiful dark theme with cyan/purple accents
- **Enhanced Light Theme** - Professional, clean alternative theme
- **Gradient Backgrounds** - Stunning visual effects on game cards
- **Smooth Animations** - Polished hover effects and transitions
- **Better Typography** - Modern Segoe UI fonts with improved readability
- **Enhanced Borders & Shadows** - 3D depth with rounded corners

### 🔍 Advanced Search & Filtering
- **Smart Search Bar** with clear button (✕)
- **Platform Filter Dropdown** - Quick filter without changing selection
- **Debounced Search** - Improved performance (300ms delay)
- **Enhanced Sorting** - Name, Size (Asc/Desc), Time Played, Date Added
- **Game Count Display** - See filtered results in status bar

### 🎯 Game Card Enhancements
- **Playtime Badges** - Visual indicators on game cards
- **Hover Effects** - Smooth background highlighting
- **Shadow Effects** - Icons pop with depth
- **Custom Star Icons** - Beautiful favorite indicators
- **Better Selection** - Thick cyan borders (3px)

### 📊 Statistics Dashboard
- **Total Games & Size** - Complete library overview
- **Total Playtime** - Track your gaming hours
- **Top 5 Most Played** - See your favorite games
- **Platform Distribution** - Top platforms by game count
- **Beautiful Formatting** - Styled HTML presentation

### ⌨️ Keyboard Shortcuts
| Shortcut | Action |
|----------|--------|
| **F5** | Refresh Library |
| **Ctrl+F** | Focus Search Bar |
| **Ctrl+Tab** | Toggle Grid/List View |
| **Enter** | Launch Selected Game |
| **Delete** | Delete Selected Game(s) |
| **Ctrl+A** | Select All Games |
| **Ctrl+I** | Show Detailed Info |
| **Ctrl+B** | Toggle Batch Mode |

### 📦 Game Collections
- **Create Custom Collections** - Organize games your way
- **Add to Collections** - Right-click context menu
- **Collection Manager** - Create, rename, delete collections
- **Multiple Collections** - Games can be in multiple collections

### 🔧 Enhanced Game Management
- **Detailed Info Dialog** - Edit metadata, add notes, manage tags
- **Batch Operations** - Multi-select for mass actions
- **Batch Delete** - Delete multiple games at once
- **Custom Tags** - Comma-separated game tags
- **Notes Field** - Add personal notes to games

### ⚙️ Settings Panel
- **General Settings** - Auto-backup, performance modes
- **Appearance Settings** - Theme selection
- **Hotkeys Reference** - View all keyboard shortcuts
- **Performance Modes** - Low, Balanced, High

### 🚀 Performance Improvements
- **In-Memory Image Cache** - Faster icon loading
- **Lazy Loading** - Efficient resource management
- **Smart Caching** - Reduced disk I/O
- **Optimized Rendering** - Smoother scrolling

### 💫 Splash Screen
- **Animated Loading** - Beautiful startup experience
- **Progress Indicator** - See what's happening
- **Status Messages** - Know what's loading

## 📋 Requirements

```
PyQt6>=6.4.0
psutil>=5.9.0
Pillow>=9.0.0
```

## 🚀 Installation

1. **Clone or download** this repository
2. **Install dependencies**:
   ```bash
   pip install -r Requirements.txt
   ```
3. **Run the application**:
   ```bash
   python emulator_hub_app.py
   ```

## 🎮 Supported Platforms

### Consoles
- **PlayStation** (1, 2, 3)
- **Xbox** (Original, 360)
- **Nintendo** (Wii, GameCube, 64)
- **Sega** (Dreamcast, Genesis, Game Gear, Saturn)
- **TurboGrafx-16**

### Handhelds
- **Game Boy** (Original, Color, Advance)
- **Nintendo DS** / **3DS**
- **PlayStation Portable (PSP)**
- **Atari Lynx**

## 🔧 Features

### Library Management
- ✅ Automatic game scanning with progress tracking
- ✅ Multiple library folder support
- ✅ Smart file organization by platform
- ✅ Caching system for fast loading
- ✅ Drag & drop folder support

### Game Organization
- ✅ Platform-based categorization
- ✅ Favorites system with visual indicators
- ✅ Recently played tracking
- ✅ Custom collections
- ✅ Tag system
- ✅ Advanced search and filtering

### Visual Customization
- ✅ Grid and List view modes
- ✅ Adjustable icon sizes
- ✅ Custom game covers (drag & drop images)
- ✅ Automatic thumbnail generation
- ✅ Beautiful placeholder icons with gradients

### Emulator Integration
- ✅ Auto-detection of popular emulators
- ✅ Manual emulator configuration
- ✅ Custom launch arguments
- ✅ Platform-specific defaults
- ✅ Per-game emulator override

### Metadata & Tracking
- ✅ Playtime tracking with psutil
- ✅ File size information
- ✅ Custom notes per game
- ✅ Tagging system
- ✅ Statistics dashboard

### User Experience
- ✅ Dark and Light themes
- ✅ Keyboard shortcuts
- ✅ Context menus
- ✅ Details panel
- ✅ Batch operations
- ✅ Settings dialog

## 🎨 Themes

### Modern Dark (Default)
- Deep blue-black backgrounds (#1A1B26)
- Cyan highlights (#2AC3DE)
- Purple accents (#BB9AF7)
- Perfect for long sessions

### Modern Light
- Clean white backgrounds (#F5F5F5)
- Professional blue highlights (#5E81AC)
- High contrast for readability

## 📖 Usage Guide

### Adding Games
1. Click **"Manage Game Folders"** in toolbar
2. Add folders containing your game files
3. Click **F5** or **"Refresh Library"** to scan
4. Games are automatically categorized by platform

### Launching Games
1. **Double-click** a game or press **Enter**
2. Select emulator if multiple available
3. Set as default for faster future launches

### Creating Collections
1. Click **"Manage Collections"** in toolbar
2. Create new collection with custom name
3. Right-click games → **"Add to Collection"**

### Batch Operations
1. Press **Ctrl+B** or click **"Batch Operations"**
2. Select multiple games (Ctrl+Click or Shift+Click)
3. Press **Delete** to remove selected games
4. Or use context menu for other actions

### Custom Covers
- **Drag & drop** image onto game card
- Or right-click → **"Set Custom Image"**
- Supports PNG, JPG, JPEG, WEBP

### Editing Game Info
- Press **Ctrl+I** on selected game
- Or right-click → **"Detailed Info"**
- Edit title, add notes, manage tags

## 🔥 Advanced Features

### Performance Modes
- **Low** - Minimal animations, faster on older hardware
- **Balanced** - Good performance with visual effects (default)
- **High** - Maximum visual quality

### Auto-Backup
- Automatic config backups before changes
- Restore from backup if issues occur

### Smart Caching
- Game library cached for instant loading
- Image cache for faster thumbnails
- Clear cache to force rescan

## 🐛 Known Issues & Solutions

### Game not launching?
- Check emulator path in "Emulators" tab
- Verify emulator supports the game format
- Set custom launch arguments if needed

### Playtime not tracking?
- Install psutil: `pip install psutil`
- Restart application after installation

### Images not loading?
- Install Pillow: `pip install Pillow`
- Check image format (PNG, JPG, JPEG, WEBP)

## 📜 License

This project is open source and available for personal use.

## 🙏 Credits

Built with:
- **PyQt6** - Modern Qt bindings for Python
- **Pillow** - Image processing
- **psutil** - Process and system utilities

---

**Enjoy your enhanced gaming library! 🎮✨**

For issues or feature requests, please create an issue on the repository.
