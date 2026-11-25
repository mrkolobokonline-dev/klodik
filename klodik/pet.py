"""Сам Клодик: создание, мышь, игровой цикл, рисунок."""
from .common import *  # noqa: F401,F403
from .apps import *  # noqa: F401,F403
from .winapi import *  # noqa: F401,F403
from .monitor import *  # noqa: F401,F403
from .brain import *  # noqa: F401,F403
from .voice import *  # noqa: F401,F403
from .sprites import *  # noqa: F401,F403

from . import common  # noqa: E402
from .pet_mind import PetMind
from .pet_world import PetWorld
from .pet_talk import PetTalk
from .pet_actions import PetActions
from .pet_tasks import PetTasks
from .pet_smart import PetSmart
from .pet_pc import PetPC
from .pet_fun import PetFun
from .pet_safety import PetSafety
from .pet_onboard import PetOnboard
from .pet_prefs import PetPrefs
from .looks import paint2, particles
from .pet_scenes import PetScenes
from .pet_brain import PetBrain
from .anim import EMO, Emotions, micro
from .ai import AI, parse_json


# ---------- сам Клодик ----------
class Pet(PetSafety, PetOnboard, PetPrefs, PetBrain, PetScenes, PetFun, PetPC, PetSmart, PetTasks, PetMind,
          PetWorld, PetTalk, PetActions):
    def __init__(s, root, claude=None, fx=None, windows=list_windows, plats=platforms, frame=frame_rect):
        s.root, s.claude, s.fx, s.windows = root, claude or s.think, fx or Effects(), windows
        s.platforms_fn, s.frame_fn = plats, frame
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.attributes("-transparentcolor", KEY)
        root.config(bg=KEY)
        s.c = tk.Canvas(root, width=W, height=H, bg=KEY, highlightthickness=0)
        s.c.pack()
        s.L, s.T, s.R, s.B = work_area()
        s.start_x = start_button_x(s.L, s.R)
        s.x, s.y, s.vy = float(random.randint(s.L, s.R - W)), float(s.B - H), 0.0
        s.dir, s.state, s.timer, s.target = 1, "walk", 6.0, None
        s.press, s.dragging, s.pos, s.key = None, False, None, None
        s.bubble, s.inp, s.thinking, s.history = Bubble(root), None, False, []
        s.answers = queue.Queue()
        s.food = s.ball = s.buddy = s.dozer = s.dz = s.snow = None
        s.hearts, s.pet_acc, s.pet_t, s._hx = 0.0, 0.0, 0.0, None
        s.stats, s.hot_n, s.warned = Stats(), 0, {}
        s.hunger, s.mood, s.hat, s.snow_mode, s.brain = 30.0, 70.0, "auto", "auto", "ollama"
        s.pulling, s.listen_on, s.listener, s.gaming = False, False, None, False
        s.jobs, s.job, s.job_phase, s.job_t, s.job_fired, s.carry = [], None, "", 0.0, False, None
        s.surface, s.surf, s.plats, s.edge_go, s.climb = None, None, [], False, None
        s.alarm_until, s.beeps, s.photo_t = 0.0, [], None
        s.look, s.yawn_until = None, 0.0
        s.emo, s.pose, s.hook_id, s.vx = Emotions(), None, None, 0.0
        s.emo_names = set(EMO["emotions"])
        s.ai = AI(local_only=lambda: s.prefs.get("local_only", False))
        s.speaker, s.tts_on, s.talk_until, s.calib, s.voice = Speaker(), True, 0.0, None, "dmitri"
        s.voice_vol = 40
        load_profile()
        s.snap, s.icons = {}, {}
        s.lmod, s.apps = load_launcher()
        s.start_apps, s.games = cached_apps()              # то, что нашёл в прошлый раз, — сразу
        s.learned, s.last_fail, s.last_text, s._vocab = load_learned(), None, "", None
        if claude is None:
            threading.Thread(target=s.rescan, daemon=True).start()
        s.access_level, s.pin, s.profile, s.prefs, s.ignore_ai_until = None, "", {}, {}, 0.0
        s.load()
        s.safety_load()
        s.tasks_load()
        s.smart_load()
        s.pc_load()
        s.fun_load()
        s.persona_var = tk.StringVar(value=s.persona)
        s.level_var = tk.StringVar(value=s.access_level)
        s.scenes_load()
        s.brain_load()
        s.onboard_load()                                   # первый запуск — знакомство
        s.hat_var, s.snow_var = tk.StringVar(value=s.hat), tk.StringVar(value=s.snow_mode)
        s.brain_var = tk.StringVar(value=s.brain)
        s.listen_var, s.tts_var = tk.BooleanVar(value=s.listen_on), tk.BooleanVar(value=s.tts_on)
        s.voice_var, s.vol_var = tk.StringVar(value=s.voice), tk.IntVar(value=s.voice_vol)
        s.speaker.voice, s.speaker.volume = s.voice, s.voice_vol
        if s.listen_on and claude is None:
            s.listener = Listener(s.answers, muted=s.speaker.speaking)
        if claude is None and s.brain == "ollama":
            threading.Thread(target=s.warm_ollama, daemon=True).start()   # у друзей: докачать модель заранее
        s.t_last = time.perf_counter()
        s.clock = 0.0
        s.next = {"poll": 0.0, "slow": 0.0, "minute": 60.0, "top": 5.0, "plats": 0.0, "look": 0.0, "full": 0.0,
                  "remind": 0.0, "smart": 10.0}
        s.menu = tk.Menu(root, tearoff=0)
        s.c.bind("<ButtonPress-1>", s.on_press)
        s.c.bind("<B1-Motion>", s.on_motion)
        s.c.bind("<ButtonRelease-1>", s.on_release)
        s.c.bind("<Motion>", s.on_hover)
        s.c.bind("<Button-3>", s.popup)
        s.update_snow()
        s.tick()

    # --- мышь ---
    def on_press(s, e):
        s.press, s.dragging = (e.x_root, e.y_root, s.x, s.y), False

    def on_motion(s, e):
        if not s.press or s.state in ("dozer", "dozer_out"):
            return
        dx, dy = e.x_root - s.press[0], e.y_root - s.press[1]
        if abs(dx) + abs(dy) > 4 and not s.dragging:
            s.dragging, s.state = True, "drag"
            s.drop()
            if s.inp:
                s.close_input()
        if s.dragging:
            s.x, s.y = s.press[2] + dx, s.press[3] + dy
            s.place()                                  # сразу, со скоростью мыши — без рывков

    def on_release(s, e):
        if s.dragging:
            s.vy = 0.0
            s.state, s.timer = ("job", 0) if s.job else ("idle", 1.0)
            s.say("Уиии!", 1.5)
        elif s.state == "alarm":
            s.stop_alarm()
        elif s.state == "sleep":
            s.state, s.timer = "idle", 2.4
            s.say("А? Я не сплю!", 2)
        elif not s.poke():                                # 5 кликов подряд — злится вместо разговора
            s.open_input()
        s.press, s.dragging = None, False

    def on_hover(s, e):
        """Погладить = поводить мышкой туда-сюда по Клодику."""
        now = time.time()
        if now - s.pet_t > 0.6:
            s.pet_acc, s._hx = 0.0, None
        if s._hx is not None:
            s.pet_acc += abs(e.x - s._hx)
        s._hx, s.pet_t = e.x, now
        if s.pet_acc > 500 and not s.hearts:
            s.pet_acc, s.hearts = 0.0, 1.6
            s.mood_add(6)
            if s.state == "sleep":
                s.state, s.timer = "idle", 2.4
            s.say(random.choice(["Мурр ♥", "Ещё-ещё!", "Приятно ♥", "Хи-хи, щекотно"]), 2)

    # --- цикл ---
    def place(s):
        pos = (int(s.x), int(s.y))
        if pos != s.pos:
            s.pos = pos
            s.root.geometry(f"{W}x{H}+{pos[0]}+{pos[1]}")

    def tick(s):
        now = time.perf_counter()
        dt, s.t_last = min(0.05, now - s.t_last), now
        try:
            s.update(dt)
        except Exception:  # одна ошибка не должна останавливать Клодика — пишем в журнал и живём дальше
            s.errors = getattr(s, "errors", 0) + 1
            if s.errors <= 20:
                log_error(traceback.format_exc())
        finally:
            s.root.after(250 if s.gaming else TICK_MS, s.tick)  # в игре — 4 раза в секунду, не 144

    def every(s, name, period):
        if s.clock >= s.next.get(name, 0.0):              # новый таймер заводится сам
            s.next[name] = s.clock + period
            return True
        return False

    def set_gaming(s, on):
        """Полноэкранная игра: прячемся и почти не тратим процессор; уши, таймеры и команды работают."""
        s.gaming = on
        corner = s.prefs.get("game_mode") == "corner"      # или тихо сидит в углу, а не прячется совсем
        wins = ([] if corner else [s.root]) + [x.w for x in (s.buddy, s.food, s.ball) if x]
        for w in wins:
            w.withdraw() if on else w.deiconify()
        if on and corner:
            s.drop()
            s.x, s.y, s.state = float(s.L), float(s.B - H), "sleep"
            s.place()
            s.key = None
            s.draw()
        if on:
            s.bubble.hide()
        else:
            s.root.attributes("-topmost", True)
            s.pos = s.key = None
        if s.snow:
            s.snow.set_hidden(on)

    def update(s, dt):
        s.clock += dt
        t = s.clock
        if s.every("full", 1):
            fs = s.fullscreen_app()
            if fs != s.gaming:
                s.set_gaming(fs)
        s.hearts = max(0.0, s.hearts - dt)
        if not s.gaming:
            for p in (s.food, s.ball):
                if p:
                    p.step(dt)
            if s.buddy:
                s.buddy.update(dt, t)
            s.frame_n = getattr(s, "frame_n", 0) + 1
            if s.snow and s.frame_n % 2:                 # снег — 72 кадра/с, хватает
                s.snow.step(dt * 2)
        if s.every("top", 5) and not s.gaming:
            s.root.attributes("-topmost", True)        # другие окна «поверх» могут перекрыть
        if s.every("poll", 2):
            s.stats.poll()
            s.check_pc()
        if s.every("slow", 10):
            threading.Thread(target=s.stats.poll_slow, daemon=True).start()
        if s.every("minute", 60):
            s.hunger = min(100.0, s.hunger + 0.35)
            s.mood_add(-0.1 - (0.3 if s.hunger > 70 else 0))
            s.save()
            s.update_snow()
            s.key = None                                 # шапка могла смениться (ночь/зима)
            if s.hunger > 70 and random.random() < 0.3:
                s.say("Есть хочу… (ПКМ → Покормить)")
        if s.every("plats", 0.4) and not s.gaming:
            s.plats = s.platforms_fn()
        if s.every("look", 0.1) and not s.gaming:
            px, py = s.root.winfo_pointerxy()
            dx, dy = px - (s.x + W / 2), py - (s.y + H - 25)
            s.look = (((0 if abs(dx) < 25 else (1 if dx > 0 else -1)), dy < -60)
                      if abs(dx) < 700 and abs(dy) < 500 and s.on("eyes") else None)
        if s.every("remind", 0.5):
            s.check_reminders()
        if s.every("smart", 10):
            s.smart_tick()
            s.game_watch()
            s.ambient_emotions()
            s.daily_scene()
        if s.every("wake", 0.25):
            s.sleep_wake()
        s.door_tick(dt)
        s.mood_tick(dt)
        s.catch_tick(dt)
        while s.beeps and s.beeps[0] <= t:
            s.beeps.pop(0)
            s.fx.beep()
        try:
            kind, text = s.answers.get_nowait()
            if kind == "photo":
                s.flash()
                s.say(f"Щёлк! Сохранил в «Изображения\\Клодик»\n(скажи «покажи фотки»)", 4)
                s.state, s.timer, s.carry = "idle", 2, None
            elif kind == "photo_err":
                s.say(f"Не получилось сфоткать: {text}", 4)
                s.state, s.timer, s.carry = "idle", 2, None
            elif kind == "info":
                s.say(text, 6)
            elif kind in ("wake", "heard", "voice", "voice_follow", "voice_timeout", "follow_end"):
                s.on_voice(kind, text)
            elif kind in ("calib", "calib_partial"):
                s.on_calib(kind, text)
            elif kind == "quiz":
                s.quiz_got(text)
            elif kind == "plan":
                s.plan_ready(text)
            elif kind == "plan_step":
                s.say(text, 6, speak=text.startswith(("✗", "Готово")))
                s.emote("pride" if text == "Готово!" else "doubt" if text.startswith("✗") else "interest", "light")
            elif kind == "run_cmd":
                s.local_command(text)
            elif kind == "plugin_draft":
                s.plugin_draft(text)
            elif kind == "fact":
                s.remember(text, quiet=True)
            elif kind in ("clip_copy", "clip_say"):
                s.clip_result(kind, text)
            elif kind == "files":
                s.files_result(text)
            elif not s.thinking and s.clock < s.ignore_ai_until:
                pass                                          # ответ ИИ пришёл после «Стоп» — выбрасываем
            else:
                s.thinking = False
                d = parse_json(text) if kind == "ok" else {}  # {"text", "emotion", "intensity", "action"}
                if kind == "ok" and d.get("action") and isinstance(d["action"], str):
                    text = "CMD: " + d["action"]              # модель угадала команду — как раньше
                elif kind == "ok" and d.get("text"):
                    text = str(d["text"])
                cmd = re.match(r"\s*CMD:\s*(.+)", text) if kind == "ok" else None
                if cmd:                                       # ИИ понял, какую команду я не расслышал
                    c = cmd[1].strip().strip("«»\"'")
                    s.say(f"Понял как «{c}»", 2)
                    s.state, s.timer = "idle", 1.0            # до команды: она сама переключит в «job»
                    if s.local_command(c):
                        s.learn(s.last_text, c)               # в следующий раз — сам, без токенов
                    else:
                        s.say(f"Не вышло: «{c}»", 3)
                elif kind == "ok":
                    say = text.replace("**", "")
                    s.history.append(f"Клодик: {say}")
                    s.mood_add(2)
                    s.say(("☁ " if s.ai.where == "cloud" else "") + say, speak=True)   # значок «облако»
                    emo = d.get("emotion") if d.get("emotion") in s.emo_names else "joy"
                    s.emote(emo, d.get("intensity") if d.get("intensity") in ("light", "medium", "strong") else "light")
                    s.state, s.timer = "idle", 1.0
                    s.vy = -230.0                         # подпрыгнуть от радости
                else:
                    s.say(f"Не получилось спросить: {text}", 6)
                    s.state, s.timer = "idle", 1.6
        except queue.Empty:
            pass
        if s.thinking:
            s.say("Думаю" + "." * (1 + int(t * 3) % 3), 1)
        if is_night() and s.state == "idle" and random.random() < dt / 480:
            s.yawn_until = t + 1.6
            s.say("Ааауу… Может, пора спать?", 2.5)
        if s.gaming:
            return
        if s.dozer:
            s.dozer_update(dt)
        else:
            s.pose = s.emo.frame(s.clock)
            s.ride()
            s.move(dt)
        s.place()
        s.bubble.follow(s.x + W / 2, s.y + 32, s.L, s.R)
        s.draw()

    def fullscreen_app(s):
        h = u32.GetForegroundWindow()
        if not h:
            return False
        pid = wt.DWORD()
        u32.GetWindowThreadProcessId(h, ctypes.byref(pid))
        cls = ctypes.create_unicode_buffer(64)
        u32.GetClassNameW(h, cls, 64)
        if pid.value == os.getpid() or cls.value in ("Progman", "WorkerW", "Shell_TrayWnd"):  # рабочий стол — не игра
            return False
        r = wt.RECT()
        u32.GetWindowRect(h, ctypes.byref(r))
        return r.left <= 0 and r.top <= 0 and r.right >= u32.GetSystemMetrics(0) and r.bottom >= u32.GetSystemMetrics(1)

    def check_pc(s):
        msg = s.stats.hot()
        s.hot_n = s.hot_n + 1 if msg else 0
        now = time.time()
        if s.hot_n == 5 and now - s.warned.get("hot", 0) > 300:   # ~10 с подряд
            s.warned["hot"] = now
            s.say(msg, 5)
        if s.stats.disk_free is not None and s.stats.disk_free < 15 and now - s.warned.get("disk", 0) > 3600:
            s.warned["disk"] = now
            s.say(f"На диске C осталось {s.stats.disk_free:.0f} ГБ!", 6)

    def at_edge(s, d):
        """Упёрся в край экрана в сторону d — дальше не дотянуться, значит «дошёл»."""
        return (d < 0 and s.x <= s.L + 1) or (d > 0 and s.x >= s.R - W - 1)

    def move(s, dt):
        st = s.state
        if st == "drag":
            return
        cx = s.x + W / 2
        if s.y < s.ground - 0.5 or s.vy < 0:              # в воздухе
            prev = s.y
            s.vy += G * dt
            s.y += s.vy * dt
            if s.vx:                                       # отпрыгивает в сторону
                s.x = max(s.L, min(s.R - W, s.x + s.vx * dt))
            if s.job and s.job_phase == "act" and s.job["anim"] == "jump" and not s.job_fired and s.vy >= 0:
                s.fire_job()                              # на вершине прыжка «бьёт» по окну
            if s.vy > 0:
                land = None if s.surface or st not in LANDABLE else s.find_landing(prev, s.y, cx)
                if land:
                    s.surface, s.surf, s.edge_go = land[0], land[1], False
                    s.y, s.vy = float(land[1][1] - H), 0.0
                    if st == "climb":
                        s.state, s.timer = "idle", random.uniform(3, 8)
                    if random.random() < 0.5:
                        s.say(random.choice(["Я наверху!", "Хоп!", "Отсюда всё видно", "Опа!"]), 1.5)
                elif s.y >= s.ground - 0.5:               # тот же допуск, что и в проверке «в воздухе»
                    if s.vy > 650:                        # падал с высоты больше ~300 px — «Ого!»
                        s.landed_hard(s.vy * s.vy / (2 * G))
                    s.y, s.vy, s.vx = s.ground, 0.0, 0.0
            return
        pose = s.pose
        if pose and st in ("idle", "walk") and not s.surface:  # движения из клипа эмоции
            if id(s.emo.clip) != s.hook_id:                # один раз на клип
                s.hook_id = id(s.emo.clip)
                px = s.root.winfo_pointerx()
                if pose.get("jump_away"):
                    s.dir = -1 if px > cx else 1
                    s.vy, s.vx = -260.0, s.dir * 180.0
                elif pose.get("walk_to_cursor"):
                    s.target = max(s.L, min(px - W // 2 - 80 * (1 if px > cx else -1), s.R - W))
                    s.state, s.timer, s.dir = "walk", 6, (1 if s.target > s.x else -1)
                elif pose.get("hide_edge"):
                    s.target = s.L if cx < (s.L + s.R) / 2 else s.R - W
                    s.state, s.timer, s.dir = "walk", 8, (1 if s.target > s.x else -1)
            if pose.get("hop") and s.vy == 0:
                s.vy = -170.0
        if st == "job":
            s.job_step(dt, cx)
        elif st == "fetch":
            if not s.food:
                s.state, s.timer = "idle", 1
            else:
                fx = s.food.x + Prop.SIZE / 2
                if abs(fx - cx) > 18 and not s.at_edge(1 if fx > cx else -1):
                    s.dir = 1 if fx > cx else -1
                    s.x += s.dir * RUN * dt
                elif s.food.on_ground():
                    s.food.destroy()
                    s.food = None
                    s.hunger = max(0.0, s.hunger - 35)
                    s.mood_add(8)
                    s.state, s.timer = "eat", 2.0
                    s.say("Ням-ням!", 2)
                    s.emote("joy", "medium")
                    s.save()
        elif st == "chase":
            if not s.ball:
                s.state = "idle"
            else:
                bx = s.ball.x + Prop.SIZE / 2
                if abs(bx - cx) > 26 and not s.at_edge(1 if bx > cx else -1):
                    s.dir = 1 if bx > cx else -1
                    s.x += s.dir * CHASE * dt
                elif s.ball.on_ground() and not s.ball.hold:
                    s.ball.vx = s.dir * random.uniform(175, 350)
                    s.ball.vy = -random.uniform(200, 375)
                    s.mood_add(3)
                    if random.random() < 0.3:
                        s.say(random.choice(["Гол!", "Лови!", "Хоп!"]), 1.5)
        elif st == "climb":
            if abs(s.x - s.target) > 3:
                s.dir = 1 if s.target > s.x else -1
                s.x += s.dir * min(RUN * 0.7 * dt, abs(s.target - s.x))
            else:                                         # прыжок ровно до верха окна (+ запас)
                height = s.y - (s.climb[1] - H) + 25
                s.vy = -math.sqrt(2 * G * max(height, 30))
                s.state, s.timer = "idle", 3                 # idle тоже может приземлиться на окно
                s.say("Хоп!", 1)
        elif st == "alarm":
            if s.clock > s.alarm_until:
                return s.stop_alarm()
            px = s.root.winfo_pointerx() - W / 2
            if abs(px - s.x) > 20:
                s.dir = 1 if px > s.x else -1
                s.x += s.dir * min(RUN * 1.3 * dt, abs(px - s.x))
            else:
                s.vy = -320.0                             # прыгает и звенит у курсора
        elif st == "photo":
            s.photo_t += dt
            if s.photo_t >= 0.8 and s.photo_t - dt < 0.8:
                s.bubble.hide()

                def shoot():
                    try:
                        s.answers.put(("photo", s.fx.screenshot()))
                    except Exception as ex:
                        s.answers.put(("photo_err", str(ex)))
                threading.Thread(target=shoot, daemon=True).start()
        elif st == "dozer_out":
            s.dir = -1
            s.x -= RUN * 1.3 * dt
            if s.x <= s.L - W:
                s.dozer, s.state = Dozer(s), "dozer"
            return
        elif st == "walk":
            s.x += s.dir * WALK * dt * (0.5 if pose and pose.get("slow_walk") else 1)
            if s.target is not None and abs(s.x - s.target) < 3:
                s.state, s.timer, s.target = "idle", 3.2, None
                s.say("Я тут!", 1.5)
            if s.surface and s.surf:                      # край окна: развернуться или спрыгнуть
                l, r = s.surf[0], s.surf[2]
                ncx = s.x + W / 2
                if ((ncx < l + 12 and s.dir < 0) or (ncx > r - 12 and s.dir > 0)) and not s.edge_go:
                    if random.random() < 0.75:
                        s.dir = -s.dir
                    else:
                        s.edge_go = True
                        s.say("Прыг!", 1)
        if st == "door":                                  # уход в дверь — за край экрана можно
            return
        if s.x <= s.L or s.x >= s.R - W:
            s.x, s.dir = max(s.L, min(s.x, s.R - W)), -s.dir
        if st in ("job", "alarm", "photo") or s.inp or s.thinking:
            return
        s.timer -= dt
        if s.timer <= 0:
            if st == "sleep":
                s.say("Выспался!", 2)
            s.pick_next()
        if st in ("walk", "idle") and random.random() < dt / 160 and s.on("walk_talk") and not s.quiet_now():
            s.say(s.walk_phrase())                      # свежие фразы от ИИ (обновляются каждую ночь)

    # --- рисунок: пиксельный квадратик как логотип ---
    def draw(s):
        t, st = s.clock, s.state
        if st == "dozer":
            if s.key != "hidden":
                s.key = "hidden"
                s.c.delete("all")
            return
        air = s.y < s.ground - 1
        going = (st in ("walk", "fetch", "chase", "climb", "alarm", "dozer_out") or (st == "job" and s.job_phase == "go")
                 or (st == "door" and s.door_plan and s.door_plan["phase"] in ("go", "enter", "exit")))
        acting = st == "job" and s.job_phase == "act" and s.job and s.job["anim"] != "jump" and not s.job_fired
        dancing = st == "dance" or (acting and s.job["anim"] == "dance")
        beat = s.meter.peak > 0.25 if st == "dance" and s.meter.ok else int(t * 4) % 2 == 0
        legs = (int(t * (12 if st != "walk" else 8)) % 2 if going and not air else
                (int(t * 4) % 2 if st == "dance" else -1))
        squash = 1 if st == "sleep" or (acting and int(t * 10) % 2) or (st == "dance" and beat) else 0
        sway = (1 if int(t * (3 if st == "dance" else 6)) % 2 else -1) if dancing else 0
        blink = (t % 4.4) < 0.15
        look = s.look if st in ("idle", "eat") and not going else None
        if s.angry_until > t:
            eyes = "angry"
        elif s.wow_until > t:
            eyes = "wide"
        elif st == "sleep" or blink or s.hearts or s.yawn_until > t or st == "dance":
            eyes = "closed"
        elif s.thinking or (look and look[1]) or st == "alarm":
            eyes = "up"
        elif s.sad:
            eyes = "down"
        else:
            eyes = "open"
        sh = s.dir if (going or st == "job") else (look[0] if look else 0)
        mouth = "yawn" if s.yawn_until > t else (int(t * 7) % 2 if st == "eat" else -1)
        sweat = int(t * 8) % 4 if s.hot_n >= 5 else -1
        zz = int(t / 0.6) % 3 if st == "sleep" else -1
        heart = int(s.hearts * 10) if s.hearts else -1
        carry = s.carry if s.carry and s.carry[1] > t else None
        ring = int(t * 10) % 2 if st == "alarm" else -1
        hat = s.hat_now()
        sp = {"color": "#e0553f" if eyes == "angry" else ORANGE, "legs": legs, "squash": squash, "eyes": eyes, "sh": sh,
              "mouth": mouth, "hat": hat}
        anim = s.prefs.get("anim", "max")
        pose = s.pose if s.pose and st not in ("sleep", "job", "dozer_out", "drag") else None
        if not pose and st in ("idle", "walk") and not air and not blink:
            sp.update({k: v for k, v in micro(t, anim).items() if not (k == "legs" and st == "walk")})
        part = None
        if pose:                                           # клип эмоции поверх базовой позы
            part = pose.get("particles")
            sway = pose.get("sway", sway) + pose.get("jitter", 0)
            sp.update({k: v for k, v in pose.items() if k in ("color", "legs", "squash", "eyes", "sh", "mouth", "arms",
                                                              "brow", "blush", "stretch", "puff", "hat_dx", "hat_dy")})
            if pose.get("eyes") == "happy" and blink:
                sp["eyes"] = "closed"
        if s.hot_n >= 5 and anim != "min":                 # жарко — обмахивается веером
            sp["arms"] = "head" if int(t * 6) % 2 else "normal"
        part_key = (part[0], round(part[1], 1), part[2]) if part else None
        key = (tuple(sorted(sp.items())), sway, sweat, zz, heart, carry and id(carry[0]), air, ring, part_key)
        if key == s.key:
            return
        s.key = key
        c = s.c
        c.delete("all")
        oy = H - 10 * C + sp["squash"] * C
        ox = OX + sway * C
        paint2(c, ox, oy, sp)
        if part_key:
            particles(c, ox, oy, part[0], part[1], part[2])

        def px(col, row, w, h, fill):
            c.create_rectangle(ox + col * C, oy + row * C, ox + (col + w) * C, oy + (row + h) * C, fill=fill, outline="")
        if sweat >= 0:
            px(1, 0 + sweat, 1, 1, "#7cc4ff")
            px(14, (sweat + 2) % 4, 1, 1, "#7cc4ff")
            if anim != "min":                              # веер
                px(15, -2 + (int(t * 6) % 2), 3, 2, "#f2c230")
        if zz >= 0:
            c.create_text(OX + 15 * C, oy - 6 - zz * 7, text="z" * (zz + 1), fill=DARK, font=("Consolas", 11, "bold"))
        if heart >= 0:
            rise = (16 - heart) * 1.5
            for hx in (OX + 3 * C, OX + 13 * C):
                c.create_text(hx, oy - 4 - rise, text="♥", fill="#e0445a", font=("Segoe UI", 12, "bold"))
        if carry:                                         # держит над головой
            thing, top = carry[0], -6 if hat in ("none", "glasses") else -8
            if isinstance(thing, tk.PhotoImage):
                c.create_image(W / 2, oy + (top + 1) * C, image=thing)
            elif thing in ("coffee", "tea"):              # кружка; у чая — пиала потемнее
                px(10, 1, 3, 3, "#f4f4f4" if thing == "coffee" else "#c9a27a"); px(13, 2, 1, 1, "#f4f4f4")
                px(10, 1, 3, 1, "#6f4e37" if thing == "coffee" else "#7a8f3a")
                if int(t * 3) % 2:
                    px(11, -1, 1, 1, "#d0d0d0")          # пар
            elif thing == "brush":                         # зубная щётка у рта + пена
                px(9, 4 + int(t * 6) % 2, 5, 1, "#4c8fd9"); px(8, 4, 1, 1, "#ffffff"); px(7, 5, 1, 1, "#ffffff")
            elif thing == "mic":
                px(7, top, 2, 3, "#555"); px(6, top + 2, 4, 1, "#555"); px(7, top + 3, 2, 1, "#555"); px(7, top, 1, 1, "#999")
            elif thing == "camera":
                px(5, top, 6, 4, "#333"); px(7, top + 1, 2, 2, "#8fd0ff"); px(9, top - 1, 2, 1, "#333")
            elif thing == "clock":
                dy = -ring
                px(5, top + dy, 6, 5, "#e0445a"); px(6, top + 1 + dy, 4, 3, "white"); px(7, top + 2 + dy, 2, 1, EYE)
                px(5, top - 1 + dy, 2, 1, "#e0445a"); px(9, top - 1 + dy, 2, 1, "#e0445a")
            else:
                px(6, top, 4, 4, "#e0b04a"); px(7, top + 1, 2, 2, "#fff3c4")
