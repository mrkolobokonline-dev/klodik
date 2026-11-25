"""Этап 7 (блоки G, H): Telegram только для владельца (ID из .env, чужих молча игнорируем; опасное — через ту же
политику с «да»; скрин — только по команде, пишется в журнал), воздушные тревоги Киева (alerts.in.ua, токен в .env;
спокойно, без шуток; нет связи — молчим), профили работа/игра/ночь и режим кино, каталог команд с поиском,
«что нового» после обновления, перенос настроек (без секретов). Друзья и режим гостя — позже, по просьбе владельца."""
import uuid
import zipfile

from .common import *  # noqa: F401,F403
from .pet_onboard import read_env
from .update import VERSION
from .policy import PKG_DATA

TG = "https://api.telegram.org/bot{t}/{m}"
ALERTS = "https://api.alerts.in.ua/v1/alerts/active.json"
PROFILES = {"работа": {"working": True, "anim": "moderate", "game_mode": "hide"},
            "игра": {"working": False, "anim": "max", "game_mode": "corner"},
            "ночь": {"working": True, "anim": "min", "game_mode": "hide"},
            "кино": {"working": True, "anim": "min", "game_mode": "hide"}}
PROFILE_WORDS = {"работ": "работа", "игр": "игра", "ноч": "ночь", "кино": "кино", "фильм": "кино"}


def tg_call(token, method, data=None, files=None, timeout=35):
    url = TG.format(t=token, m=method)
    if files:                                           # multipart для фото
        b = uuid.uuid4().hex
        body = b""
        for k, v in (data or {}).items():
            body += f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
        for k, path in files.items():
            body += (f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"; filename=\"{os.path.basename(path)}\"\r\n"
                     "Content-Type: image/png\r\n\r\n").encode() + open(path, "rb").read() + b"\r\n"
        body += f"--{b}--\r\n".encode()
        req = urllib.request.Request(url, data=body, headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    else:
        req = urllib.request.Request(url, data=json.dumps(data or {}).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def owner_msg(update, owner):
    """Текст сообщения, если оно от владельца (и чат, и отправитель); иначе None — чужих молча пропускаем."""
    m = update.get("message") or {}
    if str(m.get("chat", {}).get("id")) == str(owner) and str(m.get("from", {}).get("id")) == str(owner):
        return (m.get("text") or "").strip() or None
    return None


def kyiv_alert(alerts, region):
    return any(a.get("alert_type") == "air_raid" and region.lower() in (a.get("location_title") or "").lower()
               for a in alerts)


class PetLink:
    def link_load(s):
        s.tg_out, s.tg_until, s.alert_on = queue.Queue(), 0.0, None
        e = read_env()
        if e.get("TELEGRAM_BOT_TOKEN") and e.get("TELEGRAM_OWNER_CHAT_ID") and s.claude == s.think:
            threading.Thread(target=s.tg_loop, args=(e["TELEGRAM_BOT_TOKEN"], e["TELEGRAM_OWNER_CHAT_ID"]),
                             daemon=True).start()
        if e.get("ALERTS_TOKEN") and s.claude == s.think:
            threading.Thread(target=s.alerts_loop, args=(e["ALERTS_TOKEN"], e.get("ALERTS_REGION") or "м. Київ"),
                             daemon=True).start()
        if s.prefs.get("seen_version") != VERSION:
            s.root.after(6000, s.whats_new)

    # ---------- Telegram ----------
    def say(s, text, secs=None, image=None, speak=None):
        super().say(text, secs, image, speak)
        if text and s.clock < getattr(s, "tg_until", 0) and not text.startswith(("Думаю", "Слушаю")):
            s.tg_out.put(("text", text))                  # ответ на команду с телефона — туда же

    def tg_loop(s, token, owner):
        off = 0
        while True:
            try:
                while not s.tg_out.empty():
                    kind, v = s.tg_out.get_nowait()
                    if kind == "photo":
                        tg_call(token, "sendPhoto", {"chat_id": owner}, {"photo": v})
                    else:
                        tg_call(token, "sendMessage", {"chat_id": owner, "text": v[:4000]})
                if not s.on("telegram"):
                    time.sleep(5)
                    continue
                d = tg_call(token, "getUpdates", {"offset": off, "timeout": 20}, timeout=30)
                for u in d.get("result", []):
                    off = u["update_id"] + 1
                    text = owner_msg(u, owner)
                    if text:
                        s.answers.put(("tg", text))
            except (OSError, ValueError, KeyError):
                time.sleep(15)                            # нет сети — тихо ждём

    def tg_command(s, text):
        """Команда с телефона (главный поток)."""
        s.tg_until = s.clock + 20
        low = text.lower().lstrip("/")
        if re.search(r"^(?:скрин|screenshot|сфоткай экран)", low):
            s.log("screenshot", "скрин экрана по команде из Telegram", "отправлен владельцу")
            s.flash()                                      # на ПК видно, что снимали
            try:
                s.tg_out.put(("photo", s.fx.screenshot()))
            except (OSError, RuntimeError) as e:
                s.tg_out.put(("text", f"Скрин не вышел: {e}"))
            return
        if re.search(r"^(?:что (?:сейчас )?на пк|статус|status)", low):
            s.stats.poll()
            return s.tg_out.put(("text", f"{s.context()}"))
        if low in ("start", "help", "помощь"):
            return s.tg_out.put(("text", "Пиши мне как на ПК: «открой Steam», «напомни в 9 …», «запиши …», «скрин», "
                                         "«что на ПК». Опасное спрошу «да?» — ответь «да»."))
        s.send(text)
        s.request = (text, "Telegram")

    # ---------- тревоги ----------
    def alerts_loop(s, token, region):
        while True:
            try:
                if s.on("alerts"):
                    req = urllib.request.Request(ALERTS, headers={"Authorization": f"Bearer {token}"})
                    d = json.load(urllib.request.urlopen(req, timeout=15))
                    s.answers.put(("alert", "1" if kyiv_alert(d.get("alerts", []), region) else "0"))
            except (OSError, ValueError, KeyError):
                pass                                       # нет связи — молчим
            time.sleep(30)

    def on_alert(s, on):
        if s.alert_on is None:
            s.alert_on = on
            return
        if on == s.alert_on:
            return
        s.alert_on = on
        s.emote("fear" if on else "tenderness", "light")
        s.say("Воздушная тревога в Киеве. Пройди в укрытие." if on else "Отбой тревоги в Киеве.", 12, speak=True)
        if on:
            s.tg_out.put(("text", "Воздушная тревога в Киеве."))

    # ---------- режимы и профили ----------
    def set_profile(s, name):
        old = {k: s.prefs.get(k) for k in PROFILES[name]}
        for k, v in PROFILES[name].items():
            s.prefs[k] = v
        s.save()
        s.key = None
        s.push_undo(f"профиль {name}", lambda: (s.prefs.update(old), s.save()))
        s.log("profile", name, "включён")
        s.say({"работа": "Профиль «работа»: молчу, только важные напоминания.", "игра": "Профиль «игра»: в играх сижу в углу.",
               "ночь": "Профиль «ночь»: тихо и минимум анимаций.", "кино": "Режим кино: молчу и почти не двигаюсь. "
               "«Кино всё» — верну как было."}[name], 4, speak=name != "кино")

    # ---------- каталог команд и «что нового» ----------
    def catalog(s):
        lines = open(os.path.join(PKG_DATA, "commands.txt"), encoding="utf-8").read().splitlines()
        w = tk.Toplevel(s.root)
        w.title("Что умеет Клодик")
        w.attributes("-topmost", True)
        q = tk.Entry(w, font=("Segoe UI", 11))
        q.pack(fill="x", padx=8, pady=6)
        box = tk.Listbox(w, width=110, height=18, font=("Segoe UI", 9))
        box.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        def fill(_=None):
            box.delete(0, "end")
            for line in lines:
                if q.get().lower() in line.lower():
                    box.insert("end", line)

        def run(_=None):
            if box.curselection():
                m = re.search(r"«([^»]+)»", box.get(box.curselection()[0]))
                if m and "…" not in m[1]:
                    w.destroy()
                    s.send(m[1])
        q.bind("<KeyRelease>", fill)
        box.bind("<Double-Button-1>", run)
        fill()
        q.focus_set()
        return w

    def whats_new(s):
        s.prefs["seen_version"] = VERSION
        s.save()
        w = tk.Toplevel(s.root)
        w.title(f"Что нового — Клодик {VERSION}")
        w.attributes("-topmost", True)
        w.configure(bg=PAPER, padx=14, pady=10)
        tk.Label(w, text=open(os.path.join(PKG_DATA, "whatsnew.md"), encoding="utf-8").read(), bg=PAPER, fg=INK,
                 justify="left", wraplength=560, font=("Segoe UI", 10)).pack()
        tk.Button(w, text="Понятно", command=w.destroy, relief="flat").pack(pady=(8, 0))
        return w

    # ---------- перенос настроек ----------
    def import_settings(s):
        docs = special_dir(0x05) or HERE
        zips = sorted(f for f in os.listdir(docs) if f.startswith("Klodik-данные-") and f.endswith(".zip"))
        if not zips:
            return s.say("Не нашёл в «Документах» файл Klodik-данные-….zip (сделай его на старом ПК: «экспорт данных»).",
                         6, speak=True)
        src = os.path.join(docs, zips[-1])

        def do():
            with zipfile.ZipFile(src) as z:
                names = [n for n in z.namelist() if "/" not in n and "\\" not in n and not n.endswith(".env")]
                for n in names:
                    z.extract(n, DATA_DIR)
            s.say(f"Перенёс {len(names)} файлов настроек. Перезапусти меня, чтобы всё подхватилось.", 6, speak=True)
        s.gate("import_settings", f"заменить мои данные данными из «{zips[-1]}»", do)

    def link_command(s, seg):
        if re.search(r"режим кино|смотрю (?:фильм|кино)", seg):
            return lambda: s.set_profile("кино")
        if re.search(r"кино всё|кино все|фильм закончил", seg):
            return s.undo
        if m := re.search(r"профиль\s+(\w+)", seg):
            name = next((v for k, v in PROFILE_WORDS.items() if m[1].startswith(k)), None)
            return (lambda: s.set_profile(name)) if name else None
        if re.search(r"что (?:ты )?умеешь|список команд|каталог команд|какие (?:есть )?команды", seg):
            return s.catalog
        if re.search(r"что нового", seg):
            return s.whats_new
        if re.search(r"(?:экспорт|перенеси|сохрани)\s+(?:данн|настро)", seg):
            return s.export_data
        if re.search(r"импорт\w*\s+(?:данн|настро)", seg):
            return s.import_settings
        return None
