# autostart.py — Windows Run-key autostart management.
#
# Registers or removes the app from HKCU\Software\Microsoft\Windows\CurrentVersion\Run
# so Windows launches it automatically at login for the current user only (no UAC prompt
# required, as HKCU is writable without elevation).
#
# The registered value stores the full quoted path to the executable.  Quoting is
# necessary because Windows launches Run-key entries via CreateProcess, which would
# misparse paths containing spaces if they were unquoted.

import sys
import winreg

# The value name under the Run key — must be unique per application.
APP_NAME = "Seenema"

# HKCU registry path that Windows reads at login to auto-launch user applications.
_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _get_exe_path() -> str:
    # sys.executable resolves to the .exe when frozen by PyInstaller, and to the
    # Python interpreter path when running from source.  The latter is intentional:
    # running from source is a developer workflow and autostart is still testable.
    return sys.executable


def enable_autostart(exe_path: str | None = None) -> None:
    """Write an entry to the Run key so the app starts with Windows.

    `exe_path` defaults to sys.executable; it can be overridden in tests or when
    the caller knows the path to the installed binary (e.g. post-installer setup).

    The path is wrapped in double-quotes to handle spaces in directory names.
    """
    if exe_path is None:
        exe_path = _get_exe_path()

    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE)
    # REG_SZ stores the value as a plain Unicode string; quoting the path is required
    # for CreateProcess to handle paths with spaces correctly.
    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{exe_path}"')
    winreg.CloseKey(key)


def disable_autostart() -> None:
    """Remove the app's entry from the Run key if it exists.

    Silently does nothing if the key is already absent — this makes the function safe
    to call unconditionally without checking is_autostart_enabled() first.
    """
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE)
    try:
        winreg.DeleteValue(key, APP_NAME)
    except FileNotFoundError:
        # The value was never written or was already deleted; nothing to do.
        pass
    finally:
        # Always close the key handle regardless of whether DeleteValue succeeded.
        winreg.CloseKey(key)


def is_autostart_enabled() -> bool:
    """Return True if the app's Run key entry currently exists.

    Used at startup to synchronise AppState.autostart with the actual registry value,
    in case the user manually edited the registry or another tool removed the entry.
    """
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_READ)
        # QueryValueEx raises FileNotFoundError if the named value does not exist.
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        # Either the Run key itself or the APP_NAME value is missing — autostart is off.
        return False
