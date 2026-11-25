"""Этап 6 (блоки B, C, F): косплей по процессу игры (своя таблица costumes.json), игровые таймеры и заметки, гайды
из папки guides/, топ игр за неделю, крестики-нолики и «кто быстрее», ворчун и робот, короткие/подробные ответы,
«что играет», белый шум/дождь и метроном (свои звуки, сгенерированы на месте), черновик ответа, формулы Excel,
разбор CSV локально, команда PowerShell — только показать. Античит: из игр ничего не читаем, только имя процесса."""
import array
import csv
import wave

from .common import *  # noqa: F401,F403
from .pet_tasks import read_json, write_json
from .pet_fun import PERSONAS, PERSONA_WORDS

COSTUMES = os.path.join(DATA_DIR, "costumes.json")
GNOTES = os.path.join(DATA_DIR, "game_notes.json")
GUIDES = os.path.join(DATA_DIR, "guides")
NOISE = os.path.join(DATA_DIR, "sounds")
# процесс (без .exe, в нижнем регистре) → своя шапка по архетипу: маг, разбойник, воин, гонщик, мастер
DEFAULT_COSTUMES = {"dota2": "wizard", "pathofexile": "hood", "pathofexile_x64": "hood", "pathofexilesteam": "hood",
                    "pathofexile_x64steam": "hood", "wow": "knight", "wowclassic": "knight", "diabloimmortal": "knight",
                    "diablo iv": "knight", "diablo4": "knight", "robloxplayerbeta": "geek", "robloxstudiobeta": "geek",
                    "needforspeedunbound": "helmet", "nfsheat": "helmet", "needforspeedheat": "helmet"}
GAME_TIMERS = {"рошан": ([480, 660], "Рошан может появиться"), "аегис": ([300], "Аегис пропадает"),
               "руны": ([120], "Руны"), "аванпост": ([600], "Аванпост")}
PERSONAS.update({
    "grumpy": ("Ворчун", "Ты ворчливый, но добрый внутри: бурчишь «ну вот опять», всё равно помогаешь, без грубости.",
               ["Ну вот опять…", "Ладно уж, сделаю", "Эх, ну давай", "Ворчу, но делаю"]),
    "robot": ("Робот", "Ты дружелюбный робот: говоришь чётко, «ВЫПОЛНЯЮ», «ПРИНЯТО», иногда «бип-буп».",
              ["ПРИНЯТО.", "ВЫПОЛНЯЮ. Бип-буп.", "КОМАНДА ПОЛУЧЕНА."])})
PERSONA_WORDS.update({"ворчун": "grumpy", "ворчл": "grumpy", "робот": "robot"})
PLAY_TASKS = {"ответ": "Напиши короткий вежливый черновик ответа на это сообщение (от первого лица). Только текст ответа:",
              "формул": "Объясни простыми словами, что делает эта формула Excel, по шагам:",
              "термин": "Объясни эти термины простыми словами, каждый в одну строку:"}


def make_noise(path, kind="white", secs=4, rate=22050):
    """Свой шум (не чужой файл): белый или «дождь» (сглаженный) — WAV в %APPDATA%."""
    rnd, a, prev = random.Random(1), array.array("h"), 0.0
    for _ in range(secs * rate):
        x = rnd.uniform(-1, 1)
        prev = prev * 0.92 + x * 0.08 if kind == "rain" else x
        a.append(int(prev * (9000 if kind == "rain" else 3000)))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(a.tobytes())
    return path


def ttt_winner(b):
    for i, j, k in ((0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)):
        if b[i] and b[i] == b[j] == b[k]:
            return b[i]
    return "draw" if all(b) else None


def ttt_move(b):
    """Ход Клодика (O): выиграть → помешать → центр → угол → что есть."""
    free = [i for i in range(9) if not b[i]]
    for who in ("O", "X"):
        for i in free:
            t = b[:]
            t[i] = who
            if ttt_winner(t) == who:
                return i
    fork = b[4] == "O" and (b[0] == b[8] == "X" or b[2] == b[6] == "X")   # ловушка «противоположные углы» → на ребро
    for i in ((1, 3, 5, 7) if fork else ()) + (4, 0, 2, 6, 8, 1, 3, 5, 7):
        if i in free:
            return i
    return None


def csv_summary(path, limit=50000):
    """Локальная сводка CSV: строки, столбцы, по числовым — мин/макс/среднее."""
    with open(path, encoding="utf-8-sig", errors="replace", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        rows = list(csv.reader(f, dialect))[:limit]
    if not rows:
        return "Файл пустой."
    head, data = rows[0], rows[1:]
    parts = [f"{len(data)} строк, {len(head)} столбцов: {', '.join(head[:8])}{'…' if len(head) > 8 else ''}."]
    for c, name in enumerate(head[:8]):
        nums = []
        for r in data:
            try:
                nums.append(float(r[c].replace(",", ".").replace(" ", "")))
            except (ValueError, IndexError):
                pass
        if len(nums) > len(data) * 0.6 and nums:
            parts.append(f"{name}: от {min(nums):g} до {max(nums):g}, среднее {sum(nums) / len(nums):.4g}")
    return " ".join(parts)


class PetPlay:
    def play_load(s):
        s.costumes = {**DEFAULT_COSTUMES, **read_json(COSTUMES, {})}
        if not os.path.exists(COSTUMES):
            write_json(COSTUMES, DEFAULT_COSTUMES)        # владелец дописывает сам: "процесс": "шапка"
        s.cos_hat, s.metro = None, False

    # ---------- косплей ----------
    def costume_tick(s):
        h = u32.GetForegroundWindow()
        pid = wt.DWORD()
        u32.GetWindowThreadProcessId(h, ctypes.byref(pid))
        from .winapi import proc_name
        name = os.path.splitext(proc_name(pid.value) or "")[0].lower()
        hat = s.costumes.get(name)
        if hat and hat != s.cos_hat and s.hat == "auto":
            s.cos_hat, s.key = hat, None
        elif not hat and s.cos_hat and name not in ("", "klodik", "pythonw"):
            s.cos_hat, s.key = None, None

    def top_games(s):
        names = set(s.costumes) | {k.lower() for k in s.day.get("games", {})}
        from .pet_fun import game_name
        tot = {}
        for day in s.track.values():
            for n, t in day.items():
                if n.lower() in names:
                    tot[n] = tot.get(n, 0) + t
        if not tot:
            return s.say("За неделю игр не насчитал (включи «Тайм-трекер» в «Функциях»).", 4, speak=True)
        from .pet_desk import fmt_secs
        top = sorted(tot.items(), key=lambda x: -x[1])[:3]
        medals = ["🥇", "🥈", "🥉"]
        s.emote("pride", "medium")
        s.say("Топ игр недели: " + ", ".join(f"{medals[i]} {game_name(n)} — {fmt_secs(t)}" for i, (n, t) in enumerate(top)),
              8, speak=True)

    # ---------- игровой помощник: таймеры, заметки, гайды ----------
    def game_timer(s, key):
        times, label = GAME_TIMERS[key]
        for t in times:
            s.add_reminder(s.now() + t, f"{label} ({t // 60} мин)")

    def game_note(s, topic, text):
        notes = read_json(GNOTES, {})
        notes.setdefault(topic.lower(), []).append(text)
        write_json(GNOTES, notes)
        s.say(f"Записал про {topic}.", 3)

    def game_recall(s, topic):
        notes = read_json(GNOTES, {}).get(topic.lower(), [])
        guide = []
        if os.path.isdir(GUIDES):
            for f in os.listdir(GUIDES):
                if f.endswith((".txt", ".md")):
                    for line in open(os.path.join(GUIDES, f), encoding="utf-8", errors="replace"):
                        if topic.lower() in line.lower():
                            guide.append(line.strip())
        if not notes and not guide:
            return s.say(f"Про {topic} у меня ничего нет — не буду выдумывать. Положи гайд в %APPDATA%\\Klodik\\guides.",
                         6, speak=True)
        s.say(f"Про {topic}: " + " | ".join((notes + guide)[:4])[:400], 12, speak=True)

    # ---------- мини-игры ----------
    def points(s, n):
        s.prefs["points"] = s.prefs.get("points", 0) + n
        s.save()

    def tictactoe(s):
        w = tk.Toplevel(s.root)
        w.title("Крестики-нолики с Клодиком")
        w.attributes("-topmost", True)
        b, btns = [""] * 9, []

        def end(res):
            msg = {"X": "Ты выиграл! +3 очка", "O": "Я выиграл! Реванш?", "draw": "Ничья! +1 очко"}[res]
            s.points(3 if res == "X" else 1 if res == "draw" else 0)
            s.emote("embarrassed" if res == "X" else "pride" if res == "O" else "joy", "medium")
            s.say(msg, 4, speak=True)
            for x in btns:
                x.config(state="disabled")

        def click(i):
            if b[i] or ttt_winner(b):
                return
            b[i] = "X"
            btns[i].config(text="X")
            if (r := ttt_winner(b)):
                return end(r)
            j = ttt_move(b)
            b[j] = "O"
            btns[j].config(text="O", fg=ORANGE)
            if (r := ttt_winner(b)):
                end(r)
        for i in range(9):
            x = tk.Button(w, text="", width=4, height=2, font=("Segoe UI", 16, "bold"), command=lambda i=i: click(i))
            x.grid(row=i // 3, column=i % 3)
            btns.append(x)
        return w

    def reaction(s):
        """«Кто быстрее»: жди зелёный и жми."""
        w = tk.Toplevel(s.root)
        w.title("Кто быстрее")
        w.attributes("-topmost", True)
        lab = tk.Label(w, text="Жди зелёный… потом жми!", width=30, height=6, bg="#c0392b", fg="white",
                       font=("Segoe UI", 14, "bold"))
        lab.pack()
        st = {"go": None}

        def go():
            st["go"] = time.perf_counter()
            lab.config(bg="#27ae60", text="ЖМИ!")

        def hit(_=None):
            if st["go"] is None:
                lab.config(text="Рано! Попробуй ещё раз.")
                return
            ms = int((time.perf_counter() - st["go"]) * 1000)
            st["go"] = None
            lab.config(bg="#34495e", text=f"{ms} мс")
            best = s.prefs.get("best_react")
            if not best or ms < best:
                s.prefs["best_react"] = ms
                s.points(2)
                s.say(f"Рекорд — {ms} мс!", 3, speak=True)
            w.after(1200, lambda: (lab.config(bg="#c0392b", text="Жди зелёный…"), w.after(random.randint(1500, 4000), go)))
        lab.bind("<Button-1>", hit)
        w.after(random.randint(1500, 4000), go)
        return w

    # ---------- музыка и звуки ----------
    def now_playing(s):
        from .winapi import list_windows
        for w in list_windows():
            if w["proc"].lower().startswith("spotify") and " - " in w["title"]:
                return s.say(f"Играет: {w['title']}", 5, speak=True)
        s.say("Не вижу, что играет (поддерживаю Spotify по заголовку окна).", 4, speak=True)

    def noise(s, kind):
        if kind == "stop":
            winsound.PlaySound(None, 0)
            s.metro = False
            return s.say("Выключил звуки.", 2)
        path = os.path.join(NOISE, f"{kind}.wav")
        if not os.path.exists(path):
            make_noise(path, kind)
        winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP)
        s.say({"white": "Белый шум включён.", "rain": "Включил дождик за окном."}[kind] + " «Выключи шум» — стоп.", 4)

    def metronome(s, bpm):
        s.metro = True

        def go():
            while s.metro:
                winsound.Beep(880, 40)
                time.sleep(max(0.2, 60 / bpm - 0.04))
        threading.Thread(target=go, daemon=True).start()
        s.say(f"Метроном {bpm} ударов. «Выключи метроном» — стоп.", 3)

    # ---------- ИИ: буфер, CSV, PowerShell ----------
    def clip_play(s, key):
        try:
            text = s.root.clipboard_get().strip()
        except tk.TclError:
            text = ""
        if not text:
            return s.say("В буфере пусто — скопируй текст (Ctrl+C) и попроси ещё раз.", 4, speak=True)
        s.thinking = True
        threading.Thread(target=lambda: s.answers.put((
            "clip_copy" if key == "ответ" else "clip_say",
            s.ai.ask("Ты помощник. По-русски, без вступлений.", f"{PLAY_TASKS[key]}\n\n{text[:5000]}",
                     task="explain", private=True, tokens=600))), daemon=True).start()

    def csv_analyze(s):
        roots = [os.path.join(os.path.expanduser("~"), d) for d in ("Downloads", "Desktop", "Documents")]
        files = [os.path.join(r, f) for r in roots if os.path.isdir(r) for f in os.listdir(r) if f.lower().endswith(".csv")]
        if not files:
            return s.say("CSV-файлов в Загрузках, на столе и в Документах не нашёл.", 4, speak=True)
        f = max(files, key=os.path.getmtime)
        try:
            s.say(f"«{os.path.basename(f)}» (разбирал локально): {csv_summary(f)}", 15, speak=True)
        except OSError as e:
            s.say(f"Не открыл файл: {e}", 4)

    def ps_suggest(s, what):
        s.thinking = True

        def go():
            try:
                cmd = s.ai.ask("Ты эксперт по PowerShell. Верни только одну команду PowerShell, без пояснений и ```.",
                               what, task="code", private=False, tokens=150).strip().strip("`")
                s.answers.put(("clip_copy", cmd + "\n# (Клодик только подсказал — проверь и запусти сам)"))
            except (OSError, ValueError, KeyError, RuntimeError) as e:
                s.answers.put(("clip_say", f"Мозги не ответили: {str(e)[:60]}"))
        threading.Thread(target=go, daemon=True).start()

    def play_command(s, seg):
        for key in GAME_TIMERS:
            if re.search(rf"таймер\w*\s+{key}", seg):
                return lambda k=key: s.game_timer(k)
        if m := re.match(r"(?:кулдаун|откат|респ\w*)\s+(?:\w+\s+)?(\d+)\s*(сек|мин)", seg):
            secs = int(m[1]) * (60 if m[2].startswith("мин") else 1)
            return lambda: s.add_reminder(s.now() + secs, "Готово!")
        if m := re.match(r"(?:заметка|запиши)\s+(?:про|о)\s+(\w+)\s*:\s*(.+)", seg):
            return lambda: s.game_note(m[1], m[2])
        if m := re.search(r"(?:что (?:я )?(?:записал|знаешь) про|гайд по|билд на)\s+(\w+)", seg):
            return lambda: s.game_recall(m[1])
        if re.search(r"топ игр|во что я играл за неделю", seg):
            return s.top_games
        if re.search(r"крестики|нолики", seg):
            return s.tictactoe
        if re.search(r"кто быстрее|на реакцию", seg):
            return s.reaction
        if re.search(r"сколько (?:у меня )?очков", seg):
            return lambda: s.say(f"У тебя {s.prefs.get('points', 0)} очков.", 3, speak=True)
        if re.search(r"отвечай (?:короче|коротко|кратко)", seg):
            return lambda: (s.set_pref("verbose", False), s.say("Буду короче.", 2))
        if re.search(r"отвечай подробн", seg):
            return lambda: (s.set_pref("verbose", True), s.say("Буду отвечать подробнее.", 2))
        if re.search(r"что (?:сейчас )?играет|какой трек|что за песня", seg):
            return s.now_playing
        if re.search(r"(?:выключи|убери|хватит)\s+(?:шум|дождь|звуки|метроном)", seg):
            return lambda: s.noise("stop")
        if re.search(r"белый шум", seg):
            return lambda: s.noise("white")
        if re.search(r"(?:включи|звуки)\s+дожд|дождь за окном", seg):
            return lambda: s.noise("rain")
        if m := re.search(r"метроном\s*(\d+)?", seg):
            return lambda: s.metronome(int(m[1] or 60))
        if re.search(r"черновик ответа|(?:как|помоги) ответить", seg):
            return lambda: s.clip_play("ответ")
        if re.search(r"объясни формулу|что делает формула", seg):
            return lambda: s.clip_play("формул")
        if re.search(r"объясни термин", seg):
            return lambda: s.clip_play("термин")
        if re.search(r"(?:разбери|проанализируй|что в)\s+(?:таблиц\w*\s+)?csv", seg):
            return s.csv_analyze
        if m := re.match(r"(?:какой командой|команда powershell|команду powershell)\s+(?:чтобы\s+)?(.+)", seg):
            return lambda: s.ps_suggest(m[1])
        return None
