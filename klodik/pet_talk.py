"""Разговор и команды, таймеры, фото, друг."""
from .looks import skins
from .pet_brain import TASK_WORDS
from .common import *  # noqa: F401,F403
from .apps import *  # noqa: F401,F403
from .winapi import *  # noqa: F401,F403
from .monitor import *  # noqa: F401,F403
from .brain import *  # noqa: F401,F403
from .voice import *  # noqa: F401,F403
from .sprites import *  # noqa: F401,F403

from . import common  # noqa: E402


class PetTalk:
    # --- разговор ---
    def open_input(s):
        if s.busy:
            return s.say("Погоди, я занят…", 2)
        if s.inp:
            return
        s.bubble.hide()
        s.state, s.timer = "idle", 10**6
        w = s.inp = floating(s.root)
        f = tk.Frame(w, bg=PAPER, highlightthickness=2, highlightbackground=DARK, padx=8, pady=6)
        f.pack()
        tk.Label(f, text="Скажи или попроси (Win+H — голосом):", bg=PAPER, fg=DARK,
                 font=("Segoe UI", 9)).pack(anchor="w")
        e = tk.Entry(f, width=38, font=("Segoe UI", 10), relief="flat", bg="white")
        e.pack(pady=(3, 0))
        e.bind("<Return>", lambda ev: s.send(e.get()))
        e.bind("<Escape>", lambda ev: s.close_input())
        w.update_idletasks()
        bw, bh = w.winfo_reqwidth(), w.winfo_reqheight()
        x = int(max(s.L, min(s.x + W / 2 - bw / 2, s.R - bw)))
        w.geometry(f"+{x}+{int(max(0, s.y + 30 - bh))}")
        w.focus_force()
        e.focus_set()

    def close_input(s):
        if s.inp:
            s.inp.destroy()
            s.inp = None
        if not s.thinking and s.state == "idle":
            s.timer = 1.6

    def local_command(s, text, dry=False):
        """Разбирает команды сам, без ИИ. None — это не команда, а болтовня. dry=True — только проверить, не делать."""
        raw = text.strip()
        text = num_words(re.sub(r"[.!?]|пожалуйста|клодик,?", " ", text.lower()))
        text = re.sub(r"\b(запомни|забудь|напомни|запиши),\s*", r"\1 ", text)   # «запомни, что…» — одна команда
        # фразы целиком (до разбивки по «и»/запятым): «Стоп», второе подтверждение, ответ на «точно?», …
        if re.match(r"^\s*(?:стоп|стой|остановись|хватит всё|отмена всего|прекрати)\s*$", text) and not (s.game and not dry):
            return True if dry else (s.stop_all() or True)
        if not dry and getattr(s, "second", None) and s.check_second(text):
            return True
        if not dry and not s.confirm and re.match(r"^\s*(?:нет|не надо|отстань|не предлагай)", text) and s.reject_hint():
            return True                                         # «нет» на подсказку — больше её не предлагаю
        if not dry and (fn := s.brain_command(text.strip(), raw)) and re.match(r"^\s*(?:напиши|сделай|создай)\s+плагин", text):
            return fn() or True                                 # «напиши плагин …» — фраза целиком
        if not dry and s.confirm and s.answer_confirm(text.strip()):
            return True
        if not dry and s.game and s.game_input(text):          # ответ в мини-игре
            return True
        if re.search(r"сыгра|играем|давай\s+(?:в|игра)|угадай|викторин|печень", text) and (fn := s.fun_command(text)):
            return True if dry else (fn() or True)              # «сыграем в камень, ножницы, бумага» — целиком
        if m := re.match(r"^\s*(?:запомни|создай|сохрани|сделай)\s+режим\s+(\w+)\s*(?:[:—-]|это)?\s*(.+)$", text):
            return True if dry else (s.save_mode(m[1], m[2]) or True)
        if m := re.match(r"^\s*(?:напечатай|введи текст|напиши текст)\s*:?\s*(.+)$", raw, re.I):
            return True if dry else (s.type_text(m[1]) or True)
        segs =[x for x in re.split(r"\s*,\s*|\s+(?:и|а потом|потом|затем)\s+", text) if x.strip()]
        acts, local, missed = [], [], []
        s.snap = {i + 1: w for i, w in enumerate(s.windows())}
        for seg in segs:
            seg = re.sub(r"^(?:а |ну |слушай |давай |можешь |сделай |мне )+", "", seg.strip())
            m_num = re.search(r"на (\d+)", seg)
            step = max(1, min(10, int(m_num.group(1)) // 2)) if m_num else 5
            if fn := s.safety_command(seg):                      # «Стоп», «верни как было», журнал, уровень доступа
                local.append(fn)
            elif re.search(r"что (?:ты )?(?:можешь|умеешь) (?:запустить|открыть)|какие (?:у меня )?(?:программы|игры)", seg):
                local.append(s.what_can_run)
            elif re.search(r"забудь (?:всё|все)? ?выученн", seg):
                local.append(s.forget)
            elif re.search(r"подстройся|подстрой(?:ка)? под (?:мой )?голос|настрой уши|калибр", seg):
                local.append(s.calibrate)
            elif re.search(r"(?:говори|разговаривай)\s+(?:по)?тише|тише говори|(?:сделай\s+)?голос\s+(?:по)?тише", seg):
                local.append(lambda: s.set_volume(s.voice_vol - 15))
            elif re.search(r"(?:говори|разговаривай)\s+(?:по)?громче|громче говори|(?:сделай\s+)?голос\s+(?:по)?громче", seg):
                local.append(lambda: s.set_volume(s.voice_vol + 15))
            elif re.search(r"^(?:молчи|замолчи|не говори вслух|хватит говорить)", seg):
                local.append(lambda: s.set_tts(False))
            elif m := re.search(r"(?:смени|поменяй|другой)\s+голос(?:\s+на)?\s*(\w*)|голосом\s+(\w+)", seg):
                want = (m[1] or m[2] or "").lower()
                v = next((k for k, name in VOICES.items() if want and name.lower().startswith(want[:4])), None)
                if not v:                                     # «смени голос» без имени — следующий по кругу
                    keys = list(VOICES)
                    v = keys[(keys.index(s.voice) + 1) % len(keys)]
                local.append(lambda v=v: s.set_voice(v))
            elif re.search(r"говори вслух|озвучивай|разговаривай голосом", seg):
                local.append(lambda: s.set_tts(True))
            elif re.search(r"не слушай|перестань слушать|(?:выключи|отключи)\s+(?:микрофон|уши)", seg):
                local.append(lambda: s.set_listen(False))
            elif re.search(r"слушай меня|(?:включи|вруби)\s+(?:микрофон|уши)", seg):
                local.append(lambda: s.set_listen(True))
            elif fn := s.play_command(seg):                     # игровые таймеры и заметки, мини-игры, звуки, ИИ по буферу
                local.append(fn)
            elif fn := s.desk_command(seg):                     # помодоро, буфер, стикеры, окна, порты, файлы, проекты, свет
                local.append(fn)
            elif fn := s.soul_command(seg):                     # душа, сны, «ты живой?», настроение
                local.append(fn)
            elif fn := s.scene_command(seg):                    # «переоденься» — уйти в дверь и выйти в новой шапке
                local.append(fn)
            elif fn := s.fun_command(seg):                      # мини-игры, характер, танцы, «сколько играл»
                local.append(fn)
            elif fn := s.pc_command(seg):                       # режимы, буфер, файлы и папки, система
                local.append(fn)
            elif fn := s.brain_command(seg, raw):               # поправки, правила, недельный отчёт, плагины, «только локально»
                local.append(fn)
            elif fn := s.onboard_command(seg):                  # «называй меня…», «что ещё можно подключить», импорт памяти
                local.append(fn)
            elif fn := s.smart_command(seg):                    # память о тебе, итоги дня, сводка
                local.append(fn)
            elif fn := s.task_command(seg):                     # напоминания, список дел, калькулятор, переводчик
                local.append(fn)
            elif re.search(r"(?:закрой|убери|снеси|сверни|разгреби|почисти)\s+(?:все|всё)\b|^разгре|^разгром|бульдоз", seg):
                local.append(lambda m="close" if re.search(r"закрой|снеси", seg) else "minimize": s.start_dozer(m))
            elif re.search(r"(?:покажи|открой)\s+(?:фотк|скрин|снимк)", seg):
                local.append(s.open_photos)
            elif re.search(r"сфоткай|сфотографируй|скрин|снимок экрана|^фото", seg):
                local.append(s.photo)
            elif re.search(r"(?:прогони|отпусти|пока)\s+друг", seg):
                local.append(s.dismiss_buddy)
            elif re.search(r"\bдруг", seg):
                local.append(s.call_buddy)
            elif re.search(r"слезь|спрыгни", seg):
                local.append(s.drop)
            elif re.search(r"залезь|запрыгни|прыгай по окнам|прыгни на окно", seg):
                local.append(lambda: s.try_climb() or s.say("Некуда залезть — нет подходящих окон", 3))
            elif m := re.search(r"(?:надень|одень|наряди\w*)\s+(.+)", seg):
                words = m[1].split()                              # «шлем космонавта» — ищем любое слово-примету
                hat = next((v for k, v in sorted(HAT_WORDS.items(), key=lambda kv: -len(kv[0]))
                            if any(w.startswith(k) for w in words) or k in m[1]), None)
                hat = hat or next((f"skin:{n}" for n in skins() if n.lower() in m[1]), None)
                local.append((lambda h=hat: s.set_hat(h)) if hat else (lambda w=m[1]: s.say(f"У меня нет «{w}»", 2)))
            elif re.search(r"^сними|разденься", seg):
                local.append(lambda: s.set_hat("none"))
            elif re.search(r"(?:выключи|убери|останови)\s+снег", seg):
                local.append(lambda: s.set_snow("off"))
            elif re.search(r"^(?:включи |пусти |вруби )?снег$|снег вкл", seg):
                local.append(lambda: s.set_snow("on"))
            elif re.search(r"(?:выключи|отключи|убери|верни|включи)\s+звук|без звука|^мут", seg):
                acts.append({"do": "mute"})
            elif re.search(r"громче", seg):
                acts.append({"do": "volume", "step": step})
            elif re.search(r"тише", seg):
                acts.append({"do": "volume", "step": -step})
            elif re.search(r"следующ|некст|переключи трек", seg):
                acts.append({"do": "media", "key": "next"})
            elif re.search(r"предыдущ", seg):
                acts.append({"do": "media", "key": "prev"})
            elif re.search(r"пауз|^стоп\s+музык|продолж|включи музык|играй музык", seg):   # «стоп» один — это «Стоп всего»
                acts.append({"do": "media", "key": "play"})
            elif m := re.match(r"^(?:найди|загугли|погугли|поищи)\s+(?:в (?:гугле|интернете)\s+)?(.+)", seg):
                acts.append({"do": "url", "url": "https://www.google.com/search?q=" + urllib.parse.quote(m[1])})
            elif re.search(r"как (?:там )?комп|загрузк|температур", seg):
                local.append(lambda: s.say(s.stats.summary(), 8))
            elif re.search(r"покорм|поешь|покушай", seg):
                local.append(s.feed)
            elif re.search(r"мяч", seg):
                local.append(s.toggle_ball)
            elif re.search(r"^(?:иди )?спать|^поспи", seg):
                local.append(s.sleep)
            elif re.search(r"ко мне|иди сюда", seg):
                local.append(s.come)
            elif m := re.match(rf"^(?:{OPEN_V})\s+(?:папку|программу|приложение|сайт|игру)?\s*(.+)", seg):
                acts.append({"do": "open", "app": m[1].strip()})
            elif any(re.match(rf"^(?:{v})\s+", seg) for v in WIN_V.values()):
                do = next(k for k, v in WIN_V.items() if re.match(rf"^(?:{v})\s+", seg))
                q = re.sub(rf"^(?:{WIN_V[do]})\s+(?:окно\b\s*)?", "", seg).strip()
                win = s.find_window(q) if q else None
                if win:
                    acts.append({"do": do, "win": win})
                else:
                    missed.append(f"окно «{q}»" if q else "какое окно?")
            else:
                missed.append(f"«{seg}»")
        if not acts and not local and not any(x.startswith(("окно", "какое")) for x in missed):
            return None                                   # не команда — болтовня для ИИ
        if dry:
            return bool(acts or local) and not missed
        for fn in local:
            fn()
        if acts:
            s.say(s.ack(), 1.5)                           # «Сейчас!» в духе выбранного характера
            s.plan(acts)                                  # сам скажет, если программу не нашёл
        if missed:
            s.say("Не нашёл: " + ", ".join(missed), 4)
        return True

    def find_window(s, q):
        q = ALIAS.get(q, q)
        best, score = None, 0.0
        for i, w in s.snap.items():
            sc = max(match(q, os.path.splitext(w["proc"])[0]), 0.9 if q in w["title"].lower() else 0.0,
                     match(q, w["title"]) if len(w["title"]) < 20 else 0.0)
            if sc > score:
                best, score = i, sc
        return best if score >= 0.75 else None

    def send(s, text, voice=False, allow_chat=True):
        text = text.strip()
        s.close_input()
        if not text:
            return
        s.talk_until = s.clock + 12                           # что отвечу на эту просьбу — скажу вслух
        s.request = (text, "голос" if voice else "текст")     # для журнала: кто и зачем попросил
        s.last_touch = s.clock                                # для «скучает»: когда последний раз общались
        if s.understand(text):
            lf = s.last_fail                                  # переспросил по-другому и сработало — запомню
            if lf and s.clock - lf[1] < 40 and difflib.SequenceMatcher(None, lf[0], text.lower()).ratio() >= 0.5:
                s.learn(lf[0], text)
            s.last_fail = None
            s.day_note("cmd", text.lower())
            return
        if voice:
            s.last_fail = (text.lower(), s.clock)
            s.day_note("fail", text.lower())                  # ночью разберу, что это было
        if not allow_chat:                                    # 20 с после команды — только команды, не болтовня
            s.emote("doubt", "light")
            return s.say(f"«{text}» — не понял", 2)
        if TASK_WORDS.match(text.strip()) and s.brain != "none":   # задача на компе — план инструментами, а не болтовня
            return s.plan_task(text)
        s.day_note("chat", "")
        if s.on_user_text(text) == "support":                 # плохой день: тепло и просто, ничего не запоминаю
            return s.ask_ai(text + "\n(Владельцу сейчас плохо. Поддержи тепло, коротко и просто, без лекций, "
                                   "мягко предложи поговорить с близкими или специалистом, без советов «возьми себя в руки» и без вопросов о причинах.)", remember=False)
        s.learn_facts(text)                                   # тихо запомню, если ты рассказал что-то о себе
        s.ask_ai(text)

    def ask_ai(s, text, remember=True):
        """Вопрос мозгам (в фоне); ответ придёт событием «ok» и будет сказан вслух."""
        s.last_text = text if remember else ""
        s.thinking, s.state, s.timer = True, "idle", 10**6
        hist = "\n".join(s.history[-4:]) if remember else ""
        prompt = (f"[{time.strftime('%H:%M')}, комп: {s.stats.summary()}]\n"
                  + (f"Что ты знаешь о хозяине: {s.memory_text()}\n" if remember and s.memory else "")
                  + (f"{hist}\n" if hist else "") + f"Пользователь: {text}")
        if remember:
            s.history.append(f"Пользователь: {text}")

        def work():
            try:
                s.answers.put(("ok", s.claude(prompt)))
            except Exception as ex:  # любой сбой CLI — показать, а не уронить Клодика
                s.answers.put(("err", str(ex)))
        threading.Thread(target=work, daemon=True).start()

    # --- будильник (сами напоминания — в pet_tasks) ---
    def ring(s, note):
        s.drop()
        s.job, s.jobs = None, []
        s.state, s.alarm_until = "alarm", s.clock + 10
        s.carry = ("clock", s.alarm_until)
        s.beeps = [s.clock, s.clock + 1.3, s.clock + 2.6]
        s.say("⏰ Время!" + (f"\n{note}" if note else ""), 12)
        s.emote("surprise", "strong")
        if s.tts_on:
            s.speaker.say("Время! " + note if note else "Время! Таймер сработал.")

    def stop_alarm(s):
        s.state, s.timer, s.carry, s.beeps = "idle", 2, None, []
        s.say("Окей, понял!", 1.5)

    # --- фото ---
    def photo(s):
        if s.busy:
            return s.say("Погоди, я занят…", 2)
        s.drop()
        s.state, s.photo_t = "photo", 0.0
        s.carry = ("camera", s.clock + 4)
        s.say("Улыбочку!", 1.2)

    def open_photos(s):
        d = pictures_dir()
        os.makedirs(d, exist_ok=True)
        s.fx.start(d)

    def flash(s):
        w = floating(s.root)
        w.configure(bg="white")
        w.geometry(f"{s.R - s.L}x{s.B - s.T}+{s.L}+{s.T}")
        w.attributes("-alpha", 0.85)

        def fade(a):
            if a <= 0:
                return w.destroy()
            w.attributes("-alpha", a)
            w.after(25, fade, a - 0.12)
        fade(0.85)

    # --- друг ---
    def call_buddy(s):
        if s.buddy:
            return s.say("Он уже тут!", 2)
        s.buddy = Buddy(s)
        s.say("Друг, иди сюда!", 2)

    def dismiss_buddy(s):
        if s.buddy:
            s.buddy.leave()
            s.say("Пока, дружище!", 2)
