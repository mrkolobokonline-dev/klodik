"""Запуск: сторож-перезапуск, установка, обычный старт."""
from .common import *  # noqa: F401,F403
from .apps import *  # noqa: F401,F403
from .winapi import *  # noqa: F401,F403
from .monitor import *  # noqa: F401,F403
from .brain import *  # noqa: F401,F403
from .voice import *  # noqa: F401,F403
from .sprites import *  # noqa: F401,F403
from .install import *  # noqa: F401,F403

from .pet import Pet


def main():
    if "--selftest" in sys.argv:
        from .selftest import selftest
        if not FROZEN:
            return selftest()
        import traceback                                  # в .exe без консоли пишем итог в файл
        with open(os.path.join(os.environ.get("TEMP", HERE), "klodik_selftest.txt"), "w", encoding="utf-8") as f:
            sys.stdout = f
            try:
                selftest()
            except BaseException:
                traceback.print_exc(file=f)
        return
    if "--make-icon" in sys.argv:
        return make_icon(sys.argv[-1])
    if "--plugin" in sys.argv:                              # плагин — в отдельном процессе (и в .exe тоже)
        import runpy
        i = sys.argv.index("--plugin")
        path, text = sys.argv[i + 1], (sys.argv[i + 2] if len(sys.argv) > i + 2 else "")
        if sys.stdout is None:                                # .exe без консоли: пишем в трубу, которую дал Клодик
            try:
                sys.stdout = sys.stderr = open(1, "w", encoding="utf-8", closefd=False)
            except OSError:
                sys.stdout = sys.stderr = open(os.devnull, "w")
        sys.argv = [path, text]
        return runpy.run_path(path, run_name="__main__")
    if "--uninstall" in sys.argv:
        return uninstall()
    if FROZEN and os.path.normcase(sys.executable) != os.path.normcase(os.path.join(INSTALL_DIR, "Klodik.exe")):
        return installer()                                   # запустили скачанный файл — это установка
    if "--child" not in sys.argv:
        ctypes.windll.kernel32.CreateMutexW(None, False, "ClaudikPetMutex")
        if ctypes.windll.kernel32.GetLastError() == 183:        # уже запущен
            return
        return supervise()
    ctypes.windll.winmm.timeBeginPeriod(1)                      # точные таймеры для 144 Гц
    root = tk.Tk()
    root.report_callback_exception = lambda *exc: log_error("".join(traceback.format_exception(*exc)))
    Pet(root)
    root.mainloop()


def supervise():
    """Сторож: запускает Клодика и поднимает его снова, если тот упал (выход не через «Выход»)."""
    cmd = [sys.executable] + ([] if FROZEN else [os.path.abspath(sys.argv[0])]) + ["--child"]
    falls = []
    while True:
        code = subprocess.call(cmd)
        if code == 0:
            return
        now = time.time()
        falls = [t for t in falls if now - t < 600] + [now]
        log_error(f"Клодик упал (код {code}), перезапускаю")
        if len(falls) > 5:                                     # падает по кругу — не насилуем комп
            log_error("Падает слишком часто — остановился. Нужна починка.")
            return
        time.sleep(2)
