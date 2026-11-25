"""Значок, установка и удаление для Klodik.exe."""
from .common import *  # noqa: F401,F403
from .apps import *  # noqa: F401,F403
from .winapi import *  # noqa: F401,F403
from .monitor import *  # noqa: F401,F403
from .brain import *  # noqa: F401,F403
from .voice import *  # noqa: F401,F403
from .sprites import *  # noqa: F401,F403

# ---------- значок, установка и удаление (для Klodik.exe) ----------
class _PhotoPen:
    """Подставляется в paint() вместо холста: рисует клетки прямо в PhotoImage."""
    def __init__(s, img, k):
        s.img, s.k = img, k

    def create_rectangle(s, x1, y1, x2, y2, fill, outline=""):
        s.img.put(fill, to=(round(x1 * s.k), round(y1 * s.k), round(x2 * s.k), round(y2 * s.k)))


def klodik_photo(size, k):
    img = tk.PhotoImage(width=size, height=size)
    u = size / k
    paint(_PhotoPen(img, k), (u - 16 * C) / 2, (u - 10 * C) / 2, ORANGE, -1, 0, "open", 0, -1, "none")
    return img


def make_icon(path):
    root = tk.Tk()
    root.withdraw()
    tmp = path + ".png"
    klodik_photo(256, 3).write(tmp, format="png")
    with open(tmp, "rb") as f:
        png = f.read()
    os.remove(tmp)
    with open(path, "wb") as f:                          # .ico с одной PNG-картинкой 256×256
        f.write(struct.pack("<HHH", 0, 1, 1) + struct.pack("<BBBBHHII", 0, 0, 0, 0, 1, 32, len(png), 22) + png)
    root.destroy()


def make_lnk(path, target, args=""):
    run_quiet(["powershell", "-NoProfile", "-Command",
               "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:K_L);$s.TargetPath=$env:K_T;"
               "$s.Arguments=$env:K_A;$s.WorkingDirectory=Split-Path $env:K_T;$s.Save()"],
              env={**os.environ, "K_L": path, "K_T": target, "K_A": args}, timeout=30)
    return os.path.exists(path)


def link_paths():
    return {"menu": os.path.join(special_dir(0x02), "Клодик.lnk"),
            "menu_rm": os.path.join(special_dir(0x02), "Удалить Клодика.lnk"),
            "desktop": os.path.join(special_dir(0x10), "Клодик.lnk"),
            "startup": os.path.join(special_dir(0x07), "Клодик.lnk")}


def install_files(src, dest_dir, links, desktop=True, autostart=True):
    os.makedirs(dest_dir, exist_ok=True)
    exe = os.path.join(dest_dir, "Klodik.exe")
    shutil.copy2(src, exe)
    os.makedirs(os.path.dirname(links["menu"]), exist_ok=True)
    ok = make_lnk(links["menu"], exe) and make_lnk(links["menu_rm"], exe, "--uninstall")
    if desktop:
        ok = make_lnk(links["desktop"], exe) and ok
    if autostart:
        ok = make_lnk(links["startup"], exe) and ok
    if not ok:
        raise RuntimeError("не получилось создать ярлыки")
    return exe


def setup_ollama():
    """Ставит Ollama через winget в видимом окне (видно прогресс). Модель потом докачает сам Клодик."""
    if shutil.which("winget"):
        subprocess.Popen(["cmd", "/c", "chcp 65001 >nul & echo Ставлю Ollama — ИИ для болтовни Клодика... & "
                          "winget install -e --id Ollama.Ollama --accept-source-agreements --accept-package-agreements"
                          " & echo. & echo Готово! Окно можно закрыть. Клодик сам докачает модель. & pause"],
                         creationflags=0x10)              # CREATE_NEW_CONSOLE
    else:
        os.startfile("https://ollama.com/download")


def installer():
    root = tk.Tk()
    root.title("Установка Клодика")
    root.resizable(False, False)
    root.configure(bg=PAPER, padx=24, pady=18)
    icon = klodik_photo(96, 1)
    root.iconphoto(True, icon)
    tk.Label(root, image=icon, bg=PAPER).pack()
    tk.Label(root, text="Клодик", font=("Segoe UI", 18, "bold"), bg=PAPER, fg=INK).pack()
    tk.Label(root, text="Маленький помощник, который живёт внизу экрана: открывает программы,\n"
             "разгребает окна бульдозером, ставит таймеры, делает скрины и болтает.",
             bg=PAPER, fg=INK, font=("Segoe UI", 10), justify="center").pack(pady=(4, 12))
    v_auto, v_desk = tk.BooleanVar(value=True), tk.BooleanVar(value=True)
    have_ai = bool(ollama_exe())
    v_ai = tk.BooleanVar(value=not have_ai)
    opts = tk.Frame(root, bg=PAPER)
    opts.pack(anchor="w")
    for var, text in ((v_auto, "Запускать вместе с Windows"), (v_desk, "Ярлык на рабочем столе")):
        tk.Checkbutton(opts, text=text, variable=var, bg=PAPER, font=("Segoe UI", 10)).pack(anchor="w")
    if have_ai:
        tk.Label(opts, text="✓ ИИ для болтовни уже есть на компе", bg=PAPER, fg="#2e7d32",
                 font=("Segoe UI", 10)).pack(anchor="w")
    else:
        tk.Checkbutton(opts, text="Поставить ИИ для болтовни (Ollama, бесплатно, ~3 ГБ)", variable=v_ai, bg=PAPER,
                       font=("Segoe UI", 10)).pack(anchor="w")
        tk.Label(opts, text="Без него Клодик умеет всё, кроме болтовни. При установке принимаются условия Ollama.",
                 bg=PAPER, fg=DARK, font=("Segoe UI", 8)).pack(anchor="w", padx=22)
    status = tk.Label(root, text="", bg=PAPER, fg=DARK, font=("Segoe UI", 10))
    status.pack(pady=(10, 0))

    def go():
        btn.config(state="disabled")
        status.config(text="Ставлю…")
        root.update()
        try:
            run_quiet(["taskkill", "/f", "/im", "Klodik.exe"])        # обновление поверх старой версии
            time.sleep(0.5)
            exe = install_files(sys.executable, INSTALL_DIR, link_paths(), v_desk.get(), v_auto.get())
            if v_ai.get() and not have_ai:
                setup_ollama()
            subprocess.Popen([exe])
        except Exception as e:  # показать человеку, а не молча упасть
            status.config(text=f"Не получилось: {e}", fg="#c62828")
            btn.config(state="normal")
            return
        status.config(text="Готово! Клодик уже бегает внизу экрана.", fg="#2e7d32")
        root.after(3000, root.destroy)
    btn = tk.Button(root, text="Установить", command=go, font=("Segoe UI", 11, "bold"), bg=ORANGE, fg="white",
                    activebackground=DARK, relief="flat", padx=18, pady=6)
    btn.pack(pady=(12, 0))
    root.mainloop()


def uninstall():
    root = tk.Tk()
    root.withdraw()
    if not messagebox.askyesno("Клодик", "Удалить Клодика с компьютера?"):
        return
    for p in link_paths().values():
        if os.path.exists(p):
            os.remove(p)
    shutil.rmtree(DATA_DIR, ignore_errors=True)
    messagebox.showinfo("Клодик", "Клодик удалён. Пока!\nOllama (если ставили) удаляется в «Параметры → Приложения».")
    # сам себя удалить нельзя, пока запущен — это сделает cmd через 2 секунды
    subprocess.Popen(f'cmd /c taskkill /f /im Klodik.exe >nul 2>&1 & timeout /t 2 /nobreak >nul & rmdir /s /q "{INSTALL_DIR}"',
                     creationflags=NOWIN | 0x8)
