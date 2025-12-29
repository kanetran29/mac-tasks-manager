# macOS Task Manager

A lightweight terminal-based task manager for macOS with **mouse support** built with Python and [Textual](https://textual.textualize.io/).

![Task Manager Screenshot](docs/screenshot.png)

## Features

- **Real-time CPU monitoring** - Total usage, per-core breakdown
- **Memory monitoring** - RAM, Swap, available memory
- **Process listing** - Top processes sorted by CPU usage
- **Search** - Filter processes by name or PID
- **Kill processes** - Click to select, then kill with SIGKILL
- **Mouse support** - Clickable buttons and selectable rows

## Installation

```bash
# Clone the repo
git clone https://github.com/kanetran29/mac-tasks-manager.git
cd mac-tasks-manager

# Install dependencies
pip3 install psutil rich textual
```

## Usage

### Option 1: Double-click the app

Double-click `TaskManager.command` or `TaskManager.app`

### Option 2: Run from terminal

```bash
python3 task_manager.py
```

## Controls

| Key/Action   | Description           |
| ------------ | --------------------- |
| Click row    | Select a process      |
| 🔍 / `s`     | Search processes      |
| ✖ / `c`      | Clear search          |
| ☠ Kill / `k` | Kill selected process |
| ↻ / `r`      | Refresh               |
| `q`          | Quit                  |

## Requirements

- macOS 14+
- Python 3.10+
- psutil
- rich
- textual

## License

MIT
