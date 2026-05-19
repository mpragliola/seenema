import sys
import winreg

APP_NAME = "Seenema"
_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _get_exe_path() -> str:
    return sys.executable


def enable_autostart(exe_path: str | None = None) -> None:
    if exe_path is None:
        exe_path = _get_exe_path()
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE)
    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{exe_path}"')
    winreg.CloseKey(key)


def disable_autostart() -> None:
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE)
    try:
        winreg.DeleteValue(key, APP_NAME)
    except FileNotFoundError:
        pass
    finally:
        winreg.CloseKey(key)


def is_autostart_enabled() -> bool:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
