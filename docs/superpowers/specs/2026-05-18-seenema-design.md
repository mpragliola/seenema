# Seenema — Design Spec

**Date:** 2026-05-18  
**Stack:** Python + pystray + tkinter + ctypes + PyInstaller  
**Target:** Windows 10/11, multi-monitor setups only

---

## Overview

Seenema is a Windows system tray application that dims all monitors except a chosen "main" display. The goal is to watch a movie on one screen while keeping other screens barely visible. Overlays are click-through — mouse events pass to windows beneath them. Dimming is toggled via the tray icon.

---

## Architecture & Components

Single Python process, four modules:

| File | Responsibility |
|------|---------------|
| `main.py` | Entry point; wires components; starts tkinter main loop |
| `tray.py` | `pystray` icon and menu; dispatches user actions |
| `overlay.py` | Manages one `tkinter.Toplevel` per dimmed monitor; applies Win32 click-through style |
| `monitor.py` | Queries connected monitors via `screeninfo`; identifies by device name; polls for changes |
| `config.py` | Reads/writes `config.json` next to the exe |

State is held in a small shared object. `pystray` runs in its own thread; tkinter runs on the main thread. Cross-thread communication uses simple callbacks registered at startup.

---

## Tray Menu

```
● Dim ON / ○ Dim OFF
─────────────────────────────
Main display: [DISPLAY1 ▾]
─────────────────────────────
Opacity: 90%  [−] [+]
─────────────────────────────
□ Start with Windows
─────────────────────────────
Quit
```

**Rules:**
- Left-click on tray icon toggles dim on/off (same as menu toggle)
- If only 1 monitor is detected, "Dim ON" is greyed out
- `main_display` is `null` on first launch; user must select one before dim can be enabled
- Changing main display while dim is active: immediately removes overlay from new main, adds it to old main
- Opacity changes in steps of 5%, range 10–100%, applied live to all visible overlays
- Autostart writes/removes `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\Seenema`

---

## Overlay Windows

One `tkinter.Toplevel` per dimmed monitor. Properties:

- **Position/size:** exactly matches monitor bounds (handles non-zero offsets for secondary monitors)
- **Color:** `#000000` (pure black)
- **Transparency:** `wm_attributes('-alpha', opacity)` — tkinter built-in alpha
- **Click-through:** `ctypes` sets `WS_EX_TRANSPARENT | WS_EX_LAYERED` on the window HWND after creation
- **No chrome:** `wm_overrideredirect(True)` removes title bar, border, taskbar entry
- **Always on top:** `wm_attributes('-topmost', True)`

Overlays are created once and toggled with `deiconify`/`withdraw` — not destroyed and recreated — so Win32 attributes persist across toggles.

---

## Monitor Detection

- Uses `screeninfo.get_monitors()` to enumerate monitors
- Identifies monitors by device name (e.g. `\\.\DISPLAY2`)
- Polls every 5 seconds for monitor list changes
- On change: overlays are rebuilt; config is re-evaluated (if saved main display is no longer present, dim is disabled and user is notified via tray tooltip)

---

## Config

`config.json` next to the exe, created on first run:

```json
{
  "main_display": null,
  "opacity": 0.90,
  "autostart": false
}
```

Written immediately on any user change (no explicit save step).

---

## Packaging

- **PyInstaller** `--onefile --noconsole --windowed` → single `seenema.exe`
- Icon embedded via `--icon=assets/icon.ico`
- `build.bat` in repo root handles the PyInstaller invocation
- **Runtime dependencies:** `pystray`, `Pillow` (required by pystray), `screeninfo`

---

## Out of Scope

- Per-monitor opacity settings (all dimmed monitors share one opacity value)
- Hotkey support
- Mac/Linux support
