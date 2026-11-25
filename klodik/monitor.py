"""Мониторинг ЦП, памяти, видеокарты, диска."""
from .common import *  # noqa: F401,F403
from .apps import *  # noqa: F401,F403
from .winapi import *  # noqa: F401,F403

# ---------- мониторинг (как в MiniLauncher) ----------
class FILETIME(ctypes.Structure):
    _fields_ = [("lo", wt.DWORD), ("hi", wt.DWORD)]


class MEMSTAT(ctypes.Structure):
    _fields_ = [("len", wt.DWORD), ("load", wt.DWORD), ("total", ctypes.c_ulonglong), ("avail", ctypes.c_ulonglong),
                ("pt", ctypes.c_ulonglong), ("pa", ctypes.c_ulonglong), ("vt", ctypes.c_ulonglong),
                ("va", ctypes.c_ulonglong), ("ve", ctypes.c_ulonglong)]


class Stats:
    def __init__(s):
        s._prev = s._times()
        s.cpu = s.ram = 0.0
        s.ram_gb = (0.0, 0.0)
        s.gpu = None        # (загрузка %, температура C)
        s.disk_free = None  # ГБ на C:

    @staticmethod
    def _times():
        i, k, u = FILETIME(), FILETIME(), FILETIME()
        k32.GetSystemTimes(ctypes.byref(i), ctypes.byref(k), ctypes.byref(u))
        v = lambda f: (f.hi << 32) | f.lo
        return v(i), v(k) + v(u)  # kernel включает idle

    def poll(s):
        idle, total = s._times()
        di, dt = idle - s._prev[0], total - s._prev[1]
        s._prev = (idle, total)
        s.cpu = 0.0 if dt <= 0 else max(0.0, min(100.0, 100.0 * (1 - di / dt)))
        m = MEMSTAT()
        m.len = ctypes.sizeof(MEMSTAT)
        k32.GlobalMemoryStatusEx(ctypes.byref(m))
        s.ram, s.ram_gb = m.load, ((m.total - m.avail) / 2**30, m.total / 2**30)

    def poll_slow(s):  # в отдельном потоке: nvidia-smi бывает медленным
        out = run_quiet(["nvidia-smi", "--query-gpu=utilization.gpu,temperature.gpu", "--format=csv,noheader,nounits"],
                        timeout=10).stdout
        try:
            s.gpu = tuple(float(x) for x in out.strip().splitlines()[0].split(","))
        except (ValueError, IndexError):
            s.gpu = None
        s.disk_free = shutil.disk_usage("C:\\").free / 2**30

    def summary(s):
        lines = [f"ЦП {s.cpu:.0f}% · ОЗУ {s.ram:.0f}% ({s.ram_gb[0]:.1f} из {s.ram_gb[1]:.0f} ГБ)"]
        if s.gpu:
            lines.append(f"Видеокарта {s.gpu[0]:.0f}%, {s.gpu[1]:.0f}°C")
        if s.disk_free is not None:
            lines.append(f"Диск C: свободно {s.disk_free:.0f} ГБ")
        return "\n".join(lines)

    def hot(s):
        if s.cpu > 90: return f"Процессор на {s.cpu:.0f}%! Я потею"
        if s.ram > 90: return f"Память забита на {s.ram:.0f}%!"
        if s.gpu and s.gpu[1] > 83: return f"Видеокарта греется: {s.gpu[1]:.0f}°C"
        return ""
