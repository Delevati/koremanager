# Bot Manager - Bot Management System

## Overview

Bot Manager is a desktop application developed in Python that automates the management of multiple bots, providing full control over startup, monitoring, restart, and configuration. Designed for the community, it offers an intuitive graphical interface and advanced monitoring features.

## Main Features

- **Complete Graphical Interface:** Tab system with control, configuration, and terminals
- **System Tray:** Quick access via tray icon
- **Real-Time Monitoring:** Status, uptime, CPU and memory usage
- **Log Capture (experimental):** Under development, not recommended for use. If a terminal is selected in the third tab, it is configured to show lines containing the word "card". However, there are known issues with line order and updates.
- **Configurable Auto-Restart:** Automatic restart at custom intervals
- **Drag & Drop:** Easily reorder bots
- **Multi-Selection:** Control several bots at once

## How It Works

- **Smart Management:** Automatically detects running bots and prevents duplicates
- **Flexible Execution:** Run bots with or without visible windows
- **Temporary Renaming:** Renames start.exe to start_<bot_name>.exe during execution
- **Continuous Monitoring:** Tracks status, resources, and logs
- **Persistent Configuration:** Saves settings in a JSON file

## Required Folder Structure

```
Main_Folder\
   ├─ bot1\
   │    └─ start.exe
   │    └─ logs\
   │         └─ console.txt
   ├─ bot2\
   │    └─ start.exe
   │    └─ logs\
   │         └─ console.txt
   ├─ bot3\
   │    └─ start.exe
   │    └─ logs\
   │         └─ console.txt
   └─ KoreManager.exe
   └─ bot_config.json (created automatically)
```

Each subfolder must contain:

- **start.exe:** Bot executable
- **logs/console.txt:** Log file (optional, for terminal viewing)

## How to Use

### 1. First Run

- Run KoreManager.exe
- Go to the "🔧 Setup & Configuration" tab
- Set the main directory where your bots are located
- Click "Scan" to automatically detect bots
- Save the configuration

### 2. Controlling Bots

- Go to the "🎮 Bot Control" tab
- Select the desired bots from the list
- Use the buttons to:
  - Start All/Stop All/Restart All: General control
  - Start/Stop/Restart: Control selected bots
  - View Output: See bot output

### 3. Monitoring

The table shows real-time status:

- **Status:** 🟢 Running / 🔴 Stopped
- **PID:** Process ID
- **Console:** WINDOW or NO_WINDOW
- **Memory/CPU:** Resource usage
- **Uptime:** Execution time

### 4. Log Terminals

- The "🖥️ Terminals" tab offers 3 simultaneous terminals
- Select a bot to view its logs in real time
- "⟳" button to clear logs

### 5. System Tray

- Tray icon for quick access
- Context menu with main controls
- Minimize to keep running in the background

## Advanced Settings

### Auto-Restart

- **Interval:** Configurable in minutes (default: 120 min = 2 hours)
- **Auto-restart:** Enable/disable automatic restart
- **Capture Output:** Capture bot output for viewing

### Execution Modes

- **NO_WINDOW:** Bots run without visible window (default)
- **WINDOW:** Check "WINDOW" to see bot windows

### Log Filters

- Configurable regex to filter important logs
- Default: searches for "Weight" or "card" in logs

## Shutting Down

**Method 1: Graphical Interface**

- Close the main window
- All bots will be stopped automatically

**Method 2: System Tray**

- Right-click the tray icon
- Select "Exit"

**Method 3: Task Manager**

- Process: KoreManager.exe (not wscript.exe)
- End the process in Task Manager

## Configuration Files

### bot_config.json

```json
{
    "base_directory": "C:\\path\\to\\bots",
    "bot_folders": ["bot1", "bot2", "bot3"],
    "restart_interval": 7200,
    "auto_restart": true,
    "start_minimized": false,
    "log_level": "INFO",
    "capture_output": true
}
```

### bot_manager.log

- System log with actions and errors
- Automatically rotated

## Benefits

- Intuitive Interface: Full visual control
- Advanced Monitoring: Real-time metrics
- Flexibility: Customizable settings
- Stability: Automatic detection and correction of issues
- Community: Open-source for community use
- Detailed Logs: Complete activity tracking
- Multi-threading: Non-blocking operations

## System Requirements

- Windows 7/10/11
- .NET Framework (usually pre-installed)
- Permissions to run programs
- Disk space for logs

## Troubleshooting

**Bot does not start**

- Check if start.exe exists in the bot folder
- Confirm execution permissions
- Check system logs in the Control tab

**Interface not responding**

- Force close via Task Manager
- Look for KoreManager.exe

**Lost settings**

- bot_config.json file may be corrupted
- Delete the file to restore default settings

## Contributions

This project is developed for the community. Contributions, suggestions, and improvements are welcome!

### How to Contribute

- Report bugs or issues
- Suggest new features
- Share code improvements
- Help with documentation

## License

Open-source project for community use. Free to use, modify, and distribute.

## Changelog

### Current Version

✅ Complete graphical interface with tab system
✅ Real-time resource monitoring
✅ Integrated system tray
✅ Multiple log terminals
✅ Configurable auto-restart
✅ Persistent JSON configuration
✅ Drag & drop for reordering
✅ Multi-selection of bots
