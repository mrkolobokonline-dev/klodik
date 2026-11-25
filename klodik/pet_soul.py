"""Живой Клодик (блок I): настроение из событий, мысли облачком, любопытство, свой дневник, сны, встреча после
паузы, жизнь без владельца, черты-ползунки, любимое, взросление, ритуалы, день рождения. Файл «душа» —
%APPDATA%\\Klodik\\soul.json (смотреть/править/сбросить в окне «Душа Клодика»).
Границы: никакой вины, давления и ревности; грусть и потребности не влияют на команды и безопасность;
личное владельца в дневник и сны не пишется; «Режим без эмоций» выключает всё это одним переключателем."""
import datetime as dt

from .common import *  # noqa: F401,F403
from .pet_tasks import read_json, write_json

SOUL = os.path.join(DATA_DIR, "soul.json")
BAD_DAY = re.compile(r"устал от всего|мне плохо|всё плохо|все плохо|грустно|тоскливо|депресс|не хочу ничего|"
                     r"всё бесит|все бесит|одиноко|хреново|паршиво", re.I)
WIN = re.compile(r"победил|выиграл|сдал|получилось|сделал наконец|закончил проект|апнул|ммр вырос", re.I)
QUESTIONS = {"Какой у тебя любимый цвет?": "цвет", "А какая у тебя любимая игра сейчас?": "игра",
             "Что слушаешь в последнее время?": "музыка", "Какая еда у тебя самая любимая?": "еда",
             "Над чем сейчас работаешь?": "работа", "Какой фильм пересматривал бы бесконечно?": "фильм"}
ACTIVITIES = [("книжку читал", "book"), ("мячик гонял", "ball"), ("по окнам гулял", "walk"), ("вздремнул", "sleep"),
              ("рисовал мелом", "draw")]


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


def idle_seconds():
    """Сколько секунд владелец не трогал мышь и клавиатуру (системный счётчик, без слежки за содержимым)."""
    li = LASTINPUTINFO()
    li.cbSize = ctypes.sizeof(li)
    u32.GetLastInputInfo(ctypes.byref(li))
    return (k32.GetTickCount() - li.dwTime) / 1000.0


def default_soul():
    return {"born": dt.date.today().isoformat(), "traits": {"доброта": 80, "любопытство": 70, "лень": 30, "юмор": 70},
            "quirks": ["боится пылесоса", "мечтает увидеть море", "считает печеньки лучшей едой на свете"],
            "goals": ["выучить любимую игру владельца", "научиться понимать его с полуслова"],
            "bio": "Я Клодик — пиксельный помощник. Появился на этом компьютере и живу внизу экрана.",
            "favorites": {}, "level": 1, "xp": 0, "diary": [], "dreams": [], "moments": [], "asked": [],
            "mood": {"joy": 0.5, "boredom": 0.0, "interest": 0.4, "tired": 0.0, "sad": 0.0}}


class PetSoul:
    def soul_load(s):
        s.soul = {**default_soul(), **read_json(SOUL, {})}
        s.away = None                                   # когда владелец ушёл (по простою мыши/клавиатуры)
        s.away_log = []
        s.next_thought = random.uniform(600, 1200)          # clock стартует с 0

    def soul_save(s):
        write_json(SOUL, s.soul)

    def alive(s):
        return not s.prefs.get("no_emotions")

    # --- настроение: события сдвигают, со временем всё плавно возвращается к норме ---
    def feel(s, emo, amount):
        m = s.soul["mood"]
        if emo in m:
            m[emo] = max(0.0, min(1.0, m[emo] + amount))

    def mood_drift(s, dt_s):
        m = s.soul["mood"]
        for k in m:                                      # плавно к норме: любопытство 0.4, радость 0.3, остальное 0
            m[k] += ({"interest": 0.4, "joy": 0.3}.get(k, 0.0) - m[k]) * min(1, dt_s / 1800)
        h = time.localtime().tm_hour
        if h >= 23 or h < 6:
            s.feel("tired", 0.02)
        if s.stats.cpu > 90:
            s.feel("tired", 0.01)

    def dominant(s):
        m = s.soul["mood"]
        k = max(m, key=m.get)
        return (k, "strong" if m[k] > 0.8 else "medium" if m[k] > 0.55 else "light") if m[k] > 0.35 else (None, None)

    def gain(s, xp, why=""):
        """Взросление: опыт за общение и дела; уровень медленно растёт (можно выключить — «Режим без эмоций»)."""
        s.soul["xp"] += xp
        need = 100 * s.soul["level"]
        if s.soul["xp"] >= need:
            s.soul["xp"] -= need
            s.soul["level"] += 1
            s.moment(f"дорос до уровня {s.soul['level']}")
            s.emote("pride", "strong")
            s.say(f"Ого, я подрос — уровень {s.soul['level']}! Спасибо, что общаешься со мной.", 5, speak=True)
        s.soul_save()

    def moment(s, text):
        s.soul["moments"] = (s.soul["moments"] + [{"d": dt.date.today().isoformat(), "t": text}])[-100:]

    # --- мысли облачком и любопытство (модель локальная, вызовы редкие) ---
    def think_aloud(s):
        if not (s.alive() and s.on("thoughts")) or s.quiet_now() or s.gaming or s.prefs.get("working") or s.busy:
            return
        emo, _ = s.dominant()
        favs = ", ".join(f"{k}: {v}" for k, v in s.soul["favorites"].items()) or "ещё не знаю"
        moments = [m["t"] for m in s.soul["moments"][-5:]]

        def go():
            try:
                out = s.llm("Ты Клодик — пиксельный питомец на рабочем столе. Пиши по-русски, одну короткую мысль вслух "
                            "(до 80 символов), без вопросов к владельцу, без его личных данных, без вины и давления.",
                            f"Время {time.strftime('%H:%M')}. Настроение: {emo or 'спокойное'}. Мои причуды: "
                            f"{'; '.join(s.soul['quirks'])}. Моё любимое: {favs}. Было: {'; '.join(moments) or 'ничего'}. "
                            "Подумай вслух о чём-то своём (можно «а помнишь…», если было что вспомнить).", 60)
                if out:
                    s.answers.put(("thought", out.strip().strip("«»\"")[:120]))
            except (OSError, ValueError, KeyError):
                pass
        threading.Thread(target=go, daemon=True).start()

    def show_thought(s, text):
        s.say(f"( {text} )", 6)
        s.emote(random.choice(["interest", "doubt", "tenderness"]), "light")
        s.write_diary(f"подумал: {text}")

    def curious(s):
        """Не чаще 2 раз в день спросить что-то о владельце — ответ сам попадёт в память (если включено)."""
        today = dt.date.today().isoformat()
        asked_today = [a for a in s.soul["asked"] if a["d"] == today]
        if len(asked_today) >= 2 or not s.on("thoughts") or s.quiet_now() or s.busy:
            return
        left = [q for q in QUESTIONS if q not in [a["q"] for a in s.soul["asked"]]]
        if not left:
            return
        q = random.choice(left)
        s.soul["asked"] = (s.soul["asked"] + [{"d": today, "q": q}])[-50:]
        s.soul_save()
        s.emote("interest", "medium")
        s.pending_q = (QUESTIONS[q], s.clock)
        s.say(q + " (кликни по мне, если хочешь ответить)", 12, speak=True)

    # --- свой дневник и сны (без личного владельца) ---
    def write_diary(s, text):
        if not s.alive() or s.clock - getattr(s, "bad_day", -9999) < 3600:   # в плохой день — ничего не записываю
            return
        s.soul["diary"] = (s.soul["diary"] + [{"d": time.strftime("%Y-%m-%d %H:%M"), "t": text[:200]}])[-300:]
        s.soul_save()

    def dream(s):
        """Ночью, пока владельца нет и Клодик спит, — один сон за ночь; утром расскажет."""
        today = dt.date.today().isoformat()
        if any(d["d"] == today for d in s.soul["dreams"]) or not s.alive():
            return

        def go():
            try:
                out = s.llm("Ты Клодик. Опиши свой сон одним-двумя короткими смешными предложениями, по-русски, "
                            "без личных данных владельца.", f"Мои причуды: {'; '.join(s.soul['quirks'])}.", 80)
                if out:
                    s.soul["dreams"] = (s.soul["dreams"] + [{"d": today, "t": out.strip()}])[-60:]
                    s.soul_save()
            except (OSError, ValueError, KeyError):
                pass
        threading.Thread(target=go, daemon=True).start()

    def last_dream(s):
        d = s.soul["dreams"][-1] if s.soul["dreams"] else None
        return d["t"] if d and d["d"] in (dt.date.today().isoformat(),
                                          (dt.date.today() - dt.timedelta(days=1)).isoformat()) else None

    # --- владелец ушёл / вернулся; жизнь без него ---
    def presence_tick(s):
        idle = idle_seconds()
        if idle > 300 and not s.away and not s.gaming:
            s.away = time.time() - idle                    # ушёл
            s.away_log = []
        if s.away and idle > 300:
            if random.random() < 0.02 and s.state in ("idle", "walk") and not s.busy:
                what, kind = random.choice(ACTIVITIES)     # своя жизнь, пока никого нет
                s.away_log.append(what)
                if kind == "book":
                    s.carry = ("book", s.clock + 40)
                    s.state, s.timer = "idle", 40
                elif kind == "ball" and not s.ball:
                    s.toggle_ball()
                elif kind == "sleep":
                    s.sleep()
                elif kind == "draw":
                    s.emote("boredom", "medium")
            if is_night() and s.state == "sleep":
                s.dream()
        elif s.away and idle < 5:                          # вернулся
            gone, log, s.away = time.time() - s.away, s.away_log, None
            if s.ball and "мячик гонял" in log:
                s.toggle_ball()
            s.welcome_back(gone, log)

    def welcome_back(s, gone, log):
        if not s.alive() or s.quiet_now() or s.prefs.get("working") or s.gaming or gone < 1800:
            return
        name = s.addr()
        what = (" Пока тебя не было, я " + ", ".join(dict.fromkeys(log)) + ".") if log else ""
        if gone > 6 * 3600:
            text = f"О, {name}, привет! Давно не виделись.{what}" if name else f"Привет! Давно не виделись.{what}"
            s.emote("joy", "strong")
        else:
            text = f"С возвращением{', ' + name if name else ''}!{what}"
            s.emote("tenderness", "medium")
        s.say(text, 7, speak=True)
        s.feel("joy", 0.3)
        s.feel("boredom", -0.5)

    # --- ритуалы и праздники ---
    def rituals(s):
        h, today = time.localtime().tm_hour, dt.date.today()
        done = s.soul.setdefault("rituals", {})
        if h == 23 and done.get("night") != today.isoformat() and s.on("rituals") and idle_seconds() < 120 and not s.gaming:
            done["night"] = today.isoformat()
            s.emote("tired", "medium")
            s.say(f"Спокойной ночи{', ' + s.addr() if s.addr() else ''}! Я тоже скоро баиньки.", 6, speak=True)
        born = dt.date.fromisoformat(s.soul["born"])
        if (today.month, today.day) == (born.month, born.day) and today != born and done.get("bday") != today.isoformat():
            done["bday"] = today.isoformat()
            s.carry = ("cake", s.clock + 20)
            s.emote("joy", "strong")
            age = today.year - born.year
            s.moment(f"мой {age}-й день рождения")
            s.say(f"У меня сегодня день рождения — мне {age}! Спасибо, что я у тебя есть.", 8, speak=True)
        s.soul_save()

    # --- реакции на разговор ---
    def on_user_text(s, text):
        """Тон фразы → чувство. Плохой день — тепло и просто, без лекций; такое в дневник не пишем."""
        s.feel("boredom", -0.4)
        s.feel("joy", 0.05)
        pq = getattr(s, "pending_q", None)
        if pq and s.clock - pq[1] < 300 and len(text) < 60:   # ответ на мой вопрос — запомню как любимое
            s.note_favorite(pq[0], text.strip()[:40])
            s.pending_q = None
        if not s.alive():
            return "support" if BAD_DAY.search(text) else None
        s.gain(2)
        if BAD_DAY.search(text):
            s.emote("tenderness", "medium")
            s.bad_day = s.clock                            # пока «плохой день» — не пишем дневник и мысли
            return "support"
        if WIN.search(text):
            s.emote("joy", "strong")
            s.moment("владелец чем-то гордился, и мы радовались вместе")
            return "win"
        return None

    def note_favorite(s, kind, value):
        s.soul["favorites"][kind] = value
        s.soul_save()

    def soul_tick(s, dt_s):
        """Раз в 10 с."""
        s.mood_drift(dt_s)
        s.presence_tick()
        s.rituals()
        if s.clock > s.next_thought and not s.gaming:
            s.next_thought = s.clock + random.uniform(900, 2400) * (1.5 if s.soul["traits"]["лень"] > 60 else 1)
            if random.random() < s.soul["traits"]["любопытство"] / 400:
                s.curious()
            elif s.clock - getattr(s, "bad_day", -9999) > 3600:
                s.think_aloud()
        s.feel("boredom", 0.01)                          # без общения потихоньку скучает (без упрёков)

    # --- окно «Душа Клодика» ---
    def soul_window(s):
        w = tk.Toplevel(s.root)
        w.title("Душа Клодика")
        w.attributes("-topmost", True)
        w.configure(bg=PAPER, padx=12, pady=10)
        so = s.soul
        tk.Label(w, text=f"{so['bio']}\nДень рождения: {so['born']} · уровень {so['level']} ({so['xp']}/{100 * so['level']} опыта)\n"
                         f"Причуды: {'; '.join(so['quirks'])}\nЦели: {'; '.join(so['goals'])}\n"
                         f"Любимое: {', '.join(f'{k} — {v}' for k, v in so['favorites'].items()) or 'пока не выбрал'}",
                 bg=PAPER, fg=INK, justify="left", wraplength=560, font=("Segoe UI", 10)).pack(anchor="w")
        tk.Label(w, text="Черты (двигай — Клодик поменяет характер):", bg=PAPER, fg=DARK,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(8, 0))
        for k in list(so["traits"]):
            row = tk.Frame(w, bg=PAPER)
            row.pack(fill="x")
            tk.Label(row, text=k, width=12, anchor="w", bg=PAPER).pack(side="left")
            v = tk.IntVar(value=so["traits"][k])
            sc = tk.Scale(row, from_=0, to=100, orient="horizontal", variable=v, length=300, bg=PAPER, showvalue=True)
            sc.pack(side="left")
            sc.bind("<ButtonRelease-1>", lambda e, k=k, v=v: (so["traits"].__setitem__(k, v.get()), s.soul_save()))
        tk.Label(w, text="Мой дневник (последнее):", bg=PAPER, fg=DARK, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(8, 0))
        box = tk.Listbox(w, width=90, height=10, font=("Segoe UI", 9))
        box.pack(fill="both", expand=True)
        for e in reversed(so["diary"][-60:]):
            box.insert("end", f"{e['d']}  {e['t']}")
        for d in reversed(so["dreams"][-5:]):
            box.insert("end", f"{d['d']}  сон: {d['t']}")

        def reset():
            def ok():
                s.soul = default_soul()
                s.soul_save()
                w.destroy()
                s.say("Начинаю жизнь с чистого листа!", 3, speak=True)
            s.gate("soul_reset", "сбросить душу Клодика (характер, дневник, сны, уровень)", ok)
        tk.Button(w, text="Сбросить душу", command=reset, relief="flat").pack(anchor="w", pady=(6, 0))
        return w

    def soul_command(s, seg):
        if re.search(r"(?:покажи|открой)\s+(?:свою\s+)?душу|твой дневник|о себе расскажи|расскажи о себе", seg):
            return s.soul_window
        if re.search(r"что тебе снилось|какой (?:тебе )?сон", seg):
            return lambda: s.say(("Мне снилось: " + s.last_dream()) if s.last_dream() else "Не помню, что снилось…",
                                 6, speak=True)
        if re.search(r"ты живой", seg):
            return lambda: (s.emote("tenderness", "light"),
                            s.say("Я программа со своим характером и памятью, но стараюсь быть хорошим другом.", 6, speak=True))
        if re.search(r"как (?:у тебя )?настроение|как ты себя чувствуешь", seg):
            def tell():
                emo, lv = s.dominant()
                words = {"joy": "радостно", "boredom": "скучновато", "interest": "любопытно", "tired": "устал немножко",
                         "sad": "чуть грустно"}
                s.emote(emo or "joy", lv or "light")
                s.say(f"Мне {words.get(emo, 'спокойно')}. Уровень {s.soul['level']}.", 4, speak=True)
            return tell
        return None
