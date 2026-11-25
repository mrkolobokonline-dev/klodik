"""Характер и развлечения: знает, во что ты играешь; танцует, когда играет музыка; злится и удивляется;
характер на выбор; мини-игры (камень-ножницы-бумага, угадай число, викторина, лови печеньки)."""
from .common import *  # noqa: F401,F403
from .apps import *  # noqa: F401,F403
from .winapi import *  # noqa: F401,F403
from .monitor import *  # noqa: F401,F403
from .brain import *  # noqa: F401,F403
from .voice import *  # noqa: F401,F403
from .sprites import *  # noqa: F401,F403

PERSONAS = {
    "kind": ("Добряк", "Ты добрый, весёлый и заботливый.", ["Сейчас!", "Бегу!", "Есть!", "Щас сделаю"]),
    "sassy": ("Дерзкий", "Ты дерзкий и саркастичный, по-доброму подкалываешь хозяина, но без грубости и мата.",
              ["Ну ладно, так уж и быть", "Опять я?", "Сделаю, сделаю", "Легкотня"]),
    "butler": ("Дворецкий (как Джарвис)", "Ты вежливый дворецкий, как Джарвис: обращаешься «сэр», говоришь чинно, "
               "с лёгкой иронией.", ["Слушаюсь, сэр", "Будет исполнено, сэр", "Сию минуту, сэр"]),
    "pirate": ("Пират", "Ты весёлый пират: «йо-хо-хо», «тысяча чертей», морские словечки.",
               ["Есть, капитан!", "Йо-хо-хо, бегу!", "Тысяча чертей, сделаю!"]),
}
PERSONA_WORDS = {"добр": "kind", "дерзк": "sassy", "наглы": "sassy", "дворецк": "butler", "джарвис": "butler",
                 "пират": "pirate"}
GAME_NAMES = {"diabloimmortal": "Diablo Immortal", "cs2": "Counter-Strike 2", "dota2": "Dota 2",
              "tslgame": "PUBG", "forzahorizon6": "Forza Horizon 6", "robloxplayerbeta": "Roblox",
              "fortniteclient-win64-shipping": "Fortnite", "genshinimpact": "Genshin Impact", "hogwartslegacy": "Хогвартс"}
RPS = {"камен": "камень", "ножниц": "ножницы", "бумаг": "бумага"}
BEATS = {"камень": "ножницы", "ножницы": "бумага", "бумага": "камень"}
EMO_WORDS = {"радост": "joy", "скук": "boredom", "интерес": "interest", "усталост": "tired", "грус": "sad",
             "удивлен": "surprise", "смущен": "embarrassed", "гордост": "pride", "испуг": "fear", "страх": "fear",
             "сомнен": "doubt", "благодарн": "gratitude", "нежност": "tenderness", "злост": "playful_anger"}
ANGRY = ["Хватит тыкать!", "Ай! Ну сколько можно!", "Я тебе не кнопка!", "Щас как укушу!"]


def game_name(exe):
    key = exe.lower()
    if key in GAME_NAMES:
        return GAME_NAMES[key]
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", exe).replace("_", " ").strip() or exe


class AudioMeter:
    """Насколько громко сейчас играют колонки (0..1) — по счётчику Windows, без записи звука."""
    def __init__(s):
        s.peak, s.ok = 0.0, False
        threading.Thread(target=s.run, daemon=True).start()

    def run(s):
        try:
            import comtypes
            from ctypes import POINTER, cast
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioMeterInformation
            comtypes.CoInitialize()
            dev = AudioUtilities.GetSpeakers()
            meter = cast(getattr(dev, "_dev", dev).Activate(IAudioMeterInformation._iid_, CLSCTX_ALL, None),
                         POINTER(IAudioMeterInformation))
            s.ok = True
            while True:
                s.peak = float(meter.GetPeakValue())
                time.sleep(0.12)
        except Exception as e:  # нет pycaw или звуковой карты — просто не танцуем
            log_error(f"счётчик звука: {e}")


class PetFun:
    def fun_load(s):
        s.persona = getattr(s, "persona", "kind")
        s.meter = AudioMeter()
        s.loud, s.quiet = 0.0, 0.0                    # сколько секунд подряд громко / тихо
        s.pokes, s.angry_until, s.wow_until, s.dance_until = [], 0.0, 0.0, 0.0
        s.game = None
        s.cur_game, s.game_started = None, 0.0

    # --- характер ---
    def persona_prompt(s):
        return SYSTEM + " " + PERSONAS.get(s.persona, PERSONAS["kind"])[1]

    def ack(s):
        return random.choice(PERSONAS.get(s.persona, PERSONAS["kind"])[2])

    def set_persona(s, p):
        s.push_undo("характер", lambda prev=s.persona: s.set_persona(prev))
        s.persona = p
        if hasattr(s, "persona_var"):
            s.persona_var.set(p)
        s.save()
        s.say({"kind": "Снова добряк!", "sassy": "Ну что, теперь я дерзкий. Терпи!",
               "butler": "К вашим услугам, сэр.", "pirate": "Йо-хо-хо! Теперь я пират!"}[p], 3, speak=True)

    # --- игры на компе ---
    def game_watch(s):
        """Раз в 10 с: началась/закончилась игра → запоминаю, после — спрашиваю, как поиграл."""
        if s.gaming:
            h = u32.GetForegroundWindow()
            pid = wt.DWORD()
            u32.GetWindowThreadProcessId(h, ctypes.byref(pid))
            name = os.path.splitext(proc_name(pid.value))[0]
            if name and not s.cur_game:
                s.cur_game, s.game_started = game_name(name), time.time()
        elif s.cur_game:
            played, name = time.time() - s.game_started, s.cur_game
            s.cur_game = None
            if played > 600 and s.on("game_talk") and not s.quiet_now():
                s.root.after(4000, lambda: s.say(random.choice([
                    f"Как поиграл в {name}? {fmt_secs(played)} — серьёзно!", f"С возвращением из {name}! Победил?",
                    f"{name}: {fmt_secs(played)}. Рассказывай, как оно?"]), 6, speak=True))

    def games_today(s):
        g = s.day.get("games", {})
        if not g:
            return s.say("Сегодня ты ещё не играл", 2, speak=True)
        s.say("Сегодня играл: " + ", ".join(f"{game_name(k)} — {fmt_secs(v)}" for k, v in
                                            sorted(g.items(), key=lambda x: -x[1])), 6, speak=True)

    def diablo_hint(s):
        """Вечером, если Diablo Immortal есть, а сегодня в неё не заходил — напомнить про ежедневки."""
        if time.localtime().tm_hour < 19 or s.day.get("diablo_hint") == s.day.get("date"):
            return False
        has = any("diablo" in g.lower() for g in s.games)
        played = any("diablo" in k.lower() for k in s.day.get("games", {}))
        if has and not played:
            s.day["diablo_hint"] = s.day.get("date")
            s.day_save()
            s.say("Не забудь ежедневки в Diablo Immortal! Скажи «открой диабло» — сбегаю.", 8, speak=True)
            return True
        return False

    # --- танцы и эмоции ---
    def mood_tick(s, dt):
        if s.state == "dance" and s.clock < s.dance_until:     # танцует по просьбе — ещё не время заканчивать
            return
        if s.state == "dance" and (not s.meter.ok or s.dance_until):
            s.dance_until = 0.0
            if not s.meter.ok or s.meter.peak < 0.08:
                s.state, s.timer = "idle", 2
                return
        if not s.meter.ok or s.speaker.speaking() or s.gaming or not s.on("dance"):
            return
        p = s.meter.peak
        if p > 0.85 and s.quiet > 3 and s.state in ("idle", "walk", "sleep"):   # резкий громкий звук после тишины
            s.emote("fear", "light")
        if p > 0.08:
            s.loud, s.quiet = s.loud + dt, 0.0
        else:
            s.quiet, s.loud = s.quiet + dt, 0.0 if s.quiet > 1 else s.loud
        if s.state in ("idle", "walk") and not s.surface and s.loud > 2.5 and not s.busy:
            s.state, s.timer = "dance", 9999
            if random.random() < 0.4:
                s.say(random.choice(["Музыка! Танцуем!", "О, качает!", "Йе-е!"]), 2)
        elif s.state == "dance" and s.quiet > 3:
            s.state, s.timer = "idle", 2

    def dance(s, secs=6):
        s.drop()
        s.state, s.timer, s.dance_until = "dance", 9999, s.clock + secs
        s.say(random.choice(["Смотри, как умею!", "Тыц-тыц-тыц!", "Диско!"]), 2, speak=True)

    # --- эмоции (машина клипов — anim.py, словарь — data/emotions.json) ---
    def emote(s, emo, level="medium"):
        """Показать эмоцию анимацией. Молчит в играх, в режиме «я работаю» и при «Режиме без эмоций»."""
        if s.gaming or s.prefs.get("working") or s.prefs.get("no_emotions"):
            return None
        return s.emo.emote(emo, level, s.clock, s.prefs.get("anim", "max"), s.prefs.get("emo", "lively"))

    def set_working(s, on):
        s.prefs["working"] = bool(on)
        s.save()
        s.say("Понял, не мешаю: только важные напоминания. Скажи «я закончил», когда освободишься." if on
              else "Ура, можно снова болтать!", 3, speak=True)

    def ambient_emotions(s):
        """Раз в 10 с: изредка показать настроение — скучно, устал, грустно, интересно. Без давления и упрёков."""
        if s.state not in ("idle", "walk") or s.busy or s.emo.clip or s.quiet_now():
            return
        idle_for = s.clock - getattr(s, "last_touch", 0.0)
        r = random.random()
        if s.sad and r < 0.05:
            s.emote("sad", "light")
        elif is_night() and r < 0.06:
            s.emote("tired", random.choice(["light", "medium"]))
        elif idle_for > 900 and r < 0.05:
            s.emote("boredom", "light")
        elif r < 0.02:
            s.emote(random.choice(["interest", "joy", "tenderness"]), "light")

    def poke(s):
        """Клик по Клодику. 5 кликов за 4 секунды — злится и не открывает ввод."""
        now = s.clock
        s.pokes = [t for t in s.pokes if now - t < 4] + [now]
        if len(s.pokes) >= 5:
            s.pokes, s.angry_until = [], now + 3
            s.mood_add(-5)
            s.vy = -150.0
            s.say(random.choice(ANGRY), 2, speak=True)
            s.emote("playful_anger", "strong")
            return True
        return False

    def landed_hard(s, height):
        if height > 300:
            s.wow_until = s.clock + 1.2
            s.emote("surprise", "strong" if height > 600 else "medium")
            s.say(random.choice(["Ого!", "Ай, мягко…", "Вот это полёт!"]), 1.5)

    # --- мини-игры ---
    def start_game(s, kind):
        s.game = {"kind": kind, "t": s.clock, "score": 0, "tries": 0}
        if kind == "rps":
            s.say("Камень, ножницы или бумага? Говори! («хватит» — закончить)", 15, speak=True)
        elif kind == "number":
            s.game["secret"] = random.randint(1, 100)
            s.say("Я загадал число от 1 до 100. Угадывай!", 15, speak=True)
        elif kind == "quiz":
            s.quiz_next()
        elif kind == "catch":
            s.game.update(left=30.0, spawn=0.0, cookies=[])
            s.say("Лови печеньки мышкой! 30 секунд, поехали!", 3, speak=True)
        s.talk_until = s.clock + 30

    def quiz_next(s):
        s.say("Придумываю вопрос…", 5)

        def go():
            try:
                out = s.llm("Ты ведущий викторины. Пиши по-русски.",
                            "Придумай один интересный вопрос для викторины (игры, кино, наука, животные, история) "
                            "с коротким ответом. Формат строго:\nВОПРОС: …\nОТВЕТ: … (1–3 слова)", 120) or ""
                q, a = re.search(r"ВОПРОС:\s*(.+)", out), re.search(r"ОТВЕТ:\s*(.+)", out)
                s.answers.put(("quiz", json.dumps({"q": q[1].strip(), "a": a[1].strip(" .«»")} if q and a else {},
                                                  ensure_ascii=False)))
            except (OSError, ValueError, KeyError):
                s.answers.put(("quiz", "{}"))
        threading.Thread(target=go, daemon=True).start()

    def quiz_got(s, payload):
        d = json.loads(payload)
        if not s.game or s.game["kind"] != "quiz":
            return
        if not d:
            s.game = None
            return s.say("Мозги не придумали вопрос — нужен «ИИ на компе».", 3, speak=True)
        s.game.update(q=d["q"], a=d["a"])
        s.say(d["q"], 25, speak=True)
        s.talk_until = s.clock + 40

    def game_input(s, text):
        """Ответ в мини-игре → True, если съел фразу."""
        g = s.game
        if not g or s.clock - g["t"] > 120:
            s.game = None
            return False
        t = num_words(text.lower().strip())
        if re.search(r"хватит|стоп|закончи|надоело|выход", t):
            s.end_game()
            return True
        g["t"] = s.clock
        if g["kind"] == "rps":
            mine = next((v for k, v in RPS.items() if k in t), None)
            if not mine:
                return False
            his = random.choice(list(BEATS))
            res = "Ничья!" if mine == his else "Ты выиграл!" if BEATS[mine] == his else "Я выиграл!"
            g["score"] += 1 if res == "Ты выиграл!" else 0
            g["tries"] += 1
            s.say(f"У меня {his}! {res} ({g['score']}:{g['tries'] - g['score']}) Ещё раз?", 6, speak=True)
            return True
        if g["kind"] == "number":
            m = re.search(r"\d+", t)
            if not m:
                return False
            n, g["tries"] = int(m[0]), g["tries"] + 1
            if n == g["secret"]:
                s.say(f"Угадал! Это {n}. Попыток: {g['tries']}.", 5, speak=True)
                s.hearts = 1.6
                s.game = None
            else:
                s.say("Больше!" if n < g["secret"] else "Меньше!", 3, speak=True)
            return True
        if g["kind"] == "quiz" and g.get("a"):
            right = g["a"].lower() in t or match(t, g["a"]) > 0.7 or any(match(w, g["a"]) > 0.8 for w in t.split())
            g["score"] += right
            g["tries"] += 1
            s.say(("Правильно! " if right else f"Неа, правильно — {g['a']}. ") + f"Счёт {g['score']} из {g['tries']}. "
                  "Следующий вопрос…", 5, speak=True)
            g["a"] = None
            s.root.after(2500, s.quiz_next)
            return True
        return False

    def end_game(s):
        g, s.game = s.game, None
        s.last_score = (g or {}).get("score", 0)
        for c in (g or {}).get("cookies", []):
            c.destroy()
        s.say(f"Игра окончена! Счёт: {g['score']}" + (f" из {g['tries']}" if g and g.get("tries") else "") + ".",
              4, speak=True)

    def catch_tick(s, dt):
        g = s.game
        if not g or g["kind"] != "catch":
            return
        g["left"] -= dt
        g["spawn"] -= dt
        if g["spawn"] <= 0 and g["left"] > 1:
            g["spawn"] = random.uniform(0.6, 1.3)
            c = Prop(s, "food", random.uniform(s.L + 40, s.R - 70), s.T + 10)
            c.cv.bind("<ButtonPress-1>", lambda e, c=c: s.catch_hit(c))
            g["cookies"].append(c)
        for c in list(g["cookies"]):
            c.y += (220 + 30 * g["score"] ** 0.5) * dt     # чем больше поймал, тем быстрее падают
            c.place()
            if c.y > s.B - Prop.SIZE:
                c.destroy()
                g["cookies"].remove(c)
        if g["left"] <= 0:
            g["tries"] = 0
            s.end_game()

    def catch_hit(s, c):
        g = s.game
        if g and c in g.get("cookies", []):
            g["cookies"].remove(c)
            c.destroy()
            g["score"] += 1
            s.hunger = max(0.0, s.hunger - 1)
            if g["score"] % 5 == 0:
                s.say(f"{g['score']}! Ещё!", 1)

    def fun_command(s, seg):
        if re.search(r"камень|ножницы|бумаг", seg) and re.search(r"сыгра|игра|давай", seg):
            return lambda: s.start_game("rps")
        if re.search(r"угадай\s+число|сыграем\s+в\s+числа|загадай\s+число", seg):
            return lambda: s.start_game("number")
        if re.search(r"викторин|задай\s+вопрос", seg):
            return lambda: s.start_game("quiz")
        if re.search(r"лови(?:ть)?\s+печень|поймай\s+печень|игра\s+в\s+печень", seg):
            return lambda: s.start_game("catch")
        if re.search(r"(?:сколько|во что)\s+я\s+(?:сегодня\s+)?(?:играл|наиграл)", seg):
            return s.games_today
        if m := re.search(r"(?:будь|стань|включи характер|характер)\s+(\w+)|как\s+(джарвис)", seg):
            p = next((v for k, v in PERSONA_WORDS.items() if (m[1] or m[2] or "").startswith(k)), None)
            if p:
                return lambda: s.set_persona(p)
        if m := re.search(r"(?:покажи|изобрази|сделай)\s+(?:эмоцию\s+)?(" + "|".join(EMO_WORDS) + r")\w*", seg):
            emo = next(v for k, v in EMO_WORDS.items() if m[1].startswith(k))
            return lambda: s.emote(emo, "strong")
        if re.search(r"^(?:спасибо|благодарю|спс|дякую)|молодец|умница|красавчик|ты лучший", seg):
            praise = bool(re.search(r"молодец|умница|красавчик|лучший", seg))
            return lambda: (s.emote("embarrassed" if praise else "gratitude", "medium"),
                            s.say(random.choice(["Ой, спасибо!", "Да ладно тебе…", "Стараюсь!"] if praise else
                                                ["Всегда пожалуйста!", "Обращайся!", "Рад помочь!"]), 2, speak=True))
        if re.search(r"я работаю|не мешай|режим работы клодика", seg):
            return lambda: s.set_working(True)
        if re.search(r"я (?:закончил|освободился)|можно мешать|хватит работать", seg):
            return lambda: s.set_working(False)
        if re.search(r"потанцуй|станцуй|танцуй", seg):
            return s.dance
        if re.search(r"(?:открой|покажи)\s+настройки|^настройки$", seg):
            return s.open_settings
        if re.search(r"проверь обновлени|обновись", seg):
            return lambda: s.check_update(manual=True)
        return None

    def open_settings(s):
        from .settings import open_settings                   # здесь — чтобы не было кругового импорта
        open_settings(s)

    def check_update(s, manual=False):
        from .update import VERSION, find_update, install_update

        def go():
            try:
                up = find_update()
            except Exception as e:  # нет интернета, GitHub недоступен
                return s.answers.put(("info", f"Не смог проверить обновления: {e}")) if manual else None
            if not up:
                return s.answers.put(("info", f"У меня последняя версия ({VERSION}).")) if manual else None
            s.answers.put(("info", f"Вышла новая версия {up[0]} — обновляюсь, через минуту вернусь!"))
            time.sleep(4)
            install_update(up[1])
        threading.Thread(target=go, daemon=True).start()
