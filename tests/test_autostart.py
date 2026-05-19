from unittest.mock import patch, MagicMock, call
import winreg
from src.autostart import enable_autostart, disable_autostart, is_autostart_enabled

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "Seenema"


def test_enable_autostart_writes_registry():
    mock_key = MagicMock()
    with patch('src.autostart.winreg.OpenKey', return_value=mock_key) as mock_open, \
         patch('src.autostart.winreg.SetValueEx') as mock_set, \
         patch('src.autostart.winreg.CloseKey') as mock_close:
        enable_autostart(r"C:\path\seenema.exe")
        mock_open.assert_called_once_with(
            winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
        )
        mock_set.assert_called_once_with(
            mock_key, APP_NAME, 0, winreg.REG_SZ, r'"C:\path\seenema.exe"'
        )
        mock_close.assert_called_once_with(mock_key)


def test_disable_autostart_deletes_registry():
    mock_key = MagicMock()
    with patch('src.autostart.winreg.OpenKey', return_value=mock_key), \
         patch('src.autostart.winreg.DeleteValue') as mock_del, \
         patch('src.autostart.winreg.CloseKey'):
        disable_autostart()
        mock_del.assert_called_once_with(mock_key, APP_NAME)


def test_disable_autostart_ignores_missing_key():
    mock_key = MagicMock()
    with patch('src.autostart.winreg.OpenKey', return_value=mock_key), \
         patch('src.autostart.winreg.DeleteValue', side_effect=FileNotFoundError), \
         patch('src.autostart.winreg.CloseKey'):
        disable_autostart()  # must not raise


def test_is_autostart_enabled_returns_true_when_key_exists():
    mock_key = MagicMock()
    with patch('src.autostart.winreg.OpenKey', return_value=mock_key), \
         patch('src.autostart.winreg.QueryValueEx', return_value=(r'"C:\seenema.exe"', 1)), \
         patch('src.autostart.winreg.CloseKey'):
        assert is_autostart_enabled() is True


def test_is_autostart_enabled_returns_false_when_key_missing():
    with patch('src.autostart.winreg.OpenKey', side_effect=FileNotFoundError):
        assert is_autostart_enabled() is False
