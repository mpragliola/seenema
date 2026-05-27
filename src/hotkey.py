import ctypes
import ctypes.wintypes
import threading
from collections.abc import Callable

WH_MOUSE_LL = 14
WM_MOUSEWHEEL = 0x020A
WM_QUIT = 0x0012
VK_CONTROL = 0x11
VK_SHIFT = 0x10

HOOKPROC = ctypes.WINFUNCTYPE(
    ctypes.c_longlong,
    ctypes.c_int,
    ctypes.wintypes.WPARAM,
    ctypes.wintypes.LPARAM,
)


class _MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ('pt', ctypes.wintypes.POINT),
        ('mouseData', ctypes.wintypes.DWORD),
        ('flags', ctypes.wintypes.DWORD),
        ('time', ctypes.wintypes.DWORD),
        ('dwExtraInfo', ctypes.c_uint64),
    ]


def adjust_opacity(current: float, direction: int) -> float:
    """Round current to the nearest 5%, step by direction * 5%, clamp to [0.05, 1.0]."""
    snapped = round(current * 20) / 20
    new = snapped + direction * 0.05
    return max(0.05, min(1.0, new))


class WheelHook:
    """Global low-level mouse hook; fires on_step(+1 or -1) on Ctrl+Shift+Wheel."""

    def __init__(self, on_step: Callable[[int], None]) -> None:
        self._on_step = on_step
        self._hook = None
        self._thread_id: int = 0
        self._proc = None  # hold reference so WINFUNCTYPE wrapper is not GC'd
        self._ready: threading.Event | None = None
        self._error: OSError | None = None

    def start(self) -> None:
        """Install the hook on a new daemon thread with its own message pump."""
        if self._thread_id:
            return  # already running
        self._ready = threading.Event()
        thread = threading.Thread(target=self._thread_main, daemon=True)
        thread.start()
        self._ready.wait()
        if self._error:
            raise self._error

    def stop(self) -> None:
        """Post WM_QUIT to the hook thread to unwind its message pump."""
        if self._thread_id:
            ctypes.windll.user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
            self._thread_id = 0

    def _hook_proc(self, nCode: int, wParam: int, lParam: int) -> int:
        # Low-level hook procs have a hard timeout (~300 ms); any real work must be
        # dispatched asynchronously.  For Ctrl+Shift+Wheel we return 1 to capture the
        # event (preventing it from reaching other hooks and the target window).
        if nCode >= 0 and wParam == WM_MOUSEWHEEL:
            ctrl = ctypes.windll.user32.GetAsyncKeyState(VK_CONTROL) & 0x8000
            shift = ctypes.windll.user32.GetAsyncKeyState(VK_SHIFT) & 0x8000
            if ctrl and shift:
                info = ctypes.cast(lParam, ctypes.POINTER(_MSLLHOOKSTRUCT)).contents
                raw_delta = ctypes.c_short(info.mouseData >> 16).value
                direction = 1 if raw_delta > 0 else -1
                # Fire the callback on a separate thread so this proc returns instantly.
                threading.Thread(target=self._on_step, args=(direction,), daemon=True).start()
                return 1  # captured — do not pass to other hooks or target window
        return ctypes.windll.user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

    def _thread_main(self) -> None:
        # Set argtypes/restype so ctypes passes the 64-bit lParam pointer correctly.
        ctypes.windll.user32.CallNextHookEx.argtypes = [
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.wintypes.WPARAM,
            ctypes.wintypes.LPARAM,
        ]
        ctypes.windll.user32.CallNextHookEx.restype = ctypes.c_longlong
        self._proc = HOOKPROC(self._hook_proc)
        self._hook = ctypes.windll.user32.SetWindowsHookExW(
            WH_MOUSE_LL, self._proc, None, 0
        )
        if not self._hook:
            self._error = ctypes.WinError()
            self._ready.set()
            return
        self._thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
        self._ready.set()
        msg = ctypes.wintypes.MSG()
        while ctypes.windll.user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
            ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))
        ctypes.windll.user32.UnhookWindowsHookEx(self._hook)
        self._hook = None
