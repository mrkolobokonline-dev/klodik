"""Окна Windows и действия с компом (Effects)."""
from .common import *  # noqa: F401,F403
from .apps import *  # noqa: F401,F403

# ---------- окна Windows ----------
EnumProc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)


def proc_name(pid):
    h = k32.OpenProcess(0x1000, False, pid)
    if not h:
        return ""
    buf, n = ctypes.create_unicode_buffer(260), wt.DWORD(260)
    ok = k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n))
    k32.CloseHandle(h)
    return os.path.basename(buf.value) if ok else ""


def app_window(h, me):
    """Обычное окно приложения на экране (не наше, не рабочий стол, не скрытое)? → pid или None."""
    if not u32.IsWindowVisible(h) or u32.GetWindow(h, 4) or u32.GetWindowLongW(h, -20) & 0x80:
        return None
    if not u32.GetWindowTextLengthW(h):
        return None
    cloaked = ctypes.c_int(0)
    ctypes.windll.dwmapi.DwmGetWindowAttribute(h, 14, ctypes.byref(cloaked), 4)
    pid = wt.DWORD()
    u32.GetWindowThreadProcessId(h, ctypes.byref(pid))
    cls = ctypes.create_unicode_buffer(64)
    u32.GetClassNameW(h, cls, 64)
    if cloaked.value or pid.value == me or cls.value in ("Progman", "Shell_TrayWnd", "WorkerW"):
        return None
    return pid.value


def rect_of(h):
    r = wt.RECT()
    if ctypes.windll.dwmapi.DwmGetWindowAttribute(h, 9, ctypes.byref(r), ctypes.sizeof(r)):  # видимая рамка
        u32.GetWindowRect(h, ctypes.byref(r))
    return r.left, r.top, r.right, r.bottom


def frame_rect(h):
    """Рамка окна, если на нём можно стоять (не свёрнуто, не развёрнуто), иначе None."""
    if not u32.IsWindow(h) or not u32.IsWindowVisible(h) or u32.IsIconic(h) or u32.IsZoomed(h):
        return None
    return rect_of(h)


def list_windows():
    me, out = os.getpid(), []

    def cb(h, _):
        pid = app_window(h, me)
        if pid is None:
            return True
        n = u32.GetWindowTextLengthW(h)
        buf = ctypes.create_unicode_buffer(n + 1)
        u32.GetWindowTextW(h, buf, n + 1)
        r = wt.RECT()
        u32.GetWindowRect(h, ctypes.byref(r))
        out.append({"hwnd": h, "title": buf.value[:80], "proc": proc_name(pid),
                    "rect": (r.left, r.top, r.right, r.bottom), "min": bool(u32.IsIconic(h)),
                    "max": bool(u32.IsZoomed(h))})
        return True
    u32.EnumWindows(EnumProc(cb), 0)
    return out


def platforms():
    """Окна сверху вниз по z-порядку: (hwnd, l, t, r, b, можно_стоять)."""
    me, out = os.getpid(), []

    def cb(h, _):
        if app_window(h, me) is None or u32.IsIconic(h):
            return True
        l, t, r, b = rect_of(h)
        out.append((h, l, t, r, b, not u32.IsZoomed(h) and r - l >= 150))
        return True
    u32.EnumWindows(EnumProc(cb), 0)
    return out


class Effects:
    """Всё, что Клодик реально делает с компом (в тесте подменяется)."""
    def close(s, h): u32.PostMessageW(h, 0x10, 0, 0)          # WM_CLOSE: программа может спросить «сохранить?»
    def minimize(s, h): u32.ShowWindow(h, 6)
    def maximize(s, h): u32.ShowWindow(h, 3)
    def move(s, h, x, y): u32.SetWindowPos(h, 0, int(x), int(y), 0, 0, 0x15)   # без размера/z-порядка/фокуса

    def focus(s, h):
        u32.ShowWindow(h, 9)
        u32.SetForegroundWindow(h)

    def start(s, target): os.startfile(target)
    def lock(s): u32.LockWorkStation()
    def restore(s, h): u32.ShowWindow(h, 9)                # для «верни как было» после свернуть/развернуть
    def sleep_pc(s): ctypes.windll.powrprof.SetSuspendState(0, 0, 0)
    def abort_shutdown(s): run_quiet(["shutdown", "/a"])

    def shutdown(s, secs, restart=False):
        run_quiet(["shutdown", "/r" if restart else "/s", "/t", str(int(secs))])

    def paste(s):                                         # Ctrl+V в окно, где сейчас курсор
        for vk, up in ((0x11, 0), (0x56, 0), (0x56, 2), (0x11, 2)):
            u32.keybd_event(vk, 0, up, 0)
    def beep(s): winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS | winsound.SND_ASYNC)

    def keys(s, vk, n=1):
        for _ in range(n):
            u32.keybd_event(vk, 0, 0, 0)
            u32.keybd_event(vk, 0, 2, 0)

    def screenshot(s):
        d = pictures_dir()
        os.makedirs(d, exist_ok=True)
        f = os.path.join(d, time.strftime("Скрин_%Y-%m-%d_%H-%M-%S.png"))
        r = run_quiet(["powershell", "-NoProfile", "-Command", SHOT_PS], env={**os.environ, "PET_SHOT": f},
                      timeout=30)
        if not os.path.exists(f):
            raise RuntimeError((r.stderr or "не сохранилось").strip()[:100])
        return f
