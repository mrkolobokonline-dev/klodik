"""Первый запуск (5а): Клодик сам знакомится — имя и как склонять, стартовая память, подключения по одному шагу
кнопками «Да / Нет / Позже». Шаги — из data/onboarding_steps.json: новая функция = одна запись там + обработчик тут.
Плюс окно «Импорт памяти» и запись секретов в локальный .env (только на этом ПК, не в git, не в exe)."""
from .common import *  # noqa: F401,F403
from .apps import *  # noqa: F401,F403
from .winapi import *  # noqa: F401,F403
from .monitor import *  # noqa: F401,F403
from .brain import *  # noqa: F401,F403
from .voice import *  # noqa: F401,F403
from .sprites import *  # noqa: F401,F403
from .decline import decline, guess_lang
from .policy import LEVELS, PKG_DATA, recycle
from .pet_tasks import read_json, write_json

ONBOARD = os.path.join(DATA_DIR, "onboarding.json")
ENV = os.path.join(DATA_DIR, ".env")
SEED = os.path.join(DATA_DIR, "memory_seed.md")
NEVER = re.compile(r"парол|password|\bpin\b|cvv|токен|token|api[_ ]?key|sk-[\w-]{10,}|AIza[\w-]{10,}|"
                   r"\b(?:\d[ -]?){13,19}\b|паспорт|ИНН|РНОКПП", re.I)          # такое не сохраняем никогда
TOUCHY = re.compile(r"здоров|болезн|диагноз|лекарств|деньг|зарплат|долг|кредит|бюджет|адрес|служб|военн", re.I)
SOON = {"calendar_mail": "календарь и почта", "music": "Spotify", "ups_power": "ИБП и график света",
        "alerts": "тревоги и новости", "telegram": "Telegram"}


def read_env():
    env = {}
    try:
        for line in open(ENV, encoding="utf-8"):
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    except OSError:
        pass
    return env


def write_env(**kv):
    """Секреты — в %APPDATA%\\Klodik\\.env (локально). Пустое значение не затирает старое."""
    env = read_env()
    env.update({k: v for k, v in kv.items() if v})
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(ENV, "w", encoding="utf-8") as f:
        f.write("# Секреты Клодика. Только на этом ПК, никуда не отправляется и не коммитится.\n")
        f.writelines(f"{k}={v}\n" for k, v in env.items())


def parse_facts(text):
    """Текст → отдельные факты. Пароли/карты/ключи выкидываем, чувствительное помечаем ⚠."""
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(("#", "Формат", "Пометки", "Источник")):
            continue
        line = re.sub(r"^[-*•\d.)\s]+", "", line).strip()
        for part in re.split(r"(?<=[.!?])\s+(?=[А-ЯЁІЇЄA-Z])", line) if len(line) > 220 else [line]:
            part = part.strip(" .")
            if len(part) < 4 or NEVER.search(part):
                continue
            private = "[личное]" in part
            part = part.replace("[личное]", "").strip(" .")
            out.append({"fact": part, "private": private, "touchy": bool(TOUCHY.search(part))})
    return out


def hardware():
    """ОЗУ, видеокарта и её память — чтобы подобрать модели Ollama."""
    m = MEMSTAT()
    m.len = ctypes.sizeof(MEMSTAT)
    k32.GlobalMemoryStatusEx(ctypes.byref(m))
    ram = m.total / 2**30
    out = run_quiet(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"], timeout=10).stdout
    try:
        gname, vram = [x.strip() for x in out.strip().splitlines()[0].split(",")]
        vram = float(vram) / 1024
    except (ValueError, IndexError):
        gname, vram = "", 0.0
    if vram >= 7.5:
        rec = {"OLLAMA_MODEL_FAST": "qwen2.5:3b", "OLLAMA_MODEL_SMART": "qwen2.5:7b", "OLLAMA_MODEL_VISION": "qwen2.5vl:7b"}
    elif vram >= 4 or ram >= 15:
        rec = {"OLLAMA_MODEL_FAST": "qwen2.5:3b", "OLLAMA_MODEL_SMART": "qwen2.5:7b", "OLLAMA_MODEL_VISION": "qwen2.5vl:3b"}
    else:
        rec = {"OLLAMA_MODEL_FAST": "qwen2.5:1.5b", "OLLAMA_MODEL_SMART": "qwen2.5:3b", "OLLAMA_MODEL_VISION": "moondream"}
    return {"ram": ram, "gpu": gname, "vram": vram, "rec": rec}


class PetOnboard:
    def onboard_load(s):
        s.ob = read_json(ONBOARD, {"done": {}})
        s.ob_steps = json.load(open(os.path.join(PKG_DATA, "onboarding_steps.json"), encoding="utf-8"))["steps"]
        s.ob_win = None
        if "name" not in s.ob["done"]:
            s.root.after(4000, s.onboarding)                  # первый запуск — знакомимся
        elif s.ob_new():
            s.root.after(8000, lambda: s.say("Есть новые функции, которые можно подключить. Скажи «что ещё можно "
                                             "подключить».", 8, speak=True))

    def ob_new(s):
        return [st["id"] for st in s.ob_steps if st["id"] not in s.ob["done"]]

    def ob_mark(s, sid, answer):
        s.ob["done"][sid] = answer
        write_json(ONBOARD, s.ob)

    # --- обращение ---
    def addr(s):
        """Как обратиться к владельцу сейчас: прозвище или звательная форма имени."""
        p = s.profile or {}
        return p.get("nick") or p.get("forms", {}).get("vocative") or p.get("name") or ""

    def set_name(s, name, lang=None, nick="", gender=None):
        lang = lang or guess_lang(name)
        g = guess_lang(name)                                  # «Олексій» — склоняем по-украински, даже если болтаем по-русски
        forms = decline(name, g if g in ("uk", "en") else lang)
        s.profile = {**(s.profile or {}), "name": name.strip(), "lang": lang, "nick": nick.strip(),
                     "gender": gender or (s.profile or {}).get("gender", "m"),
                     "forms": {k: forms[k] for k in ("vocative", "genitive", "dative")}, "forms_sure": forms["sure"]}
        s.save()
        return forms

    # --- мастер ---
    def onboarding(s, start=None):
        """Окно знакомства. start — с какого шага (по умолчанию — первый неотвеченный или «Позже»)."""
        if s.ob_win and s.ob_win.winfo_exists():
            return s.ob_win.lift()
        todo = [st for st in s.ob_steps if s.ob["done"].get(st["id"]) in (None, "later")]
        if start:
            todo = [st for st in s.ob_steps if st["id"] == start] + [t for t in todo if t["id"] != start]
        if not todo:
            return s.say("Всё уже подключено или отвечено. Поменять можно в настройках.", 4, speak=True)
        w = s.ob_win = tk.Toplevel(s.root)
        w.title("Знакомство с Клодиком")
        w.attributes("-topmost", True)
        w.configure(bg=PAPER, padx=22, pady=16)
        w.resizable(False, False)
        s.ob_icon = klodik_photo_small()
        tk.Label(w, image=s.ob_icon, bg=PAPER).pack()
        s.ob_q = tk.Label(w, text="", bg=PAPER, fg=INK, font=("Segoe UI", 13, "bold"), wraplength=440, justify="center")
        s.ob_q.pack(pady=(6, 2))
        s.ob_why = tk.Label(w, text="", bg=PAPER, fg=DARK, font=("Segoe UI", 9), wraplength=440, justify="center")
        s.ob_why.pack()
        s.ob_body = tk.Frame(w, bg=PAPER)
        s.ob_body.pack(pady=8, fill="x")
        s.ob_btns = tk.Frame(w, bg=PAPER)
        s.ob_btns.pack(pady=(4, 0))
        s.ob_prog = tk.Label(w, text="", bg=PAPER, fg=DARK, font=("Segoe UI", 8))
        s.ob_prog.pack(pady=(8, 0))
        s.ob_todo, s.ob_i = todo, -1
        s.ob_next()

    def ob_clear(s):
        for f in (s.ob_body, s.ob_btns):
            for c in f.winfo_children():
                c.destroy()

    def ob_button(s, text, cmd, main=False):
        tk.Button(s.ob_btns, text=text, command=cmd, relief="flat", padx=14, pady=4,
                  bg=ORANGE if main else "#eadfd8", fg="white" if main else INK,
                  font=("Segoe UI", 10, "bold" if main else "normal")).pack(side="left", padx=4)

    def ob_yes_no(s, sid, on_yes, yes_text="Да"):
        s.ob_button(yes_text, lambda: (on_yes(), s.ob_mark(sid, "yes"), s.ob_next()), main=True)
        s.ob_button("Нет", lambda: (s.ob_mark(sid, "no"), s.ob_next()))
        s.ob_button("Позже", lambda: (s.ob_mark(sid, "later"), s.ob_next()))

    def ob_entry(s, label, value="", secret=False, width=34):
        tk.Label(s.ob_body, text=label, bg=PAPER, fg=INK, font=("Segoe UI", 9)).pack(anchor="w")
        e = tk.Entry(s.ob_body, width=width, font=("Segoe UI", 11), show="•" if secret else "")
        e.insert(0, value)
        e.pack(anchor="w", pady=(0, 6))
        return e

    def ob_radio(s, options, default):
        var = tk.StringVar(value=default)
        for k, v in options:
            tk.Radiobutton(s.ob_body, text=v, value=k, variable=var, bg=PAPER, font=("Segoe UI", 10)).pack(anchor="w")
        return var

    def ob_next(s):
        s.ob_i += 1
        if s.ob_i >= len(s.ob_todo):
            return s.ob_finish()
        st = s.ob_todo[s.ob_i]
        s.ob_clear()
        s.ob_prog.config(text=f"шаг {s.ob_i + 1} из {len(s.ob_todo)} · любой шаг можно пропустить и вернуться: "
                              "«что ещё можно подключить»")
        s.ob_q.config(text=st["ask"])
        s.ob_why.config(text=st.get("why", ""))
        getattr(s, "ob_" + st["id"], s.ob_generic)(st)
        if s.tts_on:
            s.speaker.say(st["ask"])

    def ob_generic(s, st):
        s.ob_yes_no(st["id"], lambda: None)

    def ob_name(s, st):
        name = s.ob_entry("Имя:", (s.profile or {}).get("name", ""))
        nick = s.ob_entry("Прозвище (необязательно):", (s.profile or {}).get("nick", ""))
        tk.Label(s.ob_body, text="Как о тебе говорить:", bg=PAPER, fg=INK, font=("Segoe UI", 9)).pack(anchor="w")
        g = s.ob_radio([("m", "он (рад, пришёл)"), ("f", "она (рада, пришла)")], (s.profile or {}).get("gender", "m"))
        tk.Label(s.ob_body, text="Язык общения:", bg=PAPER, fg=INK, font=("Segoe UI", 9)).pack(anchor="w", pady=(6, 0))
        lang = s.ob_radio([("ru", "Русский"), ("uk", "Українська"), ("en", "English")], (s.profile or {}).get("lang", "ru"))
        name.focus_set()

        def go():
            if not name.get().strip():
                return s.ob_why.config(text="Напиши имя — по нему я и буду к тебе обращаться.")
            forms = s.set_name(name.get(), lang.get(), nick.get(), g.get())
            if not forms["sure"]:
                return s.ob_confirm_forms()
            s.ob_mark("name", "yes")
            s.say(f"Приятно познакомиться, {s.addr()}!", 4, speak=True)
            s.ob_next()
        s.ob_button("Дальше", go, main=True)

    def ob_confirm_forms(s):
        """Склонение не уверено — один раз уточнить и запомнить."""
        s.ob_clear()
        f = s.profile["forms"]
        s.ob_q.config(text=f"Как правильно к тебе обращаться: «{f['vocative']}»?")
        s.ob_why.config(text="Поправь, если неверно. Запомню навсегда.")
        voc = s.ob_entry("Обращение (звательный падеж):", f["vocative"])
        gen = s.ob_entry("Нет кого? (родительный):", f["genitive"])
        dat = s.ob_entry("Дать кому? (дательный):", f["dative"])

        def go():
            s.profile["forms"] = {"vocative": voc.get().strip(), "genitive": gen.get().strip(), "dative": dat.get().strip()}
            s.profile["forms_sure"] = True
            s.save()
            s.ob_mark("name", "yes")
            s.say(f"Приятно познакомиться, {s.addr()}!", 4, speak=True)
            s.ob_next()
        s.ob_button("Да, верно", go, main=True)

    def ob_seed_memory(s, st):
        if not os.path.exists(SEED):
            s.ob_mark("seed_memory", "no")
            return s.ob_next()
        facts = parse_facts(open(SEED, encoding="utf-8").read())
        s.ob_why.config(text=f"У меня есть {len(facts)} фактов о тебе (из стартовой памяти). Всё хранится только на "
                             "этом ПК; помеченное «личное» не уходит даже в облачный ИИ.")

        def keep():
            n = s.import_facts([f for f in facts if not f["touchy"]])
            touchy = [f for f in facts if f["touchy"]]
            s.say(f"Запомнил {n} фактов." + (f" {len(touchy)} деликатных — проверь в «Импорт памяти»." if touchy else ""),
                  5, speak=True)
            if touchy:
                s.root.after(600, lambda: s.memory_import_window(touchy))
        s.ob_button("Оставить", lambda: (keep(), s.ob_mark("seed_memory", "yes"), s.ob_next()), main=True)
        s.ob_button("Показать", lambda: s.memory_import_window(facts))
        s.ob_button("Удалить", lambda: (recycle(SEED), s.ob_mark("seed_memory", "no"),
                                         s.say("Стартовую память удалил (в корзину).", 3), s.ob_next()))
        s.ob_button("Позже", lambda: (s.ob_mark("seed_memory", "later"), s.ob_next()))

    def ob_gemini_key(s, st):
        tk.Label(s.ob_body, text="Ключ бесплатный: aistudio.google.com/apikey → «Create API key».\n"
                                 "В облако уходит только текст запроса — без скриншотов, буфера, файлов и памяти.",
                 bg=PAPER, fg=DARK, font=("Segoe UI", 9), justify="left").pack(anchor="w", pady=(0, 6))
        key = s.ob_entry("Ключ Gemini:", "", secret=True, width=44)
        s.ob_yes_no("gemini_key", lambda: write_env(GEMINI_API_KEY=key.get().strip()), "Сохранить")

    def ob_ollama(s, st):
        hw = hardware()
        rec = hw["rec"]
        have = ollama_models()
        lines = [f"Память: {hw['ram']:.0f} ГБ" + (f", видеокарта: {hw['gpu']} ({hw['vram']:.0f} ГБ)" if hw["gpu"] else ""),
                 f"Быстрая модель: {rec['OLLAMA_MODEL_FAST']}", f"Умная: {rec['OLLAMA_MODEL_SMART']}",
                 f"Зрение (смотреть на экран): {rec['OLLAMA_MODEL_VISION']}",
                 "Ollama: " + ("работает" if have is not None else "не найдена — поставлю")]
        tk.Label(s.ob_body, text="\n".join(lines), bg=PAPER, fg=INK, font=("Segoe UI", 10), justify="left").pack(anchor="w")

        def yes():
            write_env(**rec)
            if have is None and not ollama_exe():
                from .install import setup_ollama
                setup_ollama()
            threading.Thread(target=s.pull_models, args=(list(rec.values()),), daemon=True).start()
        s.ob_yes_no("ollama", yes, "Скачать и включить")

    def pull_models(s, names):
        for _ in range(60):                                   # ждём, пока Ollama встанет (если ставится)
            if ollama_models() is not None:
                break
            time.sleep(10)
        have = ollama_models() or []
        for n in names:
            if not any(h.startswith(n) for h in have):
                try:
                    s.answers.put(("info", f"Качаю модель {n}…"))
                    ollama_call("/api/pull", {"model": n, "stream": False}, 7200)
                except (OSError, ValueError) as e:
                    s.answers.put(("info", f"Модель {n} не скачалась: {e}"))
        s.answers.put(("info", "Модели на месте!"))

    def ob_voice_mic(s, st):
        s.ob_yes_no("voice_mic", lambda: (s.set_listen(True), s.set_tts(True)))

    def ob_telegram(s, st):
        tk.Label(s.ob_body, text="Токен даёт @BotFather (/newbot). Свой chat id покажет @userinfobot.\n"
                                 "Хранится только на этом ПК. Слушаюсь только тебя (по chat id), заработает после перезапуска.",
                 bg=PAPER, fg=DARK, font=("Segoe UI", 9), justify="left").pack(anchor="w", pady=(0, 6))
        tok = s.ob_entry("Токен бота:", "", secret=True, width=44)
        cid = s.ob_entry("Твой chat id:", read_env().get("TELEGRAM_OWNER_CHAT_ID", ""))
        s.ob_yes_no("telegram", lambda: write_env(TELEGRAM_BOT_TOKEN=tok.get().strip(),
                                                  TELEGRAM_OWNER_CHAT_ID=cid.get().strip()), "Сохранить")

    def ob_soon(s, st):
        s.ob_why.config(text=f"{SOON[st['id']].capitalize()} я ещё учусь подключать. Скажешь «да» — предложу сам, "
                             "как только научусь.")
        s.ob_button("Да, хочу", lambda: (s.ob_mark(st["id"], "wanted"), s.ob_next()), main=True)
        s.ob_button("Нет", lambda: (s.ob_mark(st["id"], "no"), s.ob_next()))
        s.ob_button("Позже", lambda: (s.ob_mark(st["id"], "later"), s.ob_next()))

    ob_calendar_mail = ob_music = ob_ups_power = ob_alerts = ob_soon

    def ob_access_level(s, st):
        var = s.ob_radio(list(LEVELS.items()), s.access_level)
        s.ob_why.config(text="Помощник: простое делаю сам, остальное — после твоего «да». Опасное запрещено всегда.")
        s.ob_yes_no("access_level", lambda: s.set_level(var.get()), "Выбрать")

    def ob_quiet_hours(s, st):
        q = s.prefs.get("quiet", ["23:00", "08:00"])
        a = s.ob_entry("С (ЧЧ:ММ):", q[0], width=8)
        b = s.ob_entry("До (ЧЧ:ММ):", q[1], width=8)
        s.ob_why.config(text="В тихие часы я не говорю вслух, не подсказываю и не болтаю сам. Напоминания — только важные.")

        def yes():
            ok = all(re.fullmatch(r"\d{1,2}:\d{2}", x.get().strip()) for x in (a, b))
            s.prefs["quiet"] = [a.get().strip(), b.get().strip()] if ok else ["23:00", "08:00"]
            s.save()
        s.ob_yes_no("quiet_hours", yes, "Включить")

    def ob_animations(s, st):
        var = s.ob_radio([("max", "Максимум"), ("moderate", "Умеренно"), ("min", "Минимум")], s.prefs.get("anim", "max"))
        s.ob_yes_no("animations", lambda: (s.prefs.__setitem__("anim", var.get()), s.save()), "Выбрать")

    def ob_emotions(s, st):
        var = s.ob_radio([("calm", "Спокойный"), ("lively", "Живой (рекомендуется)"), ("very", "Очень эмоциональный")],
                         s.prefs.get("emo", "lively"))
        s.ob_yes_no("emotions", lambda: (s.prefs.__setitem__("emo", var.get()), s.save()), "Выбрать")

    def ob_finish(s):
        s.ob_clear()
        d = s.ob["done"]
        on = [st["ask"].rstrip("?") for st in s.ob_steps if d.get(st["id"]) == "yes"]
        later = [st["ask"].rstrip("?") for st in s.ob_steps if d.get(st["id"]) == "later"]
        s.ob_q.config(text=f"Готово, {s.addr()}!")
        s.ob_why.config(text=("Включено: " + "; ".join(on[:8]) + ".\n" if on else "") +
                        ("Отложено: " + "; ".join(later[:6]) + ".\n" if later else "") +
                        "Поменять всё можно: правый клик → «Настройки» или «Знакомство и подключения».")
        s.ob_button("Готово", s.ob_win.destroy, main=True)
        s.say(f"Готово, {s.addr()}! Если что — правый клик по мне.", 5, speak=True)

    # --- память: импорт, просмотр, экспорт ---
    def import_facts(s, facts):
        n = 0
        for f in facts:
            if NEVER.search(f["fact"]) or any(match(f["fact"], m["fact"]) > 0.85 for m in s.memory):
                continue
            s.memory.append({"fact": f["fact"], "t": time.time(), "private": bool(f.get("private"))})
            n += 1
        from .pet_smart import MEMORY
        write_json(MEMORY, s.memory[-500:])
        return n

    def memory_import_window(s, facts=None):
        """Вставить текст или файл → факты с галочками → сохранить отмеченные. Всё локально."""
        w = tk.Toplevel(s.root)
        w.title("Импорт памяти Клодика")
        w.attributes("-topmost", True)
        w.configure(bg=PAPER, padx=12, pady=10)
        tk.Label(w, text="Вставь текст о себе или открой файл (.md/.txt/.json). Я разберу его на факты — сохраню "
                         "только отмеченные.\nКак перенести из Gemini: спроси его «перечисли всё, что ты знаешь обо мне» "
                         "и вставь ответ (или Google Takeout). Из ChatGPT/Claude — так же.\nПароли, ключи, карты и "
                         "документы я не сохраняю никогда; деликатное помечено ⚠.",
                 bg=PAPER, fg=INK, font=("Segoe UI", 9), justify="left", wraplength=620).pack(anchor="w")
        txt = tk.Text(w, width=80, height=6, font=("Segoe UI", 9))
        txt.pack(fill="x", pady=6)
        lst = tk.Frame(w, bg=PAPER)
        lst.pack(fill="both", expand=True)
        cv = tk.Canvas(lst, bg=PAPER, height=260, width=640, highlightthickness=0)
        sb = tk.Scrollbar(lst, command=cv.yview)
        inner = tk.Frame(cv, bg=PAPER)
        inner.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.create_window((0, 0), window=inner, anchor="nw")
        cv.configure(yscrollcommand=sb.set)
        cv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        state = {"facts": [], "vars": []}

        def show(fs):
            for c in inner.winfo_children():
                c.destroy()
            state["facts"], state["vars"] = fs, []
            for f in fs:
                v = tk.BooleanVar(value=not f["touchy"])
                tk.Checkbutton(inner, text=("⚠ " if f["touchy"] else "") + ("🔒 " if f["private"] else "") + f["fact"],
                               variable=v, bg=PAPER, wraplength=600, justify="left", anchor="w").pack(fill="x", anchor="w")
                state["vars"].append(v)

        def from_text():
            show(parse_facts(txt.get("1.0", "end")))

        def from_file():
            from tkinter import filedialog
            p = filedialog.askopenfilename(parent=w, filetypes=[("Текст", "*.md *.txt *.json"), ("Все", "*.*")])
            if p:
                raw = open(p, encoding="utf-8", errors="replace").read()
                try:
                    data = json.loads(raw)
                    raw = "\n".join(str(x.get("fact", x)) if isinstance(x, dict) else str(x)
                                    for x in (data if isinstance(data, list) else data.values()))
                except ValueError:
                    pass
                show(parse_facts(raw))

        def save():
            chosen = [f for f, v in zip(state["facts"], state["vars"]) if v.get()]
            n = s.import_facts(chosen)
            s.say(f"Запомнил {n} новых фактов.", 3, speak=True)
            w.destroy()
        row = tk.Frame(w, bg=PAPER)
        row.pack(fill="x", pady=(6, 0))
        for text, cmd in (("Разобрать текст", from_text), ("Открыть файл…", from_file), ("Сохранить отмеченные", save),
                          ("Всё, что я знаю о тебе", s.recall_window), ("Экспорт", s.memory_export),
                          ("Стереть всю память", lambda: s.gate("memory_wipe", "стереть всю память о тебе",
                                                                lambda: s.forget_fact("всё")))):
            tk.Button(row, text=text, command=cmd, relief="flat", padx=8).pack(side="left", padx=2)
        if facts:
            show(facts)
        return w

    def recall_window(s):
        w = tk.Toplevel(s.root)
        w.title("Что Клодик знает о тебе")
        w.attributes("-topmost", True)
        w.configure(bg=PAPER, padx=10, pady=10)
        box = tk.Listbox(w, width=100, height=20, font=("Segoe UI", 9))
        box.pack(fill="both", expand=True)
        for f in s.memory:
            box.insert("end", ("🔒 " if f.get("private") else "") + f["fact"])

        def forget():
            for i in reversed(box.curselection()):
                s.memory.pop(i)
                box.delete(i)
            from .pet_smart import MEMORY
            write_json(MEMORY, s.memory)
        tk.Button(w, text="Забыть выбранное", command=forget, relief="flat").pack(anchor="w", pady=(6, 0))
        return w

    def memory_export(s):
        path = os.path.join(special_dir(0x05) or HERE, "klodik_memory_export.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write("# Память Клодика (экспорт)\n\n" + "\n".join(("- [личное] " if m.get("private") else "- ") + m["fact"]
                                                                 for m in s.memory) + "\n")
        s.say(f"Сохранил память в «Документы\\klodik_memory_export.md»", 4, speak=True)
        return path

    def onboard_command(s, seg):
        if re.search(r"что (?:ещё|еще) можно подключить|подключи (?:что-нибудь|функции)|знакомств", seg):
            return lambda: s.onboarding()
        if m := re.match(r"^(?:называй меня|зови меня|меня зовут)\s+(.+)$", seg):
            def go(n=m[1].strip()):
                f = s.set_name(n.title(), (s.profile or {}).get("lang"))
                s.say(f"Буду звать тебя {s.addr()}!" + ("" if f["sure"] else " Если склоняю неправильно — поправь "
                                                                             "в «Знакомство»."), 4, speak=True)
            return go
        if re.search(r"импорт\w* памят", seg):
            # есть стартовая память — сразу показать её факты с галочками; сохранится только отмеченное
            return lambda: s.memory_import_window(parse_facts(open(SEED, encoding="utf-8").read())
                                                  if os.path.exists(SEED) else None)
        if re.search(r"экспорт\w* памят", seg):
            return s.memory_export
        return None


def klodik_photo_small():
    from .install import klodik_photo
    return klodik_photo(96, 1)
