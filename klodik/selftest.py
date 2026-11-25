"""Самопроверка: python pet.pyw --selftest"""
from .common import *  # noqa: F401,F403
from .apps import *  # noqa: F401,F403
from .winapi import *  # noqa: F401,F403
from .monitor import *  # noqa: F401,F403
from .brain import *  # noqa: F401,F403
from .voice import *  # noqa: F401,F403
from .sprites import *  # noqa: F401,F403
from .install import *  # noqa: F401,F403

from . import apps, common, pet_fun, pet_smart, pet_tasks, voice
from .pet import Pet
from .tasks import calc, parse_when


def selftest():
    common.STATE = os.path.join(HERE, "state.selftest.json")
    if os.path.exists(common.STATE):                             # хвосты прошлого упавшего прогона
        os.remove(common.STATE)
    voice.ERRLOG = os.path.join(os.environ.get("TEMP", HERE), "klodik_selftest_errors.log")
    voice.PROFILE = os.path.join(os.environ.get("TEMP", HERE), "klodik_selftest_profile.json")
    voice.WAKE_EXTRA.clear()
    apps.LEARNED = os.path.join(HERE, "learned.selftest.json")
    apps.APPS_CACHE = os.path.join(HERE, "apps.selftest.json")
    pet_tasks.REMINDERS = os.path.join(HERE, "reminders.selftest.json")
    pet_tasks.NOTES = os.path.join(HERE, "notes.selftest.json")
    from . import pet_onboard, pet_prefs, pet_safety, policy, update as upd
    policy.POLICY_FILE = os.path.join(HERE, "policy.selftest.json")
    policy.JOURNAL = os.path.join(HERE, "journal.selftest.jsonl")
    tmp_dir = os.path.join(os.environ.get("TEMP", HERE), "klodik_selftest_data")
    shutil.rmtree(tmp_dir, ignore_errors=True)
    os.makedirs(tmp_dir)
    pet_onboard.ONBOARD = os.path.join(tmp_dir, "onboarding.json")
    pet_onboard.ENV = os.path.join(tmp_dir, ".env")
    pet_onboard.SEED = os.path.join(tmp_dir, "memory_seed.md")
    open(pet_onboard.SEED, "w", encoding="utf-8").write(
        "# Стартовая память\n- Зовут Тест Тестович, любит чай.\n- Пароль от почты 12345\n- Родители живут далеко. [личное]\n"
        "- Берёт кредит на машину.\n")
    pet_prefs.BACKUP_DIR = os.path.join(tmp_dir, "backup")
    from . import ai as ai_mod, pet_brain
    for mod, names in ((pet_brain, ("RULES", "KB")), (ai_mod, ("CACHE", "USAGE"))):
        for n in names:
            setattr(mod, n, os.path.join(tmp_dir, n.lower() + ".json"))
    from . import pet_soul
    from .pet_soul import idle_seconds
    pet_soul.SOUL = os.path.join(tmp_dir, "soul.json")
    from . import pet_desk, pet_play
    for n in ("COSTUMES", "GNOTES"):
        setattr(pet_play, n, os.path.join(tmp_dir, n.lower() + ".json"))
    pet_play.GUIDES, pet_play.NOISE = os.path.join(tmp_dir, "guides"), os.path.join(tmp_dir, "sounds")
    for n in ("CLIPS", "STICKERS", "TRACK", "PROJECTS", "IDEAS", "GUARD"):
        setattr(pet_desk, n, os.path.join(tmp_dir, n.lower() + ".json"))
    pet_brain.WEEKLY = os.path.join(tmp_dir, "weekly")
    pet_brain.PLUGINS = os.path.join(tmp_dir, "plugins")
    upd.OK_FLAG = os.path.join(tmp_dir, "update_ok.flag")
    for f in (policy.POLICY_FILE, policy.JOURNAL):
        if os.path.exists(f):
            os.remove(f)
    for name in ("MEMORY", "DAY", "DIARY", "FRESH"):
        setattr(pet_smart, name, os.path.join(HERE, f"{name.lower()}.selftest.json"))
        if os.path.exists(getattr(pet_smart, name)):
            os.remove(getattr(pet_smart, name))
    t0 = time.time()
    pet_tasks.write_json(pet_tasks.REMINDERS, [{"t": t0 - 3600, "text": "пропущенное"}, {"t": t0 + 99999, "text": "потом"}])
    for f in (apps.LEARNED, apps.APPS_CACHE, pet_tasks.NOTES):
        if os.path.exists(f):
            os.remove(f)

    class Rec:
        calls = []
        def close(s, h): s.calls.append(("close", h))
        def minimize(s, h): s.calls.append(("min", h))
        def maximize(s, h): s.calls.append(("max", h))
        def focus(s, h): s.calls.append(("focus", h))
        def move(s, h, x, y): s.calls.append(("move", h))
        def start(s, t): s.calls.append(("start", t))
        def keys(s, vk, n=1): s.calls.append(("keys", vk, n))
        def beep(s): s.calls.append(("beep",))
        def screenshot(s): s.calls.append(("shot",)); return "C:\\test.png"
        def lock(s): s.calls.append(("lock",))
        def sleep_pc(s): s.calls.append(("sleep",))
        def abort_shutdown(s): s.calls.append(("abort",))
        def shutdown(s, secs, restart=False): s.calls.append(("shutdown", secs, restart))
        def paste(s): s.calls.append(("paste",))
        def restore(s, h): s.calls.append(("restore", h))

    asked = []
    win = lambda h, title, proc, rect, mn=False, mx=False: {"hwnd": h, "title": title, "proc": proc, "rect": rect,
                                                           "min": mn, "max": mx}
    fake_win = [win(123, "Друзья - Discord", "Discord.exe", (300, 100, 900, 600)),
                win(456, "Блокнот", "notepad.exe", (0, 0, 10, 10), mn=True),
                win(789, "Claude", "claude.exe", (1000, 100, 1500, 700))]
    plat = {"rect": (1000, 700, 1400, 1100)}
    root = tk.Tk()
    rec = Rec()
    p = Pet(root, claude=lambda prompt: (asked.append(prompt), "привет")[1], fx=rec, windows=lambda: fake_win,
            plats=lambda: [(777,) + plat["rect"] + (True,)] if plat["rect"] else [],
            frame=lambda h: plat["rect"] if h == 777 else None)
    p.start_apps = [("Тестапп", "shell:AppsFolder\\X!y"), ("Steam", "shell:AppsFolder\\S!s")]
    p.apps = []
    p.now = lambda: t0 + p.clock                                 # время Клодика = виртуальные часы теста
    p.fullscreen_app = lambda: False                             # не зависеть от того, что сейчас на экране у владельца
    assert [r["text"] for r in p.reminders] == ["потом"], p.reminders   # пропущенное убрано и будет сказано
    run = lambda sec: [p.update(1 / 144) for _ in range(int(sec * 144))]

    def settle(limit=60):
        for _ in range(int(limit * 10)):
            time.sleep(0.002)
            run(0.1)
            if not p.busy:
                return
        raise AssertionError(f"завис в {p.state}: thinking={p.thinking} job={p.job} jobs={len(p.jobs)} dz={bool(p.dz)} "
                             f"phase={p.job_phase} x={p.x:.0f} y={p.y:.0f} vy={p.vy:.0f} vx={p.vx} ground={p.ground} "
                             f"surface={p.surface} door={p.door_plan} pose={p.pose}")

    for st in ("walk", "idle", "sleep", "eat", "chase"):
        p.state, p.timer = st, 0.3
        run(0.5)
    for hat in HATS:                                            # все шапки рисуются
        p.hat, p.key = hat, None
        p.draw()
    p.hat = "auto"
    p.hunger = 50.0
    p.feed(); run(6)
    assert p.food is None and p.hunger < 20, "не доел печеньку"
    p.toggle_ball(); run(3)
    assert p.ball and p.L <= p.ball.x <= p.R, p.ball.x
    p.toggle_ball()
    # команды — без токенов
    p.send("Клодик, открой тестапп, закрой дискорд и сделай потише на 20")
    settle()
    assert rec.calls == [("start", "shell:AppsFolder\\X!y"), ("close", 123), ("keys", 0xAE, 10)], rec.calls
    rec.calls.clear()
    p.send("запусти стим, сверни блокнот, найди рецепт борща, пауза")
    settle()
    assert rec.calls == [("start", "shell:AppsFolder\\S!s"), ("min", 456),
                         ("start", "https://www.google.com/search?q=%D1%80%D0%B5%D1%86%D0%B5%D0%BF%D1%82%20%D0%B1%D0%BE%D1%80%D1%89%D0%B0"),
                         ("keys", 0xB3, 1)], rec.calls
    p.send("закрой окно")
    assert "Не нашёл" in p.bubble.l.cget("text")
    # бульдозер: закрывает всё, кроме Claude; свёрнутое — в конце
    rec.calls.clear()
    p.send("закрой все окна")
    settle()
    closed = [c[1] for c in rec.calls if c[0] == "close"]
    assert sorted(closed) == [123, 456] and ("move", 123) in rec.calls and 789 not in closed, rec.calls
    assert "Закрыл 2 окна" in p.bubble.l.cget("text"), p.bubble.l.cget("text")
    # напоминания: сохраняются на диск, звенят вовремя, отменяются
    rec.calls.clear()
    p.send("напомни через 1 секунду попить воды")
    assert [r["text"] for r in p.reminders] == ["попить воды", "потом"], p.reminders
    assert "попить воды" in json.dumps(pet_tasks.read_json(pet_tasks.REMINDERS, []), ensure_ascii=False)
    run(1.6)
    assert p.state == "alarm" and "попить воды" in p.bubble.l.cget("text") and ("beep",) in rec.calls
    p.stop_alarm()
    p.send("напомни завтра в 9 позвонить маме")
    assert any(r["text"] == "позвонить маме" for r in p.reminders), p.reminders
    p.send("отмени напоминание про маму")
    assert not any("маме" in r["text"] for r in p.reminders) and any(r["text"] == "потом" for r in p.reminders)
    assert parse_duration("засеки полчаса") == 1800 and parse_duration("таймер на 1 час 20 минут") == 4800
    # список дел, калькулятор, переводчик — без токенов (перевод — через мозги)
    p.send("запиши купить хлеб")
    p.send("добавь в список позвонить Васе")
    assert p.notes == ["купить хлеб", "позвонить васе"], p.notes
    p.notes_window()
    p.send("вычеркни хлеб")
    assert p.notes == ["позвонить васе"] and pet_tasks.read_json(pet_tasks.NOTES, []) == ["позвонить васе"]
    p.notes_win.destroy()
    n_asked = len(asked)
    p.send("сколько будет 15 процентов от 3400")
    assert "= 510" in p.bubble.l.cget("text") and len(asked) == n_asked, p.bubble.l.cget("text")
    p.send("переведи доброе утро на английский")
    settle()
    assert len(asked) == n_asked + 1 and "английский" in asked[-1] and "доброе утро" in asked[-1], asked[-1]
    asked.clear()                                                # дальше снова проверяем, что команды не ходят в ИИ
    # память о тебе: явная («запомни, что я…») и тихая (из болтовни — через ИИ)
    p.llm = lambda system, prompt, tokens=400: (
        "CMD: сделай громче" if "искажённая команда" in prompt else
        "ИТОГ: Хороший был день, много играли.\nФ: Опять Дота?\nФ: Я выспался, а ты?" if "ИТОГ" in prompt else
        "любит котиков")
    p.send("запомни, что я люблю доту")
    assert [f["fact"] for f in p.memory] == ["люблю доту"], p.memory
    p.send("что ты обо мне знаешь")
    assert "люблю доту" in p.bubble.l.cget("text")
    p.send("забудь что я люблю доту")
    assert not p.memory
    p.send("у меня дома живёт кот")
    settle()
    for _ in range(50):
        time.sleep(0.02)
        run(0.05)
    assert [f["fact"] for f in p.memory] == ["любит котиков"], p.memory
    p.send("как дела")
    settle()
    assert "любит котиков" in asked[-1], asked[-1]               # мозги видят, что я о тебе знаю
    # итоги дня: дневник, свежие фразы, самообучение на непонятых фразах
    p.day = {"date": "2026-01-01", "cmds": {"сделай громче": 3}, "fails": ["громкость в верх"], "chat": 2,
             "games": {"dota2": 3600}}
    p.close_day()
    diary = pet_tasks.read_json(pet_smart.DIARY, [])
    assert diary[-1]["summary"].startswith("Хороший") and diary[-1]["learned"] == 1, diary
    assert p.learned.get("громкость в верх") == "сделай громче" and p.fresh == ["Опять Дота?", "Я выспался, а ты?"]
    assert p.day["date"] == pet_smart.today() and p.walk_phrase()
    p.morning()
    assert "dota2" in p.bubble.l.cget("text") and "выучил 1" in p.bubble.l.cget("text"), p.bubble.l.cget("text")
    p.game_t, p.hinted = 4 * 3600, {}
    p.hints()
    assert "3 часа" in p.bubble.l.cget("text")
    asked.clear()
    # этап 5: режимы, «точно?», буфер, файлы, папки, печать
    from . import pet_pc
    pet_pc.MODES = os.path.join(HERE, "modes.selftest.json")
    rec.calls.clear()
    p.send("запомни режим работы: открой тестапп и сделай громче")
    assert p.modes.get("работ") == "открой тестапп и сделай громче", p.modes
    p.send("режим работы")
    settle()
    assert ("start", "shell:AppsFolder\\X!y") in rec.calls and ("keys", 0xAF, 5) in rec.calls, rec.calls
    rec.calls.clear()
    p.send("выключи комп через 10 минут")
    assert "Скажи «да»" in p.bubble.l.cget("text") and not rec.calls
    p.send("да")
    assert rec.calls == [("shutdown", 600, False)], rec.calls
    p.send("отмени выключение")
    p.send("перезагрузи комп")
    p.send("нет")
    assert rec.calls == [("shutdown", 600, False), ("abort",)], rec.calls
    p.root.clipboard_clear(); p.root.clipboard_append("helo wrld")
    p.llm = lambda system, prompt, tokens=400: "hello world" if "helo wrld" in prompt else ""
    p.send("исправь то что скопировал")
    for _ in range(100):
        time.sleep(0.01)
        run(0.02)
        if p.root.clipboard_get() == "hello world":
            break
    assert p.root.clipboard_get() == "hello world", p.root.clipboard_get()
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        open(os.path.join(tmp, "Отчёт_за_ноябрь.txt"), "w").close()
        os.makedirs(os.path.join(tmp, "AppData")); open(os.path.join(tmp, "AppData", "отчёт.txt"), "w").close()
        assert [os.path.basename(x) for x in pet_pc.find_files("отчёт", roots=[tmp])] == ["Отчёт_за_ноябрь.txt"]
        assert pet_pc.newest(tmp).endswith("Отчёт_за_ноябрь.txt")
        p.files_result(json.dumps({"q": "отчёт", "open": False, "hits": [os.path.join(tmp, "Отчёт_за_ноябрь.txt")]}))
        rec.calls.clear()
        p.send("открой первый")
        assert rec.calls and rec.calls[0][1].endswith("Отчёт_за_ноябрь.txt"), rec.calls
    rec.calls.clear()
    p.send("открой загрузки")
    assert rec.calls == [("start", os.path.join(os.environ["USERPROFILE"], "Downloads"))], rec.calls
    p.send("напечатай Привет, Мир")
    assert p.root.clipboard_get() == "Привет, Мир"
    # большой промпт, этап 1: политика доступа, журнал, «Стоп», откат, корзина
    called = []
    p.gate("format_disk", "отформатировать диск D", lambda: called.append("format"))
    assert not called and "никогда" in p.bubble.l.cget("text")
    p.gate("registry", "поменять реестр", lambda: called.append("reg"))
    p.send("да")
    assert not called and "подтверждаю" in p.bubble.l.cget("text")
    p.send("подтверждаю")
    assert called == ["reg"], called
    p.set_level("advisor")
    rec.calls.clear()
    p.send("открой тестапп")
    settle()
    assert not rec.calls and "Советник" in p.bubble.l.cget("text"), (rec.calls, p.bubble.l.cget("text"))
    p.set_level("assistant")
    p.send("сверни блокнот")
    settle()
    assert ("min", 456) in rec.calls
    p.send("верни как было")
    assert ("restore", 456) in rec.calls, rec.calls
    p.plan([{"do": "open", "app": "тестапп"}, {"do": "open", "app": "steam"}])
    p.send("стоп")
    assert not p.job and not p.jobs and "Стоп" in p.bubble.l.cget("text")
    jr = policy.read_journal()
    assert any(e["action"] == "minimize" and e["by"] == "текст" for e in jr) and any(e["action"] == "stop" for e in jr), jr[-5:]
    assert any(e["result"] == "запрещено политикой" for e in jr)
    import tempfile
    tf = os.path.join(tempfile.gettempdir(), "klodik_recycle_test.txt")
    open(tf, "w").write("тест корзины")
    policy.recycle(tf)
    assert not os.path.exists(tf)
    w = p.journal_window(); w.destroy()
    # склонение (тесты из промпта), разбор памяти, мастер знакомства, функции, тихие часы, копии
    from .decline import decline
    for c in json.load(open(os.path.join(policy.PKG_DATA, "name_declension_tests.json"), encoding="utf-8"))["cases"]:
        d = decline(c["name"], c["lang"])
        assert all(d[k] == c[k] for k in ("vocative", "genitive", "dative")), (c, d)
    facts = pet_onboard.parse_facts(open(pet_onboard.SEED, encoding="utf-8").read())
    assert not any("12345" in f["fact"] for f in facts), facts                     # пароль не попал
    assert any(f["private"] and "Родители" in f["fact"] for f in facts) and any(f["touchy"] for f in facts)
    p.memory = []
    p.onboarding()
    want = {"seed_memory": "Оставить", "gemini_key": "Сохранить", "access_level": "Выбрать", "quiet_hours": "Включить"}
    for _ in range(30):
        if not p.ob_win.winfo_exists():
            break
        btns = {b.cget("text"): b for b in p.ob_btns.winfo_children()}
        if "Дальше" in btns:                                     # шаг «имя»
            ents = [e for e in p.ob_body.winfo_children() if isinstance(e, tk.Entry)]
            ents[0].delete(0, "end")
            ents[0].insert(0, "Олексій")
            btns["Дальше"].invoke()
            continue
        sid = p.ob_todo[p.ob_i]["id"] if p.ob_i < len(p.ob_todo) else "finish"
        if sid == "gemini_key":
            [e for e in p.ob_body.winfo_children() if isinstance(e, tk.Entry)][0].insert(0, "test-key")
        label = "Готово" if "Готово" in btns else want.get(sid, "Позже")
        btns[label].invoke()
    assert not p.ob_win.winfo_exists(), "мастер не дошёл до конца"
    assert p.addr() == "Олексію" and p.profile["forms"]["genitive"] == "Олексія", p.profile
    assert p.ob["done"]["name"] == "yes" and p.ob["done"]["ollama"] == "later" and p.ob["done"]["seed_memory"] == "yes"
    assert pet_onboard.read_env()["GEMINI_API_KEY"] == "test-key" and p.prefs.get("quiet")
    assert any("чай" in m["fact"] for m in p.memory) and not any("кредит" in m["fact"] for m in p.memory), p.memory
    p.send("называй меня Макс")
    assert p.profile["name"] == "Макс"
    p.set_name("Олексій")
    p.toggle("climb", False)
    assert not p.on("climb")
    p.toggle("climb", True)
    p.prefs["quiet"] = ["00:00", "23:59"]
    assert p.quiet_now()
    p.prefs["quiet"] = ["03:00", "03:01"]
    p.daily_backup()
    assert os.listdir(pet_prefs.BACKUP_DIR), "нет резервной копии"
    upd.mark_alive()
    assert os.path.exists(upd.OK_FLAG)
    p.memory_import_window(facts).destroy()
    # этап 2 большого промпта: эмоции (все 13 × 3 силы рисуются), шапки, двери, сценки, сон, угол в игре
    from .anim import EMO
    from .looks import HAT_ART, NEW_HATS, paint2
    p.state, p.surface, p.timer = "idle", None, 99
    for emo in EMO["emotions"]:
        for lv in ("light", "medium", "strong"):
            p.emo.clip = p.emo.queue = None
            p.emo.queue = []
            assert p.emote(emo, lv), emo
            for _ in range(int(3 * 144 / 6)):                    # кадры клипа
                p.update(6 / 144)
    assert len(NEW_HATS) >= 19 and all(h in HAT_ART or h == "geek" for h in NEW_HATS)
    cv = tk.Canvas(root)
    for h in list(HAT_ART) + ["geek", "glasses"]:
        paint2(cv, 0, 40, {"hat": h, "arms": "wave", "eyes": "happy", "blush": 1, "brow": "raise"})
    cv.destroy()
    p.send("надень шлем космонавта")
    assert p.hat == "astronaut", p.hat
    p.send("покажи радость")
    assert p.emo.clip and p.emo.clip["emo"] == "joy"
    p.send("спасибо")
    assert p.emo.clip["emo"] in ("gratitude", "joy")
    p.toggle("climb", False)                                     # чтобы не запрыгнул на тестовое окно
    p.state, p.x, p.y, p.vy, p.timer, p.surface, p.surf = "idle", float(p.L + 400), float(p.B - H), 0.0, 99, None, None
    p.emo.clip, p.emo.queue = None, []
    p.door_trip("cowboy")
    assert p.door_plan, (p.bubble.l.cget("text"), p.busy, p.surface, p.state, p.thinking, p.job, p.jobs, p.dz)
    for _ in range(300):
        run(0.1)
        if not p.door_plan:
            break
    assert p.door_plan is None and p.hat == "cowboy" and p.state == "idle", (p.door_plan, p.hat, p.state)
    p.toggle("climb", True)
    p.state = "sleep"
    p.ptr_last = (-9999, -9999)
    p.root.winfo_pointerxy = lambda: (int(p.x + 50), int(p.y + 40))
    p.sleep_wake()
    assert p.state == "idle"
    del p.root.winfo_pointerxy
    p.prefs["working"] = True
    assert p.emote("joy") is None                               # «я работаю» — тишина
    p.prefs["working"] = False
    p.set_pref("game_mode", "corner")
    p.set_gaming(True)
    assert p.root.winfo_viewable() and p.state == "sleep"
    p.set_gaming(False)
    p.set_pref("game_mode", "hide")
    # этап 3: слой ИИ (облако/локально, лимиты, кэш, приватность), характер, план, поправки, плагины
    from .ai import AI, parse_json
    from . import tools as T
    calls = []
    a = AI()
    ai_mod.env = lambda: {"GEMINI_API_KEY": "k"}
    a.gemini = lambda *x: (calls.append("cloud"), '{"say":"ok"}')[1]
    a.ollama = lambda *x, **kw: (calls.append("local"), '{"say":"ok"}')[1]
    a.ask("s", "личное", task="chat", private=True)
    a.ask("s", "план", task="plan", private=False)
    a.ask("s", "план", task="plan", private=False)                 # повтор — из кэша
    assert calls == ["local", "cloud"], calls
    a.gemini = lambda *x: (_ for _ in ()).throw(OSError("429"))
    assert a.ask("s", "другой план", task="plan", private=False) and calls[-1] == "local" and a.where == "local"
    a.minute = [time.time()] * 8
    assert not a.can_cloud()                                       # запас под лимит
    ai_mod.env = lambda: {}
    assert parse_json("вот: {\"text\": \"hi\"} ок")["text"] == "hi" and parse_json("просто")["text"] == "просто"
    p.memory = [{"fact": "любит чай", "private": False}, {"fact": "служит", "private": True}]
    sysp = p.personality()
    assert "Олексію" in sysp and "служит" in sysp and "служит" not in p.personality(cloud=True)
    p.claude = lambda prompt: '{"text": "Ого, привет!", "emotion": "surprise", "intensity": "strong"}'
    p.send("как ты")
    settle()
    assert "Ого, привет!" in p.bubble.l.cget("text") and p.emo.clip and p.emo.clip["emo"] == "surprise"
    rec_t = []
    T.get_volume, T.set_volume = (lambda: 50), (lambda v: rec_t.append(("vol", v)))
    T.get_theme, T.set_theme = (lambda: "light"), (lambda m: rec_t.append(("theme", m)))
    p.ai.ask = lambda *x, **kw: json.dumps({"say": "Сделаю", "steps": [
        {"tool": "set_volume", "args": {"percent": 30}, "why": "тише"},
        {"tool": "theme", "args": {"mode": "dark"}, "why": "тёмная тема"}]}, ensure_ascii=False)
    p.send("настрой тёмную тему")
    for _ in range(100):
        time.sleep(0.01); run(0.02)
        if p.confirm:
            break
    assert p.confirm and "Выполнить план" in p.bubble.l.cget("text"), p.bubble.l.cget("text")
    p.send("да")
    for _ in range(200):
        time.sleep(0.01); run(0.02)
        if ("theme", "dark") in rec_t:
            break
    assert rec_t == [("vol", 30), ("theme", "dark")], rec_t
    run(0.2)
    p.send("верни как было")
    assert ("theme", "light") in rec_t
    p.send("так не делай")
    assert p.rules and p.rules[-1]["tool"] in ("theme", "undo"), p.rules
    p.rules = [{"text": "не делать: theme", "tool": "theme", "target": "", "t": 0}]
    rec_t.clear()
    p.send("настрой тёмную тему")
    for _ in range(100):
        time.sleep(0.01); run(0.02)
        if rec_t:
            break
    assert rec_t == [("vol", 30)] and not any(x[0] == "theme" for x in rec_t), rec_t   # правило: тему не трогать
    assert T.tool_action("powershell", {"command": "Get-Date"}) == "pc_info"
    assert p.decide(T.tool_action("powershell", {"command": "Remove-Item C:\\x"})) == "ask"
    p.hinted, p.game_t, p.prefs["rejected"] = {}, 4 * 3600, []
    p.hints()
    assert p.last_hint and p.last_hint[0] == "game"
    p.send("не надо")
    assert "game" in p.prefs["rejected"]
    p.hinted = {}
    p.say("—", 1)
    p.hints()
    assert "3 часа" not in p.bubble.l.cget("text")
    p.llm = lambda system, prompt, tokens=400: "1) узнал 2) починил"
    p.weekly_report(show=False)
    for _ in range(50):
        time.sleep(0.02)
        if os.path.isdir(pet_brain.WEEKLY) and os.listdir(pet_brain.WEEKLY):
            break
    assert os.listdir(pet_brain.WEEKLY)
    pd = os.path.join(pet_brain.PLUGINS, "echo")
    os.makedirs(pd)
    open(os.path.join(pd, "plugin.py"), "w", encoding="utf-8").write(
        "import os, sys\nprint('плагин:', sys.argv[1], 'песочница' if os.environ.get('KLODIK_SANDBOX') == '1' else '')\n")
    pet_tasks.write_json(os.path.join(pd, "plugin.json"), {"name": "echo", "pattern": "эхо", "enabled": True})
    p.plugins = p.load_plugins()
    assert "песочница" in p.run_plugin(p.plugins[0], "тест", sandbox=True)
    p.send("эхо привет")
    for _ in range(200):
        time.sleep(0.02); run(0.02)
        if "плагин:" in p.bubble.l.cget("text"):
            break
    assert "плагин: эхо привет" in p.bubble.l.cget("text"), p.bubble.l.cget("text")
    p.claude = lambda prompt: (asked.append(prompt), "привет")[1]
    p.state = "idle"
    p.recall_window().destroy()
    # этап 6: характер, мини-игры, эмоции, танцы, настройки, обновления
    from . import update
    import pycaw.pycaw                                           # счётчик звука для танцев (и в .exe тоже)
    assert pycaw.pycaw.AudioUtilities
    p.meter.ok = False                                          # реальная музыка на компе не должна влиять на тест
    p.send("будь дерзким")
    assert p.persona == "sassy" and "саркастичный" in p.persona_prompt() and p.ack() in pet_fun.PERSONAS["sassy"][2]
    p.send("будь добрым")
    p.send("сыграем в камень, ножницы, бумага")
    assert p.game and p.game["kind"] == "rps", p.game
    p.send("камень")
    assert "У меня" in p.bubble.l.cget("text"), p.bubble.l.cget("text")
    p.send("хватит")
    assert p.game is None
    p.send("угадай число")
    p.game["secret"] = 42
    p.send("пятьдесят")
    assert "Меньше" in p.bubble.l.cget("text")
    p.send("42")
    assert "Угадал" in p.bubble.l.cget("text") and p.game is None
    p.llm = lambda system, prompt, tokens=400: "ВОПРОС: Столица Франции?\nОТВЕТ: Париж"
    p.send("викторина")
    for _ in range(100):
        time.sleep(0.01)
        run(0.02)
        if p.game and p.game.get("a"):
            break
    assert "Франции" in p.bubble.l.cget("text"), p.bubble.l.cget("text")
    p.send("это париж")
    assert "Правильно" in p.bubble.l.cget("text") and p.game["score"] == 1
    p.send("хватит")
    p.send("лови печеньки")
    run(2.5)
    assert p.game["cookies"], "печеньки не падают"
    p.catch_hit(p.game["cookies"][0])
    assert p.game["score"] == 1
    run(31)
    assert p.game is None and p.last_score == 1                 # облачко могла перебить случайная фраза — смотрим счёт
    p.state = "idle"
    for _ in range(5):
        p.poke()
    assert p.angry_until > p.clock
    p.key = None; p.draw()                                     # злое лицо рисуется
    p.dance()
    run(1)
    assert p.state == "dance"
    run(7)
    assert p.state != "dance"
    p.day["games"] = {"DiabloImmortal": 5400}
    p.send("сколько я сегодня играл")
    assert "Diablo Immortal" in p.bubble.l.cget("text"), p.bubble.l.cget("text")
    win = p.open_settings() or p.settings_win
    assert win.winfo_exists()
    win.destroy()
    assert update.ver("v99.0.0") > update.ver(update.VERSION) and update.repo()   # без сети: GitHub проверяю отдельно
    if os.path.exists(pet_pc.MODES):
        os.remove(pet_pc.MODES)
    asked.clear()
    # фото
    p.send("сфоткай")
    settle()
    assert ("shot",) in rec.calls and "Сохранил" in p.bubble.l.cget("text")
    # друг
    p.send("позови друга")
    assert p.buddy
    run(3)
    p.send("прогони друга")
    run(25)
    assert p.buddy is None, "друг не ушёл"
    # окна-платформы: залезть, ехать вместе с окном, упасть, когда окно пропало
    run(0.5)
    p.state, p.timer, p.x = "idle", 5, 600.0
    assert p.try_climb()
    for _ in range(150):
        run(0.1)
        if p.surface:
            break
    p.state, p.timer = "idle", 100
    assert p.surface == 777 and abs(p.y - (700 - H)) < 1, (p.surface, p.y, p.state)
    x0 = p.x
    plat["rect"] = (1100, 650, 1500, 1050)
    run(0.1)
    assert abs(p.x - x0 - 100) < 1 and abs(p.y - (650 - H)) < 1, (p.x, p.y)
    plat["rect"] = None
    run(4)
    assert p.surface is None and p.y == p.B - H, (p.surface, p.y)
    # снег и болтовня
    p.set_snow("on"); run(0.5)
    assert p.snow
    p.set_snow("off")
    assert not asked, "команды не должны тратить токены"
    p.send("как дела?")
    settle()
    assert len(asked) == 1 and len(asked[0]) < 400 and "привет" in p.bubble.l.cget("text"), asked
    # голос: «Клодик» на слух модели — «клади к»
    v = VoiceLogic()
    assert v.final("клади к открой блокнот", 0) == [("voice", "открой блокнот")]
    assert v.final("сделай громче", 5) == [("voice_follow", "сделай громче")]        # 20 с без «Клодик»
    assert v.tick(30) == [("follow_end",)] and v.final("сделай громче", 31) == []    # потом — снова нужно имя
    v = VoiceLogic()
    assert v.partial("клади к", 0) == [("wake",)] and v.final("клади к", 0) == []
    assert v.partial("засеки", 1) == [("heard", "засеки")] and v.final("засеки пять минут", 2) == [("voice", "засеки пять минут")]
    v = VoiceLogic()
    assert v.final("ну клод разгромив все окна", 3) == [("voice", "разгромив все окна")]
    v = VoiceLogic()
    assert v.final("кладу на стол", 4) == [] and v.final("клади", 5) == [("wake",)] and v.tick(20) == [("voice_timeout",)]
    for heard in ("лодик открой", "колодик открой", "кладик открой", "клоди к открой", "эй клод открой"):
        assert VoiceLogic().final(heard, 0) == [("voice", "открой")], heard
    assert VoiceLogic().final("кто там открой", 0) == []
    # имя так, как его реально слышала распознавалка у пользователя
    for heard in ("клодия", "колодок", "логик", "владик", "плотик", "клодии к", "кладик"):
        assert wake_len(heard.split()) > 0, heard
    assert wake_len("клодия включи музыку".split()) == 1 and wake_len("кладу на стол".split()) == 0
    assert wake_len("пошли в доту".split()) == 0 and wake_len("включи музыку".split()) == 0
    assert isinstance(in_call(), bool)
    assert wake_len("хладик закрой роблокс".split()) == 1 and wake_len("клодиак".split()) == 1
    v = VoiceLogic()                                             # в звонке: только по имени, без «20 с без имени»
    v.strict = True
    assert v.final("клодия открой стим", 0) == [("voice", "открой стим")] and v.final("пошли в доту", 2) == []
    assert v.final("клодия", 3) == [("wake",)] and v.final("сделай громче", 4) == [("voice", "сделай громче")]
    rec.calls.clear()
    vol0 = p.voice_vol
    p.send("говори тише")
    assert p.voice_vol == vol0 - 15 and p.speaker.volume == p.voice_vol and not rec.calls, (p.voice_vol, rec.calls)
    p.set_volume(vol0)
    # голос Клодика: отвечает вслух на твою просьбу, а случайные фразы — молча
    class FakeSpeaker:
        said = []
        def say(s, t): s.said.append(t)
        def speaking(s): return False
        def hush(s): pass
    p.speaker = FakeSpeaker()
    p.talk_until = 0
    p.say("просто гуляю")
    assert not p.speaker.said
    p.send("сделай громче")
    assert p.speaker.said, "ответ на просьбу не прозвучал"
    settle()
    # подстройка: «Клодик» звучит как «клодия» — запоминаю; кривые команды — учу
    class FakeListener:
        calib = False
        def stop(s): pass
    p.listener = FakeListener()
    p.calibrate()
    for _ in range(5):
        p.on_calib("calib", "клодия"); p.calib_next()
    p.on_calib("calib", "клодия открой с тем"); p.calib_next()
    p.calib_done()
    assert "klodiya" in voice.WAKE_EXTRA and p.learned.get("открой с тем") == "открой steam", (voice.WAKE_EXTRA, p.learned)
    assert os.path.exists(voice.PROFILE)
    p.listener = None
    # числа словами, похожие слова, обучение
    assert parse_duration("засеки двадцать пять минут") == 1500 and num_words("потише на двадцать") == "потише на 20"
    assert p.fix_words("засеки пяти минут") == "засеки пять минут", p.fix_words("засеки пяти минут")
    rec.calls.clear()
    p.send("гомче", voice=True)
    settle()
    assert rec.calls == [("keys", 0xAF, 5)] and p.learned.get("гомче") == "громче", (rec.calls, p.learned)
    rec.calls.clear()
    p.claude = lambda prompt: (asked.append(prompt), "CMD: сделай потише")[1]   # ИИ угадал команду
    p.send("чтоб не орало", voice=True)
    settle()
    assert ("keys", 0xAE, 5) in rec.calls and p.learned.get("чтоб не орало") == "сделай потише", p.learned
    rec.calls.clear()
    n_asked = len(asked)
    p.send("чтоб не орало", voice=True)                        # второй раз — сам, без токенов
    settle()
    assert ("keys", 0xAE, 5) in rec.calls and len(asked) == n_asked
    found, games = scan_apps()
    assert isinstance(found, list) and isinstance(games, list) and os.path.exists(apps.APPS_CACHE)
    import sounddevice, vosk                                     # пакеты для голоса на месте (и в .exe тоже)
    assert vosk.KaldiRecognizer and sounddevice.query_devices() is not None
    rec.calls.clear()
    p.on_voice("wake")
    assert p.carry and p.carry[0] == "mic"
    p.on_voice("voice", "сделай громче")
    settle()
    assert rec.calls == [("keys", 0xAF, 5)], rec.calls
    # мозги без ИИ и установка в папку-песочницу
    p.brain = "none"
    assert p.think("привет") in CANNED
    assert ollama_models() is None or isinstance(ollama_models(), list)
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        links = {k: os.path.join(tmp, "links", f"{k}.lnk") for k in ("menu", "menu_rm", "desktop", "startup")}
        exe = install_files(sys.executable, os.path.join(tmp, "app"), links)
        assert os.path.exists(exe) and all(os.path.exists(x) for x in links.values()), os.listdir(os.path.join(tmp, "links"))
        make_icon(os.path.join(tmp, "k.ico"))
        assert os.path.getsize(os.path.join(tmp, "k.ico")) > 500
    # живой Клодик: настроение, границы, душа, сны, встреча, день рождения
    p.soul["mood"]["boredom"] = 0.9
    assert p.dominant() == ("boredom", "strong")
    p.mood_drift(3600)
    assert p.soul["mood"]["boredom"] < 0.05 and abs(p.soul["mood"]["interest"] - 0.4) < 0.01
    p.send("ты живой?")
    assert "программа" in p.bubble.l.cget("text"), p.bubble.l.cget("text")
    n = len(p.soul["diary"])
    assert p.on_user_text("мне сегодня хреново") == "support"
    p.write_diary("тест")
    assert len(p.soul["diary"]) == n                       # в плохой день — без записей
    p.bad_day = -9999
    p.write_diary("тест")
    assert p.soul["diary"][-1]["t"] == "тест"
    p.pending_q = ("цвет", p.clock)
    p.on_user_text("зелёный")
    assert p.soul["favorites"]["цвет"] == "зелёный"
    p.soul["dreams"].append({"d": __import__("datetime").date.today().isoformat(), "t": "летал на печеньке"})
    p.send("что тебе снилось")
    assert "печеньке" in p.bubble.l.cget("text")
    p.soul["xp"], lvl = 99 * p.soul["level"] + 99, p.soul["level"]
    p.gain(5)
    assert p.soul["level"] == lvl + 1
    p.welcome_back(7 * 3600, ["книжку читал"])
    assert "Давно не виделись" in p.bubble.l.cget("text") and "книжку" in p.bubble.l.cget("text")
    born = __import__("datetime").date.today().replace(year=__import__("datetime").date.today().year - 1)
    p.soul["born"], p.soul["rituals"] = born.isoformat(), {}
    p.rituals()
    assert p.carry and p.carry[0] == "cake" and "день рождения" in p.bubble.l.cget("text")
    p.carry = None
    p.prefs["no_emotions"] = True
    n = len(p.soul["diary"])
    p.write_diary("нельзя")
    assert len(p.soul["diary"]) == n
    p.prefs["no_emotions"] = False
    assert isinstance(idle_seconds(), float)
    p.soul_window().destroy()
    p.soul_tick(10)
    assert os.path.exists(pet_soul.SOUL)
    # этап 5: дела, окна, файлы, свет
    assert pet_desk.grid(4, (0, 0, 1000, 800)) == [(0, 0, 500, 400), (500, 0, 500, 400), (0, 400, 500, 400), (500, 400, 500, 400)]
    assert pet_desk.SECRET.search("Qwerty12345") and pet_desk.SECRET.search("4149 4993 1234 5678")
    assert not pet_desk.SECRET.search("купить хлеб и молоко")
    dl = os.path.join(tmp_dir, "dl")
    os.makedirs(dl, exist_ok=True)
    for f in ("a.jpg", "b.zip", "c.pdf", "d.xyz"):
        open(os.path.join(dl, f), "w").close()
    sp = pet_desk.sort_plan(dl)
    assert sorted(os.path.basename(os.path.dirname(b)) for _, b in sp) == ["Архивы", "Документы", "Фото"]
    ac, pct, mins = pet_desk.power_status()
    assert isinstance(ac, bool)
    p.pomodoro()
    assert p.prefs["working"] and p.pomo["phase"] == "work"
    p.pomo["end"] = 0
    p.pomo_tick()
    assert p.pomo["phase"] == "break" and not p.prefs["working"]
    p.send("помодоро стоп")
    assert p.pomo is None
    p.send("стикер купить корм коту")
    assert p.stickers and pet_desk.read_json(pet_desk.STICKERS, [])[0]["t"] == "купить корм коту"
    p.stickers[0]["w"].destroy(); p.stickers.clear()
    p.track = {}
    p.prefs.setdefault("off", [])
    p.track[__import__("datetime").date.today().isoformat()] = {"Code": 3700, "Steam": 600}
    assert p.track_report().startswith("Code — 1 ч 1 мин")
    p.send("добавь проект Парковка бот")
    assert p.projects[-1]["name"] == "парковка бот" or p.projects[-1]["name"].lower() == "парковка бот"
    p.projects[-1]["last"] = (__import__("datetime").date.today() - __import__("datetime").timedelta(days=1)).isoformat()
    assert "продолжим" in p.yesterday_project()
    for cmd in ("разложи окна", "закрепи окно поверх всех", "кто открыл порты", "что зависло", "пинг", "сожми видео",
                "разбери загрузки", "что это за ошибка", "погода", "какой курс доллара", "проверь ботов", "на добраніч",
                "история буфера"):
        assert p.desk_command(cmd), cmd
    assert p.desk_command("покажи курсор") is None
    p.on_battery = False
    pet_desk.power_status, real_ps = (lambda: (False, 40, 50)), pet_desk.power_status
    p.power_tick()
    assert p.on_battery and p.prefs["anim"] == "min" and "свет" in p.bubble.l.cget("text")
    pet_desk.power_status = lambda: (True, 100, None)
    p.power_tick()
    assert not p.on_battery and p.prefs["anim"] != "min"
    pet_desk.power_status = real_ps
    p.guard_tick(); p.guard_tick()
    p.clips_window().destroy()
    p.desk_tick(10)
    # этап 6: игры, голос и звук, ИИ-помощник
    b = ["X", "X", "", "O", "", "", "", "", ""]
    assert pet_play.ttt_move(b) == 2 and pet_play.ttt_winner(["X"] * 3 + [""] * 6) == "X"
    assert pet_play.ttt_move(["X", "", "", "", "O", "", "", "", "X"]) in (1, 3, 5, 7)
    assert pet_play.ttt_winner(["X", "O", "X", "X", "O", "O", "O", "X", "X"]) == "draw"
    cf = os.path.join(tmp_dir, "t.csv")
    open(cf, "w", encoding="utf-8").write("имя;сумма\nа;10\nб;30\n")
    assert "2 строк" in pet_play.csv_summary(cf) and "среднее 20" in pet_play.csv_summary(cf)
    wf = pet_play.make_noise(os.path.join(tmp_dir, "sounds", "rain.wav"), "rain", secs=1)
    assert os.path.getsize(wf) > 40000
    assert p.costumes["dota2"] == "wizard" and os.path.exists(pet_play.COSTUMES)
    p.cos_hat = "wizard"
    assert p.hat_now() == "wizard" or p.hat != "auto"
    p.cos_hat = None
    n = len(p.reminders)
    p.send("таймер рошана")
    assert len(p.reminders) == n + 2
    p.send("кулдаун ульты 90 сек")
    assert len(p.reminders) == n + 3
    p.reminders = p.reminders[:n]
    p.send("заметка про пуджа: хук через деревья")
    p.send("что я записал про пуджа")
    assert "хук" in p.bubble.l.cget("text"), p.bubble.l.cget("text")
    p.send("гайд по кракену")
    assert "не буду выдумывать" in p.bubble.l.cget("text")
    p.send("будь ворчуном")
    assert p.persona == "grumpy" and "ворчлив" in p.personality()
    p.send("отвечай подробнее")
    assert "подробно" in p.personality()
    p.send("будь добряком")
    for cmd in ("крестики нолики", "кто быстрее", "белый шум", "метроном 90", "черновик ответа", "разбери csv",
                "что играет", "топ игр", "какой командой узнать версию windows"):
        assert p.play_command(cmd), cmd
    p.tictactoe().destroy(); p.reaction().destroy()
    p.costume_tick()
    # этап 7: связь, режимы, каталог
    from . import pet_link
    up = {"message": {"chat": {"id": 42}, "from": {"id": 42}, "text": "открой steam"}}
    assert pet_link.owner_msg(up, "42") == "открой steam"
    assert pet_link.owner_msg({"message": {"chat": {"id": 7}, "from": {"id": 7}, "text": "скрин"}}, "42") is None
    assert pet_link.kyiv_alert([{"alert_type": "air_raid", "location_title": "м. Київ"}], "м. Київ")
    assert not pet_link.kyiv_alert([{"alert_type": "air_raid", "location_title": "Львівська область"}], "м. Київ")
    p.tg_command("скрин")
    sent = [p.tg_out.get_nowait() for _ in range(p.tg_out.qsize())]
    assert any(k == "photo" and v.endswith("test.png") for k, v in sent), sent
    assert policy.read_journal(1)[-1]["action"] == "screenshot"
    p.tg_command("что на пк")
    sent = [p.tg_out.get_nowait() for _ in range(p.tg_out.qsize())]
    assert any("ПК" in v for _, v in sent), sent
    p.tg_command("сколько будет 2+2")
    assert any("4" in x[1] for x in iter(lambda: p.tg_out.get_nowait() if not p.tg_out.empty() else None, None))
    p.tg_until = 0
    p.alert_on = None
    p.on_alert(False); p.on_alert(True)
    assert "тревога" in p.bubble.l.cget("text")
    p.on_alert(False)
    assert "Отбой" in p.bubble.l.cget("text")
    while not p.tg_out.empty():
        p.tg_out.get_nowait()
    anim0 = p.prefs.get("anim")
    p.send("режим кино")
    assert p.prefs["anim"] == "min" and p.prefs["working"]
    p.send("кино всё")
    assert p.prefs.get("anim") == anim0
    p.send("профиль игра")
    assert p.prefs["game_mode"] == "corner"
    p.undo()
    p.prefs["working"] = False
    p.catalog().destroy(); p.whats_new().destroy()
    assert p.prefs["seen_version"] == upd.VERSION
    assert p.link_command("что ты умеешь") and p.link_command("импорт настроек") and p.link_command("профиль ночь")
    # игра на весь экран: прячется и дальше работает; ошибка в кадре не роняет
    p.fullscreen_app = lambda: True
    run(1.5)
    assert p.gaming and not p.root.winfo_viewable()
    p.send("сделай громче")
    assert ("keys", 0xAF, 5) in rec.calls or p.jobs or p.job
    p.fullscreen_app = lambda: False
    run(1.5)
    assert not p.gaming
    real_draw, p.draw = p.draw, lambda: 1 / 0
    p.tick()
    p.draw = real_draw
    assert p.errors >= 1
    assert want_model() in OLLAMA_MODELS and pick_model(["llama3:8b", "qwen2.5:3b-instruct"]) == "qwen2.5:3b-instruct"
    p.stats.poll(); p.stats.poll_slow()
    assert "ЦП" in p.stats.summary() and isinstance(list_windows(), list) and isinstance(platforms(), list)
    p.open_input(); p.close_input()
    assert p.L <= p.x <= p.R - W and p.y <= p.B - H, (p.x, p.y)
    p.save()
    shutil.rmtree(tmp_dir, ignore_errors=True)
    for f in (common.STATE, apps.LEARNED, apps.APPS_CACHE, pet_tasks.REMINDERS, pet_tasks.NOTES, pet_smart.MEMORY,
              pet_smart.DAY, pet_smart.DIARY, pet_smart.FRESH, policy.POLICY_FILE, policy.JOURNAL):
        if os.path.exists(f):
            os.remove(f)
    root.destroy()
    print("ok")
