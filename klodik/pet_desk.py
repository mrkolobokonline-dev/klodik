"""Этап 5 (блоки E, D, J, K): помодоро, история буфера, стикеры, палитра Alt+Space, тайм-трекер программ, погода и курс,
«что это за ошибка» (локально), окна по сетке/поверх/вернуть пропавшие, монитор, порты и зависшие программы (только показ,
завершение — после «да»), разбор загрузок, ffmpeg, пинг; проекты, идеи для игр, проверка ботов, «на добраніч»;
режим отключения света (питание от батареи/ИБП) и охранник автозапуска. Всё локально; удаление — только в корзину."""
import collections
import datetime as dt

from .common import *  # noqa: F401,F403
from .pet_tasks import read_json, write_json
from . import tools as T

CLIPS = os.path.join(DATA_DIR, "clips.json")
STICKERS = os.path.join(DATA_DIR, "stickers.json")
TRACK = os.path.join(DATA_DIR, "apptime.json")
PROJECTS = os.path.join(DATA_DIR, "projects.json")
IDEAS = os.path.join(DATA_DIR, "ideas.json")
GUARD = os.path.join(DATA_DIR, "autostart_seen.json")
SECRET = re.compile(r"^(?=.*\d)(?=.*[A-Za-z])\S{8,64}$|\b(?:\d[ -]?){13,19}\b|-----BEGIN|password|пароль|api[_-]?key|token",
                    re.I)                                 # похожее на пароль, карту, ключ — в историю не кладём
PASS_APPS = ("keepass", "1password", "bitwarden", "lastpass", "dashlane", "enpass")
KINDS = {"Фото": (".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".bmp"), "Видео": (".mp4", ".mkv", ".mov", ".avi", ".webm"),
         "Архивы": (".zip", ".rar", ".7z", ".tar", ".gz"), "Документы": (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".txt", ".pptx"),
         "Программы": (".exe", ".msi"), "Музыка": (".mp3", ".wav", ".flac", ".ogg", ".m4a")}
WEATHER_CODES = {0: "ясно", 1: "почти ясно", 2: "переменная облачность", 3: "пасмурно", 45: "туман", 48: "туман",
                 51: "морось", 61: "дождь", 63: "дождь", 65: "ливень", 71: "снег", 73: "снег", 75: "сильный снег",
                 80: "ливни", 95: "гроза"}


class SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [("ACLineStatus", ctypes.c_ubyte), ("BatteryFlag", ctypes.c_ubyte), ("BatteryLifePercent", ctypes.c_ubyte),
                ("SystemStatusFlag", ctypes.c_ubyte), ("BatteryLifeTime", ctypes.c_ulong), ("BatteryFullLifeTime", ctypes.c_ulong)]


def power_status():
    """(от сети?, процент или None, минут осталось или None). Батарея ноутбука или ИБП, который Windows видит как батарею."""
    st = SYSTEM_POWER_STATUS()
    k32.GetSystemPowerStatus(ctypes.byref(st))
    pct = None if st.BatteryLifePercent == 255 or st.BatteryFlag == 128 else st.BatteryLifePercent
    mins = None if st.BatteryLifeTime == 0xFFFFFFFF else st.BatteryLifeTime // 60
    return st.ACLineStatus != 0, pct, mins


def grid(n, area):
    """n окон → прямоугольники сетки (почти квадратной) внутри рабочей области."""
    L, Tp, R, B = area
    cols = max(1, math.ceil(math.sqrt(n)))
    rows = max(1, math.ceil(n / cols))
    w, h = (R - L) // cols, (B - Tp) // rows
    return [(L + (i % cols) * w, Tp + (i // cols) * h, w, h) for i in range(n)]


def sort_plan(folder):
    """Файлы в корне папки → (откуда, куда) по типу. Ничего не удаляет."""
    out = []
    for f in os.listdir(folder):
        p = os.path.join(folder, f)
        if not os.path.isfile(p):
            continue
        ext = os.path.splitext(f)[1].lower()
        for kind, exts in KINDS.items():
            if ext in exts:
                out.append((p, os.path.join(folder, kind, f)))
                break
    return out


def listening_ports():
    """Кто слушает порты: [(порт, процесс)] — только показ."""
    r = run_quiet(["netstat", "-ano", "-p", "TCP"], encoding="oem", errors="replace", timeout=20)
    from .winapi import proc_name
    seen = {}
    for line in (r.stdout or "").splitlines():
        cols = line.split()
        if len(cols) >= 5 and cols[3].upper() in ("LISTENING", "ПРОСЛУШИВАНИЕ"):
            port = cols[1].rsplit(":", 1)[-1]
            seen.setdefault(int(port), proc_name(int(cols[4])) or ("Windows" if cols[4] in ("0", "4") else "служба Windows"))
    return sorted(seen.items())


def hung_windows():
    from .winapi import list_windows
    return [w for w in list_windows() if u32.IsHungAppWindow(w["hwnd"])]


class PetDesk:
    def desk_load(s):
        s.clips = read_json(CLIPS, [])
        s.last_clip, s.pomo, s.stickers = "", None, []
        s.track = read_json(TRACK, {})
        s.projects = read_json(PROJECTS, [])
        s.on_battery = None
        s.alt_space = False
        s.root.after(1500, s.load_stickers)

    # ---------- помодоро ----------
    def pomodoro(s, stop=False):
        if stop:
            s.pomo = None
            return s.say("Помодоро остановил.", 3, speak=True)
        s.pomo = {"phase": "work", "end": time.time() + 25 * 60, "n": 0}
        s.emote("interest", "medium")
        s.say("Помодоро: 25 минут работы. Я помолчу и скажу, когда перерыв.", 5, speak=True)
        s.prefs["working"] = True

    def pomo_tick(s):
        p = s.pomo
        if not p or time.time() < p["end"]:
            return
        if p["phase"] == "work":
            p["n"] += 1
            long_break = p["n"] % 4 == 0
            p["phase"], p["end"] = "break", time.time() + (15 if long_break else 5) * 60
            s.prefs["working"] = False
            s.emote("joy", "medium")
            s.say(f"Перерыв {'15' if long_break else '5'} минут! Разомнись и попей воды.", 8, speak=True)
            s.fx.beep()
        else:
            p["phase"], p["end"] = "work", time.time() + 25 * 60
            s.prefs["working"] = True
            s.say("Перерыв окончен — снова 25 минут работы.", 5, speak=True)
            s.fx.beep()

    # ---------- история буфера (выкл. по умолчанию) ----------
    def clip_tick(s):
        if not s.on("clip_history"):
            return
        try:
            text = s.root.clipboard_get()
        except tk.TclError:
            return
        if not text or text == s.last_clip:
            return
        s.last_clip = text
        from .winapi import proc_name
        pid = wt.DWORD()
        u32.GetWindowThreadProcessId(u32.GetForegroundWindow(), ctypes.byref(pid))
        if SECRET.search(text.strip()) or any(a in (proc_name(pid.value) or "").lower() for a in PASS_APPS):
            return
        s.clips = ([c for c in s.clips if c["t"] != text] + [{"t": text[:2000], "at": time.time()}])[-30:]
        keep = s.prefs.get("clip_days", 1) * 86400
        s.clips = [c for c in s.clips if time.time() - c["at"] < keep]
        write_json(CLIPS, s.clips)

    def clips_window(s):
        w = tk.Toplevel(s.root)
        w.title("История буфера")
        w.attributes("-topmost", True)
        box = tk.Listbox(w, width=80, height=15, font=("Segoe UI", 9))
        box.pack(fill="both", expand=True, padx=8, pady=6)
        for c in reversed(s.clips):
            box.insert("end", c["t"].replace("\n", " ⏎ ")[:120])

        def copy(_=None):
            if box.curselection():
                t = list(reversed(s.clips))[box.curselection()[0]]["t"]
                s.last_clip = t
                s.root.clipboard_clear()
                s.root.clipboard_append(t)
                w.destroy()
                s.say("Скопировал — вставь Ctrl+V.", 3)

        def clear():
            s.clips = []
            write_json(CLIPS, [])
            w.destroy()
            s.say("Историю буфера стёр.", 3)
        box.bind("<Double-Button-1>", copy)
        row = tk.Frame(w)
        row.pack(fill="x", padx=8, pady=(0, 8))
        tk.Button(row, text="Скопировать", command=copy).pack(side="left")
        tk.Button(row, text="Очистить", command=clear).pack(side="right")
        return w

    # ---------- стикеры на рабочем столе ----------
    def sticker(s, text, x=None, y=None, save=True):
        w = tk.Toplevel(s.root)
        w.overrideredirect(True)
        w.attributes("-topmost", True)
        w.configure(bg="#fff3a8")
        x = x if x is not None else s.R - 230 - 30 * (len(s.stickers) % 6)
        y = y if y is not None else s.T + 40 + 30 * (len(s.stickers) % 6)
        w.geometry(f"+{x}+{y}")
        lab = tk.Label(w, text=text, bg="#fff3a8", fg=INK, wraplength=200, justify="left", font=("Segoe UI", 10), padx=8, pady=6)
        lab.pack()
        item = {"t": text, "x": x, "y": y, "w": w}
        s.stickers.append(item)
        drag = {}

        def press(e):
            drag["d"] = (e.x_root - w.winfo_x(), e.y_root - w.winfo_y())

        def move(e):
            item["x"], item["y"] = e.x_root - drag["d"][0], e.y_root - drag["d"][1]
            w.geometry(f"+{item['x']}+{item['y']}")

        def kill(_=None):
            s.stickers.remove(item)
            w.destroy()
            s.save_stickers()
        lab.bind("<ButtonPress-1>", press)
        lab.bind("<B1-Motion>", move)
        lab.bind("<ButtonRelease-1>", lambda e: s.save_stickers())
        lab.bind("<Button-3>", kill)                      # правый клик — снять стикер
        if save:
            s.save_stickers()
        return w

    def save_stickers(s):
        write_json(STICKERS, [{k: i[k] for k in ("t", "x", "y")} for i in s.stickers])

    def load_stickers(s):
        for i in read_json(STICKERS, []):
            s.sticker(i["t"], i["x"], i["y"], save=False)

    # ---------- командная палитра Alt+Space ----------
    def palette_tick(s):
        down = bool(u32.GetAsyncKeyState(0x12) & 0x8000) and bool(u32.GetAsyncKeyState(0x20) & 0x8000)
        if down and not s.alt_space and not s.gaming:
            s.open_input()
        s.alt_space = down

    # ---------- тайм-трекер программ ----------
    def track_tick(s, secs):
        if not s.on("tracker") or idle_away():
            return
        from .winapi import proc_name
        pid = wt.DWORD()
        u32.GetWindowThreadProcessId(u32.GetForegroundWindow(), ctypes.byref(pid))
        name = (proc_name(pid.value) or "").replace(".exe", "")
        if not name or name.lower() in ("explorer", "pythonw", "python", "klodik"):
            return
        day = s.track.setdefault(dt.date.today().isoformat(), {})
        day[name] = day.get(name, 0) + secs
        for d in [d for d in s.track if d < (dt.date.today() - dt.timedelta(days=14)).isoformat()]:
            del s.track[d]
        if random.random() < 0.1:
            write_json(TRACK, s.track)

    def track_report(s, days=7, day=None):
        tot = collections.Counter()
        keys = [day] if day else [(dt.date.today() - dt.timedelta(days=i)).isoformat() for i in range(days)]
        for k in keys:
            tot.update(s.track.get(k, {}))
        if not tot:
            return "Пока ничего не насчитал."
        return ", ".join(f"{n} — {fmt_secs(t)}" for n, t in tot.most_common(5))

    def track_clear(s):
        s.track = {}
        write_json(TRACK, {})
        s.say("Тайм-трекер стёр.", 3, speak=True)

    # ---------- погода и курс (бесплатные API без ключей) ----------
    def weather_rates(s, what):
        def go():
            try:
                if what == "weather":
                    url = ("https://api.open-meteo.com/v1/forecast?latitude=50.45&longitude=30.52"
                           "&current=temperature_2m,weather_code&daily=temperature_2m_max,temperature_2m_min&timezone=auto"
                           "&forecast_days=1")
                    d = json.load(urllib.request.urlopen(url, timeout=10))
                    c, dl = d["current"], d["daily"]
                    msg = (f"В Киеве сейчас {c['temperature_2m']:+.0f}°, {WEATHER_CODES.get(c['weather_code'], 'облачно')}; "
                           f"днём {dl['temperature_2m_min'][0]:+.0f}…{dl['temperature_2m_max'][0]:+.0f}°.")
                else:
                    d = json.load(urllib.request.urlopen(
                        "https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?json", timeout=10))
                    r = {x["cc"]: x["rate"] for x in d}
                    msg = f"Курс НБУ: доллар {r['USD']:.2f} ₴, евро {r['EUR']:.2f} ₴."
            except (OSError, ValueError, KeyError) as e:
                msg = f"Не достал данные (нет интернета?): {str(e)[:60]}"
            s.answers.put(("info_say", msg))
        threading.Thread(target=go, daemon=True).start()

    # ---------- «что это за ошибка?» — буфер или скрин, только локальная модель ----------
    def explain_error(s):
        try:
            text = s.root.clipboard_get().strip()
        except tk.TclError:
            text = ""
        looks_err = re.search(r"error|exception|traceback|ошибк|failed|не удалось|denied|0x[0-9a-f]{6,}", text, re.I)
        s.thinking = True
        sys_p = ("Ты Клодик, помощник по компьютеру. По-русски, простыми словами: что это за ошибка (1–2 фразы) и решение "
                 "в 3–5 коротких пронумерованных шагах. Если не уверен — так и скажи. Не выдумывай.")

        def go():
            try:
                if looks_err:
                    out = s.ai.ask(sys_p, text[:4000], task="explain", private=True, tokens=500)
                else:
                    shot = s.fx.screenshot()                # скрин остаётся на компе, смотрит локальная модель
                    out = s.ai.ask(sys_p, "На скриншоте ошибка. Объясни её.", task="explain", private=True,
                                   tokens=500, image=shot)
                s.answers.put(("clip_say", out))
                s.kb_add_error(text[:200] if looks_err else "ошибка со скрина", out[:300])
            except (OSError, ValueError, KeyError, RuntimeError) as e:
                s.answers.put(("clip_say", f"Не смог разобрать: {str(e)[:80]}. Скопируй текст ошибки (Ctrl+C) и спроси ещё раз."))
        threading.Thread(target=go, daemon=True).start()

    def kb_add_error(s, problem, answer):
        from .pet_brain import KB
        kb = read_json(KB, [])
        kb.append({"problem": problem, "solution": answer, "t": time.time(), "kind": "error"})
        write_json(KB, kb[-200:])

    # ---------- окна ----------
    def arrange(s):
        from .winapi import list_windows
        ws = [w for w in list_windows() if not w["min"]][:9]
        if not ws:
            return s.say("Нечего раскладывать.", 2)
        old = [(w["hwnd"], w["rect"]) for w in ws]
        for w, (x, y, cw, ch) in zip(ws, grid(len(ws), (s.L, s.T, s.R, s.B))):
            u32.ShowWindow(w["hwnd"], 9)                   # SW_RESTORE
            u32.SetWindowPos(w["hwnd"], 0, x, y, cw, ch, 0x0014)
        s.push_undo("раскладка окон", lambda: [u32.SetWindowPos(h, 0, r[0], r[1], r[2] - r[0], r[3] - r[1], 0x0014)
                                                for h, r in old])
        s.log("arrange_windows", f"{len(ws)} окон по сетке", "готово")
        s.say(f"Разложил {len(ws)} окон по сетке. «Верни как было» — откачу.", 4, speak=True)

    def window_op(s, op):
        h = u32.GetForegroundWindow()
        if op == "max":
            u32.ShowWindow(h, 3)
        elif op in ("pin", "unpin"):
            u32.SetWindowPos(h, -1 if op == "pin" else -2, 0, 0, 0, 0, 0x0003)
            s.say("Закрепил окно поверх всех." if op == "pin" else "Открепил окно.", 3)
        elif op == "rescue":
            from .winapi import list_windows
            n = 0
            for w in list_windows():
                l, t, r, b = w["rect"]
                if not w["min"] and (r < 50 or l > s.R - 50 or b < 30 or t > s.B - 30):
                    u32.SetWindowPos(w["hwnd"], 0, s.L + 80, s.T + 80, 0, 0, 0x0015)
                    n += 1
            s.say(f"Вернул окон: {n}." if n else "Потерянных окон не нашёл.", 3, speak=True)

    def monitor_off(s):
        s.say("Гашу монитор. Двинь мышку — включится.", 2)
        s.root.after(1500, lambda: u32.PostMessageW(0xFFFF, 0x0112, 0xF170, 2))

    # ---------- система: порты, зависшие, пинг ----------
    def show_ports(s):
        def go():
            ports = listening_ports()
            s.answers.put(("info_say", "Слушают порты: " + ", ".join(f"{p} ({n})" for p, n in ports[:12])
                           + ("…" if len(ports) > 12 else "") + ". Я только показываю, ничего не закрываю."))
        threading.Thread(target=go, daemon=True).start()

    def hung(s):
        hs = hung_windows()
        if not hs:
            return s.say("Зависших программ нет.", 3, speak=True)
        w = hs[0]
        pid = wt.DWORD()
        u32.GetWindowThreadProcessId(w["hwnd"], ctypes.byref(pid))
        s.gate("close_app", f"завершить зависшую «{w['title'] or w['proc']}» (несохранённое пропадёт)",
               lambda: run_quiet(["taskkill", "/PID", str(pid.value), "/F"], timeout=15))

    def ping(s):
        def go():
            out = []
            for name, host in (("Google", "8.8.8.8"), ("Cloudflare", "1.1.1.1"), ("Steam", "steamcommunity.com")):
                r = run_quiet(["ping", "-n", "3", "-w", "1500", host], encoding="oem", errors="replace", timeout=20)
                m = re.findall(r"(?:time|время)[=<](\d+)", r.stdout or "")
                out.append(f"{name} {round(sum(map(int, m)) / len(m))} мс" if m else f"{name} не отвечает")
            s.answers.put(("info_say", "Пинг: " + ", ".join(out) + "."))
        threading.Thread(target=go, daemon=True).start()

    # ---------- файлы: разбор загрузок, ffmpeg ----------
    def sort_downloads(s):
        folder = os.path.join(os.path.expanduser("~"), "Downloads")
        plan = sort_plan(folder)
        if not plan:
            return s.say("В загрузках разбирать нечего.", 3, speak=True)
        kinds = collections.Counter(os.path.basename(os.path.dirname(b)) for _, b in plan)

        def do():
            done = []
            for a, b in plan:
                os.makedirs(os.path.dirname(b), exist_ok=True)
                if not os.path.exists(b):
                    shutil.move(a, b)
                    done.append((a, b))
            s.push_undo("разбор загрузок", lambda: [shutil.move(b, a) for a, b in done if os.path.exists(b)])
            s.say(f"Разложил {len(done)} файлов по папкам. «Верни как было» — верну.", 4, speak=True)
        s.gate("move_files", "разложить загрузки по папкам: " + ", ".join(f"{k} {n}" for k, n in kinds.items()), do)

    def ffmpeg(s, how):
        exe = shutil.which("ffmpeg")
        if not exe:
            return s.say("Не нашёл ffmpeg. Скажи «установи ffmpeg» — поставлю через winget.", 5, speak=True)
        vids = KINDS["Видео"] if how in ("tg", "mp4") else KINDS["Фото"]
        roots = [os.path.join(os.path.expanduser("~"), d) for d in ("Downloads", "Videos", "Pictures", "Desktop")]
        files = [os.path.join(r, f) for r in roots if os.path.isdir(r) for f in os.listdir(r) if f.lower().endswith(vids)]
        if not files:
            return s.say("Не нашёл подходящий файл в Загрузках, Видео, Изображениях и на столе.", 4, speak=True)
        src = max(files, key=os.path.getmtime)
        base = os.path.splitext(src)[0]
        dst, args = {"tg": (base + "_tg.mp4", ["-vf", "scale=-2:720", "-c:v", "libx264", "-crf", "28", "-preset", "veryfast",
                                               "-c:a", "aac", "-b:a", "96k"]),
                     "mp4": (base + "_conv.mp4", ["-c:v", "libx264", "-crf", "23", "-c:a", "aac"]),
                     "img": (base + "_small.jpg", ["-vf", "scale='min(1600,iw)':-2", "-q:v", "4"])}[how]

        def go():
            r = run_quiet([exe, "-y", "-i", src, *args, dst], timeout=1800)
            s.answers.put(("info_say", f"Готово: {os.path.basename(dst)} рядом с исходником." if os.path.exists(dst)
                           else f"ffmpeg не справился: {(r.stderr or '')[-120:]}"))
        s.gate("convert_file", f"сделать из «{os.path.basename(src)}» файл «{os.path.basename(dst)}» (исходник не трогаю)",
               lambda: (s.say("Конвертирую… скажу, когда готово.", 3), threading.Thread(target=go, daemon=True).start()))

    # ---------- проекты, идеи, боты ----------
    def project_tick(s):
        h = u32.GetForegroundWindow()
        n = u32.GetWindowTextLengthW(h)
        buf = ctypes.create_unicode_buffer(n + 1)
        u32.GetWindowTextW(h, buf, n + 1)
        title = buf.value.lower()
        for p in s.projects:
            if p["name"].lower() in title:
                p["last"] = dt.date.today().isoformat()
                p["where"] = buf.value[:80]

    def projects_say(s):
        if not s.projects:
            return s.say("Проектов пока нет. Скажи «добавь проект Название».", 4, speak=True)
        s.say("Твои проекты: " + "; ".join(f"{p['name']}" + (f" (последний раз {p['last']})" if p.get("last") else "")
                                         for p in s.projects), 8, speak=True)

    def yesterday_project(s):
        y = (dt.date.today() - dt.timedelta(days=1)).isoformat()
        ps_ = [p["name"] for p in s.projects if p.get("last") == y]
        return f"Вчера ты работал над {', '.join(ps_)} — продолжим?" if ps_ else None

    def game_idea(s):
        def go():
            try:
                out = s.ai.ask("Ты геймдизайнер. По-русски, 2–3 предложения.",
                               "Предложи одну свежую идею для игры в Roblox (механика + чем зацепит игроков).",
                               task="chat", private=False, tokens=200)
                ideas = read_json(IDEAS, [])
                write_json(IDEAS, (ideas + [{"d": dt.date.today().isoformat(), "t": out}])[-100:])
                s.answers.put(("info_say", "Идея: " + out + " (записал в «мои идеи»)"))
            except (OSError, ValueError, KeyError, RuntimeError) as e:
                s.answers.put(("info_say", f"Мозги не ответили: {str(e)[:60]}"))
        threading.Thread(target=go, daemon=True).start()

    def check_bots(s):
        from .pet_onboard import read_env
        urls = [u.strip() for u in read_env().get("BOTS_URLS", "").split(",") if u.strip()]
        if not urls:
            return s.say("Адреса ботов не заданы. Впиши их в %APPDATA%\\Klodik\\.env строкой BOTS_URLS=адрес1,адрес2", 7)

        def go():
            bad = []
            for u in urls:
                try:
                    urllib.request.urlopen(u, timeout=10)
                except OSError as e:
                    bad.append(f"{u} ({str(e)[:40]})")
            s.answers.put(("bots", "Все боты живы." if not bad else "Не отвечают: " + "; ".join(bad)
                           + ". Проверь сервер: процесс, логи, место на диске. Сам ничего не перезапускаю."))
        threading.Thread(target=go, daemon=True).start()

    # ---------- свет и охрана ----------
    def power_tick(s):
        ac, pct, mins = power_status()
        if pct is None:                                    # батареи/ИБП не видно — режим не нужен
            return
        if s.on_battery is None:
            s.on_battery = not ac
            return
        if not ac and not s.on_battery:
            s.on_battery = True
            s.saved_anim = s.prefs.get("anim", "max")
            s.prefs["anim"] = "min"
            s.emote("fear", "medium")
            left = f", осталось {pct}%" + (f" (~{mins} мин)" if mins else "") if pct is not None else ""
            s.say(f"Похоже, свет отключили — работаем от батареи{left}. Сохрани работу и закрой тяжёлое; "
                  "я перешёл в экономный режим.", 10, speak=True)
            s.log("power_outage", "питание от батареи", "экономный режим")
        elif ac and s.on_battery:
            s.on_battery = False
            s.prefs["anim"] = getattr(s, "saved_anim", "max")
            s.emote("joy", "medium")
            s.say("Свет вернулся! Вернул всё как было.", 5, speak=True)

    def guard_tick(s):
        now = set(T.autostart())
        seen = read_json(GUARD, None)
        write_json(GUARD, sorted(now | set(seen or [])))
        new = now - set(seen or now)
        if new:
            s.emote("fear", "light")
            s.say("В автозапуске появилось новое: " + ", ".join(sorted(new)) + ". Если это не ты — скажи «покажи автозапуск».",
                  10, speak=True)
            s.log("guard", "автозапуск: " + ", ".join(sorted(new)), "сообщил")

    def good_night(s):
        """«На добраніч»: короткий итог дня и спокойное прощание."""
        parts = [f"На добраніч{', ' + s.addr() if s.addr() else ''}!"]
        rep = s.track_report(day=dt.date.today().isoformat())
        if rep != "Пока ничего не насчитал.":
            parts.append(f"Сегодня больше всего: {rep}.")
        if s.notes:
            parts.append(f"На завтра в списке: {', '.join(s.notes[:3])}.")
        s.emote("tired", "medium")
        s.say(" ".join(parts), 10, speak=True)
        s.root.after(4000, s.sleep)

    def desk_tick(s, secs):
        """Раз в 10 с."""
        s.pomo_tick()
        s.track_tick(secs)
        s.project_tick()
        s.power_tick()
        if s.every("guard", 3600):
            s.guard_tick()

    def desk_command(s, seg):
        if re.search(r"помодоро", seg):
            return lambda: s.pomodoro(stop=bool(re.search(r"стоп|выключи|останови|хватит", seg)))
        if re.search(r"истори\w+ буфер|что я копировал", seg):
            return s.clips_window
        if m := re.match(r"(?:стикер|повесь стикер|наклей)\s*:?\s*(.+)", seg):
            return lambda t=m[1]: s.sticker(t[:200])
        if re.search(r"(?:сколько|где) я (?:сидел|провёл|провел)|тайм.?трекер|что я делал (?:вчера|сегодня|за неделю)", seg):
            day = ((dt.date.today() - dt.timedelta(days=1)).isoformat() if "вчера" in seg
                   else dt.date.today().isoformat() if "сегодня" in seg else None)
            if re.search(r"сотри|очисти", seg):
                return s.track_clear
            return lambda: s.say(s.track_report(day=day), 8, speak=True)
        if re.search(r"погод", seg):
            return lambda: s.weather_rates("weather")
        if re.search(r"курс (?:валют|доллар|евро|гривн)|какой курс|почём доллар|почем доллар", seg):
            return lambda: s.weather_rates("rates")
        if re.search(r"что (?:это )?за ошибк|объясни ошибк|разбери ошибк", seg):
            return s.explain_error
        if re.search(r"разложи окна|окна по сетке|раскидай окна", seg):
            return s.arrange
        if re.search(r"(?:увеличь|разверни)\s+окно", seg):
            return lambda: s.window_op("max")
        if re.search(r"(?:открепи|сними)\s+(?:окно|поверх)", seg):
            return lambda: s.window_op("unpin")
        if re.search(r"закрепи\s+(?:окно|поверх)|поверх всех", seg):
            return lambda: s.window_op("pin")
        if re.search(r"(?:верни|найди)\s+(?:пропавш|потерянн)\w*\s+окн", seg):
            return lambda: s.window_op("rescue")
        if re.search(r"(?:выключи|погаси)\s+(?:монитор|экран)", seg):
            return s.monitor_off
        if re.search(r"(?:кто|что)\s+(?:открыл|слушает)\s+порт|открытые порты", seg):
            return s.show_ports
        if re.search(r"(?:что|какая программа)\s+завис|зависш", seg):
            return s.hung
        if re.search(r"пинг|скорость (?:интернета|связи)", seg):
            return s.ping
        if re.search(r"разбер\w*\s+загрузк|разложи загрузк|наведи порядок в загрузк", seg):
            return s.sort_downloads
        if re.search(r"сожми видео|видео для телеграм", seg):
            return lambda: s.ffmpeg("tg")
        if re.search(r"(?:в|сделай)\s+mp4|конверт\w*\s+видео", seg):
            return lambda: s.ffmpeg("mp4")
        if re.search(r"уменьши фото|сожми фото|уменьши картинк", seg):
            return lambda: s.ffmpeg("img")
        if m := re.match(r"(?:добавь|запомни)\s+проект\s+(.+)", seg):
            return lambda n=m[1].strip(): (s.projects.append({"name": n}), write_json(PROJECTS, s.projects),
                                           s.say(f"Запомнил проект «{n}».", 3, speak=True))
        if m := re.match(r"(?:удали|убери)\s+проект\s+(.+)", seg):
            def rm(n=m[1].strip().lower()):
                s.projects = [p for p in s.projects if p["name"].lower() != n]
                write_json(PROJECTS, s.projects)
                s.say("Убрал проект.", 3)
            return rm
        if re.search(r"мои проекты|какие (?:у меня )?проекты|где (?:я )?остановил", seg):
            return s.projects_say
        if re.search(r"иде\w+ для игр|придумай игру", seg):
            return s.game_idea
        if re.search(r"мои идеи", seg):
            return lambda: s.say("Идеи: " + " | ".join(i["t"][:80] for i in read_json(IDEAS, [])[-3:]) or "пока нет", 10)
        if re.search(r"(?:проверь|как там|живы ли)\s+бот", seg):
            return s.check_bots
        if re.search(r"на добраніч|спокойной ночи|добрых снов", seg):
            return s.good_night
        if re.search(r"(?:покажи|какой)\s+заряд|сколько (?:осталось )?(?:заряда|батаре)", seg):
            def bat():
                ac, pct, mins = power_status()
                s.say("Батареи или ИБП не вижу (по USB он должен отдавать данные Windows)." if pct is None else
                      f"Заряд {pct}%{', от сети' if ac else ''}" + (f", ~{mins} мин" if mins and not ac else "") + ".", 5,
                      speak=True)
            return bat
        return None


def idle_away():
    from .pet_soul import idle_seconds
    return idle_seconds() > 300


def fmt_secs(t):
    t = int(t)
    return f"{t // 3600} ч {t % 3600 // 60} мин" if t >= 3600 else f"{t // 60} мин"
