"""Меню и прогулки по окнам."""
from .common import *  # noqa: F401,F403
from .apps import *  # noqa: F401,F403
from .winapi import *  # noqa: F401,F403
from .monitor import *  # noqa: F401,F403
from .brain import *  # noqa: F401,F403
from .voice import *  # noqa: F401,F403
from .sprites import *  # noqa: F401,F403
from .tasks import fmt_when
from .pet_tasks import write_json
from .policy import LEVELS, POLICY_FILE

from . import common  # noqa: E402


class PetWorld:
    # --- меню ---
    def popup(s, e):
        m = s.menu
        m.delete(0, "end")
        m.add_command(label=f"Сытость {100 - s.hunger:.0f}% · Настроение {s.mood:.0f}%", state="disabled")
        if s.reminders:
            r = s.reminders[0]
            m.add_command(label=f"⏰ {fmt_when(r['t'], s.now())}" + (f" — {r['text']}" if r["text"] else "")
                          + (f" (и ещё {len(s.reminders) - 1})" if len(s.reminders) > 1 else ""), command=s.timer_left)
            m.add_command(label="Отменить все напоминания", command=s.cancel_timers)
        m.add_command(label="⛔ Стоп — прервать всё", command=s.stop_all)
        if s.undo_stack:
            m.add_command(label=f"↩ Верни как было: {s.undo_stack[-1][0][:30]}", command=s.undo)
        m.add_separator()
        m.add_command(label="Поговорить / попросить", command=s.open_input)
        m.add_command(label="Настройки и все команды…", command=s.open_settings)
        safety = tk.Menu(m, tearoff=0)
        for k, v in LEVELS.items():
            safety.add_radiobutton(label=v, value=k, variable=s.level_var, command=lambda k=k: s.set_level(k))
        safety.add_separator()
        safety.add_command(label="Журнал действий…", command=s.journal_window)
        safety.add_command(label="Открыть файл политики", command=lambda: s.fx.start(POLICY_FILE))
        m.add_cascade(label="Доступ и безопасность", menu=safety)
        m.add_cascade(label="Функции (вкл/выкл)", menu=s.feature_menu(m))
        pl = tk.Menu(m, tearoff=0)
        for man in s.plugins:
            v = tk.BooleanVar(value=man.get("enabled", True))

            def flip(man=man, v=v):
                man["enabled"] = v.get()
                write_json(os.path.join(man["dir"], "plugin.json"), {k: x for k, x in man.items() if k != "dir"})
            pl.add_checkbutton(label=f"{man['name']} — {man.get('description', '')[:40]}", variable=v, command=flip)
        if s.plugins:
            pl.add_separator()
        pl.add_command(label="Как написать: скажи «напиши плагин, который …»", state="disabled")
        pl.add_command(label="Правила из поправок…", command=lambda: s.say(
            "Правила:\n" + "\n".join(r["text"] for r in s.rules) if s.rules else "Правил пока нет.", 8))
        pl.add_command(label="Недельный отчёт", command=s.weekly_report)
        m.add_cascade(label="Мозг: плагины и правила", menu=pl)
        me = tk.Menu(m, tearoff=0)
        me.add_command(label="Знакомство и подключения…", command=s.onboarding)
        me.add_command(label="Что ты обо мне знаешь…", command=s.recall_window)
        me.add_command(label="Импорт памяти…", command=s.memory_import_window)
        me.add_command(label="Экспорт памяти", command=s.memory_export)
        me.add_command(label="Душа Клодика (характер, дневник, сны)…", command=s.soul_window)
        me.add_command(label="Сохранить копию всех данных", command=s.export_data)
        m.add_cascade(label=f"Обо мне{', ' + s.addr() if s.addr() else ''}", menu=me)
        m.add_command(label=f"Список дел ({len(s.notes)})", command=s.notes_window)
        m.add_command(label="История буфера…", command=s.clips_window)
        m.add_command(label="Что я умею (каталог команд)…", command=s.catalog)
        m.add_command(label="Помодоро: стоп" if s.pomo else "Помодоро 25/5", command=lambda: s.pomodoro(stop=bool(s.pomo)))
        m.add_command(label="Покормить", command=s.feed)
        m.add_command(label="Убрать мячик" if s.ball else "Мячик", command=s.toggle_ball)
        m.add_command(label="Прогнать друга" if s.buddy else "Позвать друга",
                      command=s.dismiss_buddy if s.buddy else s.call_buddy)
        m.add_command(label="Спрыгнуть с окна" if s.surface else "Залезть на окно",
                      command=s.drop if s.surface else lambda: s.try_climb() or s.say("Некуда залезть", 2))
        m.add_command(label="Бульдозер: свернуть всё", command=lambda: s.start_dozer("minimize"))
        m.add_command(label="Сфоткать экран", command=s.photo)
        m.add_command(label="Открыть фотки", command=s.open_photos)
        m.add_command(label="Как там комп?", command=lambda: s.say(s.stats.summary(), 8))
        wear = tk.Menu(m, tearoff=0)
        for k, v in HATS.items():
            wear.add_radiobutton(label=v, value=k, variable=s.hat_var, command=lambda k=k: s.set_hat(k))
        m.add_cascade(label="Гардероб", menu=wear)
        snow = tk.Menu(m, tearoff=0)
        for k, v in (("auto", "Только зимой"), ("on", "Включить"), ("off", "Выключить")):
            snow.add_radiobutton(label=v, value=k, variable=s.snow_var, command=lambda k=k: s.set_snow(k))
        m.add_cascade(label="Снег", menu=snow)
        brain = tk.Menu(m, tearoff=0)
        for k, v in BRAINS.items():
            brain.add_radiobutton(label=v, value=k, variable=s.brain_var, command=lambda k=k: s.set_brain(k))
        m.add_cascade(label="Мозг для болтовни", menu=brain)
        m.add_checkbutton(label="Слушать «Клодик» (микрофон, офлайн)", variable=s.listen_var,
                          command=lambda: s.set_listen(s.listen_var.get()))
        m.add_checkbutton(label="Говорить вслух", variable=s.tts_var, command=lambda: s.set_tts(s.tts_var.get()))
        voice = tk.Menu(m, tearoff=0)
        for k, v in VOICES.items():
            voice.add_radiobutton(label=v, value=k, variable=s.voice_var, command=lambda k=k: s.set_voice(k))
        voice.add_separator()
        for v in (20, 30, 40, 60, 80, 100):
            voice.add_radiobutton(label=f"Громкость {v}%", value=v, variable=s.vol_var, command=lambda v=v: s.set_volume(v))
        m.add_cascade(label="Голос Клодика", menu=voice)
        m.add_command(label="Подстроить уши под мой голос", command=s.calibrate)
        m.add_command(label="Что ты умеешь запускать?", command=s.what_can_run)
        if s.learned:
            m.add_command(label=f"Забыть выученное ({len(s.learned)})", command=s.forget)
        m.add_separator()
        m.add_command(label="Уснуть", command=s.sleep)
        m.add_command(label="Ко мне", command=s.come)
        m.add_command(label="Выход", command=s.quit)
        m.tk_popup(e.x_root, e.y_root)

    def drop(s):
        if s.surface:
            s.surface = s.surf = None

    def feed(s):
        if s.food:
            return s.say("Там уже лежит печенька!")
        cx = s.x + W / 2 + random.choice((-1, 1)) * random.randint(80, 220)
        s.food = Prop(s, "food", max(s.L, min(cx, s.R - Prop.SIZE)), s.T + 40)
        if not s.busy:
            s.drop()
            s.state, s.timer = "fetch", 60
        s.say("Ого, печенька!", 2)

    def toggle_ball(s):
        if s.ball:
            s.ball.destroy()
            s.ball = None
            return s.say("Ну ладно…", 2)
        px, py = s.root.winfo_pointerx(), s.root.winfo_pointery()
        s.ball = Prop(s, "ball", px - 13, min(py, s.B - 60))
        if not s.busy:
            s.drop()
            s.state, s.timer = "chase", 15
        s.say("Мячик! Кидай его мышкой", 3)

    def sleep(s):
        s.state, s.timer = "sleep", 36

    def come(s):
        s.drop()
        s.target = max(s.L, min(s.root.winfo_pointerx() - W // 2, s.R - W))
        s.state, s.timer = "walk", 80
        s.dir = 1 if s.target > s.x else -1

    def pick_next(s):
        s.target = None
        r = random.random()
        if is_night() and random.random() < 0.3:
            return s.sleep()
        if s.surface:
            if r < 0.45:
                s.state, s.timer = "idle", random.uniform(2, 7)
            elif r < 0.85:
                s.state, s.timer, s.dir = "walk", random.uniform(2, 6), random.choice((-1, 1))
            else:
                s.drop()
                s.vy, s.state, s.timer = -200.0, "idle", 2
                s.say("Вниз!", 1)
            return
        if s.ball and r < 0.7:
            s.state, s.timer = "chase", random.uniform(6, 16)
        elif r < 0.14 and s.on("climb") and s.try_climb():
            pass
        elif r < 0.45:
            s.state, s.timer = "idle", random.uniform(1.6, 6.4)
        elif r < 0.84:
            s.state, s.timer, s.dir = "walk", random.uniform(2.4, 10), random.choice((-1, 1))
        elif r < 0.92:
            s.come()
        else:
            s.sleep()

    # --- окна как платформы ---
    def occluded(s, i, x, y):
        return any(l <= x <= r and t <= y <= b for (_, l, t, r, b, _) in s.plats[:i])

    def find_landing(s, prev, new, cx):
        for i, (h, l, t, r, b, ok) in enumerate(s.plats):
            fy = t - H
            if ok and l + 5 <= cx <= r - 5 and prev <= fy <= new and fy >= s.T and not s.occluded(i, cx, t):
                return h, (l, t, r, b)
        return None

    def try_climb(s):
        if s.busy:
            return False
        cands = []
        for i, (h, l, t, r, b, ok) in enumerate(s.plats):
            if ok and r - l >= W + 30 and t - H >= s.T + 5 and t < s.B - H - 40:
                x = random.uniform(max(l + 5, s.L), min(r - W - 5, s.R - W))
                if x >= l and not s.occluded(i, x + W / 2, t):
                    cands.append((h, x, t))
        if not cands:
            return False
        h, x, t = random.choice(cands)
        s.drop()
        s.state, s.target, s.climb, s.timer = "climb", x, (h, t), 30
        s.dir = 1 if x > s.x else -1
        return True

    def ride(s):
        """Стоит на окне: едет вместе с ним; окно исчезло или ушёл с края — падает."""
        if not s.surface or s.state == "drag":
            return
        fr = s.frame_fn(s.surface)
        if fr and s.surf:
            s.x += fr[0] - s.surf[0]
        if fr and fr[0] - 3 <= s.x + W / 2 <= fr[2] + 3:
            s.surf = fr
            if s.vy == 0:
                s.y = float(fr[1] - H)
            return
        if not fr:
            s.say(random.choice(["Ааа!", "Эй, куда окно?!", "Падаю!"]), 1.5)
        s.surface = s.surf = None
