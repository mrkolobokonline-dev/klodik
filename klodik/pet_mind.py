"""Память, мозги, обучение, голосовые события, настройки."""
from .common import *  # noqa: F401,F403
from .apps import *  # noqa: F401,F403
from .winapi import *  # noqa: F401,F403
from .monitor import *  # noqa: F401,F403
from .brain import *  # noqa: F401,F403
from .voice import *  # noqa: F401,F403
from .sprites import *  # noqa: F401,F403

from . import common  # noqa: E402


class PetMind:
    # --- память ---
    def load(s):
        old = os.path.join(HERE, "state.json")             # раньше лежал рядом со скриптом
        if not os.path.exists(common.STATE) and os.path.exists(old):
            os.makedirs(DATA_DIR, exist_ok=True)
            shutil.copy2(old, common.STATE)
        try:
            with open(common.STATE, encoding="utf-8") as f:
                d = json.load(f)
            mins = max(0.0, (time.time() - d.get("t", time.time())) / 60)
            s.hunger = min(100.0, d.get("hunger", 30) + mins * 0.35)
            s.mood = max(0.0, d.get("mood", 70) - mins * 0.1)
            s.hat = d.get("hat", "auto") if d.get("hat") in HATS else "auto"
            s.snow_mode = d.get("snow", "auto") if d.get("snow") in ("auto", "on", "off") else "auto"
            s.brain = d["brain"] if d.get("brain") in BRAINS else "ollama"   # старое «auto» → Ollama
            s.listen_on = bool(d.get("listen", False))
            s.tts_on = bool(d.get("tts", True))
            s.voice = d["voice"] if d.get("voice") in VOICES else "dmitri"
            s.voice_vol = int(d.get("vol", 40))
            s.persona = d.get("persona", "kind")
            s.access_level = d.get("level")
            s.pin = d.get("pin", "")
            s.profile = d.get("profile", {})                   # имя, пол, язык, формы имени — из знакомства
            s.prefs = d.get("prefs", {})                       # переключатели функций, тихие часы, анимации
        except (OSError, ValueError):
            pass

    def save(s):
        os.makedirs(os.path.dirname(common.STATE), exist_ok=True)
        tmp = common.STATE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"hunger": round(s.hunger, 1), "mood": round(s.mood, 1), "hat": s.hat, "snow": s.snow_mode,
                       "brain": s.brain, "listen": s.listen_on, "tts": s.tts_on, "voice": s.voice, "vol": s.voice_vol,
                       "persona": getattr(s, "persona", "kind"), "level": getattr(s, "access_level", None),
                       "pin": getattr(s, "pin", ""), "profile": getattr(s, "profile", {}),
                       "prefs": getattr(s, "prefs", {}), "t": time.time()}, f)
        os.replace(tmp, common.STATE)

    # --- мозги: Ollama на компе (по умолчанию, бесплатно) → готовые фразы. Claude — только если выбрать руками. ---
    def think(s, prompt):
        b = s.brain
        if b == "claude":
            return ask_claude(prompt) if claude_exe() else "Claude на этом компе нет — выбери другой мозг (ПКМ → Мозг)."
        if b == "ollama":
            models = ollama_models()
            if models is None:
                if ollama_exe():
                    os.startfile(ollama_exe())
                    return "Бужу свои мозги… Спроси ещё раз секунд через 20."
                return "Мозги (Ollama) не установлены. Скачай с ollama.com — и я начну болтать."
            model = pick_model(models)
            if model:
                return ask_ollama(prompt, model, s.persona_prompt())   # с выбранным характером
            threading.Thread(target=s.pull_model, daemon=True).start()
            return "Качаю себе мозги (несколько ГБ, один раз). Минут через 5–15 смогу болтать!"
        return random.choice(CANNED)

    def pull_model(s):
        if s.pulling:
            return
        s.pulling = True
        try:
            ollama_call("/api/pull", {"model": want_model(), "stream": False}, 3600)
            s.answers.put(("info", "Мозги скачались! Теперь со мной можно болтать — кликни по мне."))
        except (OSError, ValueError) as e:
            s.answers.put(("info", f"Не смог скачать мозги: {e}"))
        finally:
            s.pulling = False

    def warm_ollama(s):
        for _ in range(40):                                # до ~10 минут ждём, пока Ollama поставится и запустится
            models = ollama_models()
            if models is not None:
                if not pick_model(models):
                    s.answers.put(("info", "Качаю себе мозги для болтовни (несколько ГБ, один раз)…"))
                    s.pull_model()
                return
            time.sleep(15)

    # --- что есть на компе и чему научился ---
    def rescan(s):
        first = not s.start_apps
        apps, games = scan_apps()
        s.start_apps, s.games, s._vocab = apps, games, None
        if first and apps:
            s.answers.put(("info", f"Я осмотрелся: знаю {len(apps)} программ, из них {len(games)} игр. "
                                   "Спроси «что можешь запустить»."))

    def what_can_run(s):
        g = ", ".join(s.games[:12]) + ("…" if len(s.games) > 12 else "")
        s.say(f"Знаю {len(s.start_apps)} программ." + (f"\nИгры: {g}" if g else "") +
              "\nСкажи «открой …» — и название.", 10)

    def vocab(s):
        """Слова, которые Клодик понимает: команды, псевдонимы, названия программ, выученное."""
        if s._vocab is None:
            words = set(CMD_WORDS) | set(ALIAS) | set(DIRECT)
            for name in [n for n, _ in s.start_apps] + [a["name"] for a in s.apps] + list(s.learned.values()):
                words |= {w for w in re.split(r"[\s\-:.,()]+", name.lower()) if len(w) >= 3}
            s._vocab = words
        return s._vocab

    def fix_words(s, text):
        """Похожие слова → известные: «разгромив» → «разгреби», «стимм» → «стим»."""
        out, vocab = [], s.vocab()
        for w in text.lower().split():
            if len(w) >= 4 and w not in vocab:
                m = difflib.get_close_matches(w, vocab, n=1, cutoff=0.7)
                w = m[0] if m else w
            out.append(w)
        return " ".join(out)

    def learn(s, heard, cmd):
        heard = heard.lower().strip()
        if heard and heard != cmd.lower().strip():
            s.learned[heard] = cmd
            s._vocab = None
            save_learned(s.learned)

    def understand(s, text):
        """Пробует выполнить как команду: выученное → как есть → с исправленными словами. True — сделал."""
        t = text.lower().strip()
        key = t if t in s.learned else next(iter(difflib.get_close_matches(t, list(s.learned), n=1, cutoff=0.85)), None)
        hit = s.learned.get(key) if key else None
        if hit and s.local_command(hit):
            return True
        if s.local_command(text):
            return True
        fixed = s.fix_words(t)
        if fixed != t and s.local_command(fixed):
            s.learn(t, fixed)
            return True
        return False

    def forget(s):
        s.learned = {}
        s._vocab = None
        save_learned(s.learned)
        s.say("Забыл всё выученное", 2)

    def set_listen(s, on):
        s.listen_on = on
        s.listen_var.set(on)
        s.save()
        if on and not s.listener:
            s.listener = Listener(s.answers, muted=s.speaker.speaking)
            s.say("Включаю уши…", 2)
        elif not on and s.listener:
            s.listener.stop()
            s.listener = None
            s.say("Больше не подслушиваю", 2)

    def set_tts(s, on):
        s.tts_on = on
        s.tts_var.set(on)
        s.save()
        if not on:
            s.speaker.hush()
        s.say("Буду говорить вслух!" if on else "Молчу, только пишу.", 2, speak=on)

    def set_volume(s, vol):
        s.push_undo("громкость голоса", lambda p=s.voice_vol: s.set_volume(p))
        s.voice_vol = s.speaker.volume = max(10, min(100, int(vol)))
        s.vol_var.set(s.voice_vol)
        s.save()
        s.say(f"Громкость голоса: {s.voice_vol}%", 2, speak=True)

    def set_voice(s, v):
        s.push_undo("голос", lambda p=s.voice: s.set_voice(p))
        s.voice = v
        s.voice_var.set(v)
        s.speaker.set_voice(v)
        s.save()
        if not s.tts_on:
            s.set_tts(True)
        s.say(f"Теперь я говорю голосом: {VOICES[v]}. Как тебе?", 3, speak=True)

    # --- подстройка под голос: читаешь фразы — запоминаю, как именно слышу тебя ---
    CALIB = [("Клодик", None)] * 5 + [("Клодик, открой Steam", "открой steam"), ("Клодик, сделай громче", "сделай громче"),
                                      ("Клодик, засеки пять минут", "засеки 5 минут"),
                                      ("Клодик, разгреби все окна", "разгреби все окна"),
                                      ("Клодик, позови друга", "позови друга"), ("Клодик, сфоткай", "сфоткай")]

    def calibrate(s):
        if s.calib:
            return
        if not s.listener:
            s.set_listen(True)
        w = floating(s.root)
        w.configure(bg=PAPER, padx=22, pady=16, highlightthickness=2, highlightbackground=DARK)
        tk.Label(w, text="Подстройка под твой голос", bg=PAPER, fg=INK, font=("Segoe UI", 13, "bold")).pack()
        tk.Label(w, text="Скажи вслух обычным голосом:", bg=PAPER, fg=DARK, font=("Segoe UI", 10)).pack(pady=(8, 0))
        phrase = tk.Label(w, text="", bg=PAPER, fg=ORANGE, font=("Segoe UI", 18, "bold"))
        phrase.pack(pady=4)
        heard = tk.Label(w, text="", bg=PAPER, fg=INK, font=("Segoe UI", 10), wraplength=360)
        heard.pack()
        step = tk.Label(w, text="", bg=PAPER, fg=DARK, font=("Segoe UI", 9))
        step.pack(pady=(6, 0))
        bar = tk.Frame(w, bg=PAPER)
        bar.pack(pady=(10, 0))
        tk.Button(bar, text="Пропустить", command=lambda: s.calib_next(), relief="flat", padx=10).pack(side="left", padx=4)
        tk.Button(bar, text="Хватит", command=lambda: s.calib_done(), relief="flat", padx=10).pack(side="left", padx=4)
        w.update_idletasks()
        w.geometry(f"+{(s.L + s.R - w.winfo_reqwidth()) // 2}+{(s.T + s.B) // 3}")
        s.calib = {"win": w, "phrase": phrase, "heard": heard, "step": step, "i": -1, "wake": 0, "cmd": 0}
        s.speaker.hush()
        s.calib_next()

    def calib_next(s):
        c = s.calib
        c["i"] += 1
        if c["i"] >= len(s.CALIB):
            return s.calib_done()
        c["phrase"].config(text=f"«{s.CALIB[c['i']][0]}»")
        c["heard"].config(text="(слушаю…)")
        c["step"].config(text=f"{c['i'] + 1} из {len(s.CALIB)}")
        if s.listener:
            s.listener.calib = True

    def on_calib(s, kind, text):
        c = s.calib
        if not c:
            return
        if kind == "calib_partial":
            return c["heard"].config(text=f"слышу: {text}…")
        c["heard"].config(text=f"услышал: «{text}»")
        words, want = text.split(), s.CALIB[c["i"]][1]
        name_n = 2 if len(words) > 1 and len(words[1]) <= 3 else 1   # «клади к» — два слова
        name = tr("".join(words[:name_n]))
        if len(name) >= 3 and (want is None or words[0] not in CMD_WORDS):
            if name not in WAKE_EXTRA:
                WAKE_EXTRA.add(name)
                c["wake"] += 1
        if want:
            rest = " ".join(words[name_n:])
            if rest and rest != want and not s.local_parse_same(rest, want):
                s.learn(rest, want)
                c["cmd"] += 1
        s.listener.calib = False
        s.root.after(900, s.calib_next)                     # пауза — показать, что услышал

    def local_parse_same(s, heard, want):
        """Услышанное и так понимается как нужная команда — учить не надо."""
        return s.fix_words(num_words(heard)) == s.fix_words(num_words(want))

    def calib_done(s):
        c, s.calib = s.calib, None
        if s.listener:
            s.listener.calib = False
        if c:
            c["win"].destroy()
            save_profile()
            s.say(f"Готово! Запомнил {c['wake']} вариантов, как слышу «Клодик», и {c['cmd']} команд.", 6, speak=True)

    def on_voice(s, kind, text=""):
        if kind == "wake":
            s.speaker.hush()                                   # позвали — замолкаю и слушаю
            if s.state == "sleep":
                s.state, s.timer = "idle", 3
            s.carry = ("mic", s.clock + 8)
            s.say("Слушаю!", 8)
            winsound.MessageBeep(winsound.MB_OK)
        elif kind == "heard":
            s.carry = ("mic", s.clock + 4)
            s.say(f"«{text}…»", 4)
        elif kind == "voice_timeout":
            s.carry = None
            s.say("Не расслышал…", 1.5)
        elif kind == "follow_end":
            s.carry = None
        elif kind in ("voice", "voice_follow"):
            s.carry = ("mic", s.clock + VoiceLogic.FOLLOW)   # микрофон над головой = можно говорить без «Клодик»
            if s.thinking:
                return s.say("Погоди, ещё думаю…", 2)
            s.say(f"«{text}»", 2)
            s.talk_until = s.clock + 12                        # ответ на голос — тоже голосом
            s.send(text, voice=True, allow_chat=kind == "voice")

    def set_brain(s, b):
        s.push_undo("мозг", lambda p=s.brain: s.set_brain(p))
        s.brain = b
        s.brain_var.set(b)
        s.save()
        s.say(f"Мозг: {BRAINS[b]}", 2)
        if b == "ollama":
            threading.Thread(target=s.warm_ollama, daemon=True).start()

    def quit(s):
        if s.listener:
            s.listener.stop()
        s.speaker.hush()
        s.save()
        s.root.destroy()

    def say(s, text, secs=None, image=None, speak=None):
        """Облачко; вслух — если speak=True или это ответ в течение 12 с после твоей просьбы (speak=None)."""
        if not text:
            return
        s.bubble.show(text, secs or max(3, min(25, len(text) / 12)), image)
        if speak is None:
            speak = s.clock < s.talk_until and len(text) >= 4 and not text.startswith(("«", "Думаю", "Слушаю"))
        # в тихие часы вслух — только ответы на твою просьбу (будильники говорят сами в ring)
        if speak and s.tts_on and (s.clock < s.talk_until or not s.quiet_now()):
            s.speaker.say(text)

    def mood_add(s, v):
        s.mood = max(0.0, min(100.0, s.mood + v))

    @property
    def sad(s):
        return s.mood < 35 or s.hunger > 70

    @property
    def ground(s):
        return float(s.surf[1] - H) if s.surface and s.surf else float(s.B - H)

    @property
    def busy(s):
        return bool(s.thinking or s.job or s.jobs or s.dz or s.state in ("photo", "alarm", "dozer", "dozer_out", "door"))

    def hat_now(s):
        if s.hat != "auto":
            return s.hat
        if is_night():
            return "nightcap"
        if 21 <= time.localtime().tm_hour < 23:
            return "pajama"                                # вечером — в пижамном колпаке
        m, d = time.localtime().tm_mon, time.localtime().tm_mday
        if (m == 12 and d >= 20) or (m == 1 and d <= 7):
            return "santa"                                 # праздники
        if m == 10 and d >= 25 or (m == 11 and d == 1):
            return "pumpkin"                               # Хэллоуин
        return "winter" if m in (12, 1, 2) else "none"

    def set_hat(s, hat):
        s.push_undo("шапка", lambda p=s.hat: s.set_hat(p))
        s.hat = hat
        s.hat_var.set(hat)
        s.key = None
        s.save()
        label = HATS.get(hat) or hat.replace("skin:", "скин ")
        s.say({"none": "Снял!", "auto": "Буду одеваться по погоде"}.get(hat, f"{label} — как я тебе?"), 2)
        if hat not in ("none", "auto"):
            s.emote("pride", "light")

    def set_snow(s, mode):
        s.push_undo("снег", lambda p=s.snow_mode: s.set_snow(p))
        s.snow_mode = mode
        s.snow_var.set(mode)
        s.save()
        s.update_snow()
        s.say({"on": "Пусть идёт снег!", "off": "Снег выключил", "auto": "Снег — только зимой"}[mode], 2)

    def update_snow(s):
        want = s.snow_mode == "on" or (s.snow_mode == "auto" and time.localtime().tm_mon in (12, 1, 2))
        if want and not s.snow:
            s.snow = Snow(s)
        elif not want and s.snow:
            s.snow.destroy()
            s.snow = None
