"""Безопасность (раздел 3): каждое действие проходит политику, пишется в журнал с причиной;
«Стоп» прерывает всё; «верни как было» откатывает последнее обратимое действие."""
from .common import *  # noqa: F401,F403
from .apps import *  # noqa: F401,F403
from .winapi import *  # noqa: F401,F403
from .monitor import *  # noqa: F401,F403
from .brain import *  # noqa: F401,F403
from .voice import *  # noqa: F401,F403
from .sprites import *  # noqa: F401,F403
from .policy import LEVELS, decide, journal, load_policy, read_journal


class PetSafety:
    def safety_load(s):
        s.policy = load_policy()
        s.access_level = getattr(s, "access_level", None) or s.policy.get("default_level", "assistant")
        s.undo_stack, s.undoing = [], False
        s.request = ("", "сам")                            # последняя просьба: текст и откуда (голос/текст/меню)
        s.pin = getattr(s, "pin", "")

    # --- политика ---
    def decide(s, action):
        return decide(s.policy, s.access_level, action)

    def log(s, action, target, result):
        journal(action, target, s.request[1], s.request[0], result)

    def gate(s, action, what, fn):
        """Пропустить действие через политику. what — по-человечески, что будет сделано."""
        d = s.decide(action)
        if d == "auto":
            return fn()
        if d == "forbidden":
            s.log(action, what, "запрещено политикой")
            return s.say(f"Это я не делаю никогда: {what}. Так записано в политике безопасности "
                         f"(%APPDATA%\\Klodik\\policy.json).", 6, speak=True)
        if d == "advise":
            s.log(action, what, "подсказал (Советник)")
            return s.say(f"Я бы сделал так: {what}. Сейчас я Советник — сделай сам или переключи меня на «Помощника».",
                         6, speak=True)
        if d == "double":
            return s.ask_confirm(f"Важное действие: {what}. Точно?", lambda: s.ask_second(action, what, fn))
        s.ask_confirm(f"Сделать: {what}?", lambda: s.run_logged(action, what, fn))

    def ask_second(s, action, what, fn):
        """Двойное подтверждение: после «да» ещё фраза «подтверждаю» (или PIN, если задан)."""
        need = s.pin or "подтверждаю"
        s.second = (need, lambda: s.run_logged(action, what, fn), s.clock + 30)
        s.say(f"Второе подтверждение: скажи «{need}».", 30, speak=True)

    def check_second(s, text):
        sec = getattr(s, "second", None)
        if not sec or s.clock > sec[2]:
            s.second = None
            return False
        s.second = None
        if sec[0] in text.lower():
            sec[1]()
        else:
            s.say("Не подтверждено — ничего не делаю.", 3, speak=True)
        return True

    def run_logged(s, action, what, fn):
        try:
            r = fn()
            s.log(action, what, "сделано")
            return r
        except Exception as e:  # действие не вышло — запишем и скажем, не роняя Клодика
            s.log(action, what, f"ошибка: {e}")
            s.say(f"Не вышло: {e}", 4, speak=True)

    def set_level(s, level):
        s.access_level = level
        if hasattr(s, "level_var"):
            s.level_var.set(level)
        s.save()
        s.log("access_level", level, "сделано")
        s.say(f"Уровень доступа: {LEVELS[level]}", 3, speak=True)

    # --- откат ---
    def push_undo(s, label, fn):
        if not s.undoing:
            s.undo_stack = (s.undo_stack + [(label, fn)])[-20:]

    def undo(s):
        if not s.undo_stack:
            return s.say("Нечего откатывать — последние действия необратимы или их не было.", 3, speak=True)
        label, fn = s.undo_stack.pop()
        s.undoing = True
        try:
            fn()
            s.log("undo", label, "откатил")
            s.say(f"Вернул как было: {label}", 3, speak=True)
        except Exception as e:  # окно уже закрыто и т. п.
            s.say(f"Откатить не вышло: {e}", 3)
        finally:
            s.undoing = False

    # --- «Стоп» ---
    def stop_all(s):
        """Немедленно прервать всё: задания, бульдозер, речь, игру, ожидание ответа ИИ, вопросы."""
        s.jobs, s.job = [], None
        if s.dozer:
            s.dozer.destroy()
            s.dozer = s.dz = None
            s.x, s.y, s.vy = float(s.R - W - 60), float(s.T + 40), 0.0
        s.speaker.hush()
        if s.game:
            for c in s.game.get("cookies", []):
                c.destroy()
            s.game = None
        s.confirm = s.second = None
        s.thinking = False
        s.ignore_ai_until = s.clock + 180                  # поздний ответ ИИ после «Стоп» не нужен
        if s.state in ("job", "dozer", "dozer_out", "alarm", "photo", "dance"):
            s.state, s.timer, s.carry = "idle", 2, None
        s.log("stop", "всё", "остановил")
        s.say("Стоп! Всё остановил.", 2)

    # --- журнал ---
    def journal_window(s):
        w = tk.Toplevel(s.root)
        w.title("Журнал действий Клодика")
        w.attributes("-topmost", True)
        w.configure(bg=PAPER, padx=10, pady=10)
        tk.Label(w, text="Что Клодик делал, по чьей просьбе и чем кончилось (последние 200):", bg=PAPER,
                 fg=INK, font=("Segoe UI", 10, "bold")).pack(anchor="w")
        box = tk.Listbox(w, width=120, height=24, font=("Consolas", 9))
        box.pack(fill="both", expand=True, pady=(6, 0))
        for e in reversed(read_journal()):
            box.insert("end", f"{e['t']}  {e['action']:<14} {e['target'][:40]:<40} {e['result'][:24]:<24} "
                              f"[{e['by']}] {e['reason'][:50]}")
        return w

    def safety_command(s, seg):
        if re.match(r"^(?:стоп|стой|остановись|хватит всё|отмена всего|прекрати)$", seg):
            return s.stop_all
        if re.search(r"верни как было|откати|отмени последн", seg):
            return s.undo
        if re.search(r"(?:покажи|открой)\s+журнал|что ты делал", seg):
            return s.journal_window
        if m := re.search(r"(?:уровень|доступ)\w*\s+(советник|помощник|автопилот)|стань\s+(советником|помощником|автопилотом)", seg):
            lv = {"сов": "advisor", "пом": "assistant", "авт": "autopilot"}[(m[1] or m[2])[:3]]
            return lambda: s.set_level(lv)
        return None
