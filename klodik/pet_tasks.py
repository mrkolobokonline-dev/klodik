"""Дела: напоминания по дате (сохраняются на диск), список дел с окном, калькулятор, переводчик."""
from .common import *  # noqa: F401,F403
from .apps import *  # noqa: F401,F403
from .winapi import *  # noqa: F401,F403
from .monitor import *  # noqa: F401,F403
from .brain import *  # noqa: F401,F403
from .voice import *  # noqa: F401,F403
from .sprites import *  # noqa: F401,F403
from .tasks import calc, fmt_when, parse_when

REMINDERS = os.path.join(DATA_DIR, "reminders.json")
NOTES = os.path.join(DATA_DIR, "notes.json")
LANGS = {"англ": "английский", "немец": "немецкий", "француз": "французский", "испан": "испанский",
         "итальян": "итальянский", "украин": "украинский", "польск": "польский", "китай": "китайский",
         "япон": "японский", "турец": "турецкий", "корей": "корейский"}


def read_json(path, default):
    try:
        return json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return default


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


class PetTasks:
    def now(s):
        return time.time()

    # --- напоминания и таймеры (одно и то же: момент + о чём) ---
    def tasks_load(s):
        s.reminders = sorted(read_json(REMINDERS, []), key=lambda r: r["t"])
        s.notes = read_json(NOTES, [])
        s.notes_win = None
        missed = [r for r in s.reminders if r["t"] < s.now() - 60]       # пока комп был выключен
        if missed:
            s.reminders = [r for r in s.reminders if r not in missed]
            write_json(REMINDERS, s.reminders)
            text = "; ".join(f"{r['text'] or 'таймер'} ({time.strftime('%d.%m %H:%M', time.localtime(r['t']))})" for r in missed)
            s.root.after(6000, lambda: s.say(f"Пока тебя не было, пропустил напоминания: {text}", 12, speak=True))

    def add_reminder(s, ts, note):
        s.reminders = sorted(s.reminders + [{"t": ts, "text": note}], key=lambda r: r["t"])
        write_json(REMINDERS, s.reminders)
        when = fmt_when(ts, s.now())
        s.say(f"Напомню {when}" + (f": {note}" if note else "") + "!", 4)

    def add_timer(s, secs, note):                         # старое имя — для совместимости
        s.add_reminder(s.now() + secs, note)

    def timer_left(s):
        if not s.reminders:
            return s.say("Напоминаний нет", 2)
        now = s.now()
        s.say("\n".join(f"⏰ {fmt_when(r['t'], now)}" + (f" — {r['text']}" if r["text"] else "") for r in s.reminders[:8]), 8)

    def cancel_timers(s, what=""):
        """«отмени напоминание про маму» — одно, «отмени напоминания/таймеры» — все."""
        what = re.sub(r"^(?:про|о|об)\s+", "", what.strip())
        if what:                                          # «про маму» ≈ «позвонить маме»: каждое слово похоже на какое-то
            hit = [r for r in s.reminders if what in r["text"].lower() or
                   all(any(match(q, w) >= 0.7 for w in r["text"].lower().split()) for q in what.split())]
        else:
            hit = list(s.reminders)
        s.reminders = [r for r in s.reminders if r not in hit]
        write_json(REMINDERS, s.reminders)
        if s.state == "alarm":
            s.stop_alarm()
        s.say(f"Отменил: {len(hit)}" if hit else "Таких напоминаний нет", 2)

    def check_reminders(s):
        now = s.now()
        due = [r for r in s.reminders if r["t"] <= now]
        if due:
            s.reminders = [r for r in s.reminders if r not in due]
            write_json(REMINDERS, s.reminders)
            s.ring("; ".join(r["text"] for r in due if r["text"]))

    # --- список дел ---
    def note_add(s, text):
        text = text.strip(" .,")
        if not text:
            return s.say("А что записать?", 2)
        s.notes.append(text)
        write_json(NOTES, s.notes)
        s.say(f"Записал: {text}. В списке {len(s.notes)}.", 3)
        s.notes_refresh()

    def note_list(s):
        if not s.notes:
            return s.say("Список пуст", 2)
        s.say("\n".join(f"{i}. {n}" for i, n in enumerate(s.notes, 1)), 10)

    def find_note(s, q):
        q = q.strip(" .,")
        if q.isdigit() and 1 <= int(q) <= len(s.notes):
            return int(q) - 1
        best = max(range(len(s.notes)), key=lambda i: match(q, s.notes[i]), default=None)
        return best if best is not None and (q in s.notes[best].lower() or match(q, s.notes[best]) >= 0.6) else None

    def note_done(s, q):
        i = s.find_note(q)
        if i is None:
            return s.say(f"В списке нет «{q}»", 2)
        done = s.notes.pop(i)
        write_json(NOTES, s.notes)
        s.say(f"Вычеркнул: {done}", 2)
        s.notes_refresh()

    def note_clear(s):
        s.notes = []
        write_json(NOTES, s.notes)
        s.say("Список очищен", 2)
        s.notes_refresh()

    def notes_window(s):
        if s.notes_win and s.notes_win.winfo_exists():
            return s.notes_win.lift()
        w = s.notes_win = tk.Toplevel(s.root)
        w.title("Список дел Клодика")
        w.configure(bg=PAPER, padx=14, pady=12)
        w.attributes("-topmost", True)
        s.notes_box = tk.Frame(w, bg=PAPER)
        s.notes_box.pack(fill="both")
        row = tk.Frame(w, bg=PAPER)
        row.pack(fill="x", pady=(8, 0))
        e = tk.Entry(row, width=34, font=("Segoe UI", 10))
        e.pack(side="left", padx=(0, 6))
        add = lambda ev=None: (s.note_add(e.get()), e.delete(0, "end"))
        e.bind("<Return>", add)
        tk.Button(row, text="Добавить", command=add, relief="flat", bg=ORANGE, fg="white").pack(side="left")
        s.notes_refresh()

    def notes_refresh(s):
        if not (s.notes_win and s.notes_win.winfo_exists()):
            return
        for c in s.notes_box.winfo_children():
            c.destroy()
        if not s.notes:
            tk.Label(s.notes_box, text="Пока пусто. Скажи «запиши купить хлеб».", bg=PAPER, fg=DARK,
                     font=("Segoe UI", 10)).pack(anchor="w")
        for i, n in enumerate(s.notes):
            tk.Checkbutton(s.notes_box, text=n, bg=PAPER, font=("Segoe UI", 11), anchor="w",
                           command=lambda i=i: s.root.after(300, lambda: s.note_done(str(i + 1)))).pack(fill="x", anchor="w")

    # --- калькулятор и переводчик ---
    def calc_say(s, answer):
        s.say(answer.replace("**", "^"), 8, speak=True)

    def translate(s, phrase, lang):
        s.ask_ai(f"Переведи на {lang} язык: «{phrase}». Ответь одной строкой: перевод, а в скобках — как это "
                 f"произносится русскими буквами. Без пояснений.", remember=False)

    def task_command(s, seg):
        """Команды дел → функция, которую выполнить, или None, если это не про дела."""
        if m := re.search(r"(?:отмени|убери|сбрось|удали|выключи|останови)\s+(?:все\s+)?(?:таймер|будильник|напоминани)\w*\s*(.*)", seg):
            return lambda w=m[1]: s.cancel_timers(w)
        if re.search(r"сколько осталось|какие (?:у меня )?(?:напоминани|таймер)|что (?:у меня )?запланировано", seg):
            return s.timer_left
        if re.search(r"засеки|таймер|напомни|будильник|разбуди|^через", seg):
            ts, note = parse_when(seg, s.now())
            if ts:
                return lambda: s.add_reminder(ts, note)
        if re.search(r"(?:открой|покажи)\s+(?:мой\s+)?список(?:\s+дел)?\s*$|окно списка", seg):
            return s.notes_window
        if re.search(r"(?:что|прочитай|зачитай)\s+(?:у меня\s+)?(?:в\s+)?(?:списке|заметках|делах)|^список дел$|мои дела", seg):
            return s.note_list
        if re.search(r"очисти\s+список|удали\s+все\s+заметки", seg):
            return s.note_clear
        if (m := re.match(r"^(?:вычеркни|удали|убери)\s+(?:из\s+списка\s+)?(?:пункт\s+)?(.+)", seg)) and s.notes \
                and s.find_note(m[1]) is not None:
            return lambda q=m[1]: s.note_done(q)
        if m := re.match(r"^(?:запиши|добавь в список|добавь в дела|заметка|запомни)\s*:?\s*(.+)", seg):
            return lambda t=m[1]: s.note_add(t)
        if (r := calc(seg)) is not None:
            return lambda: s.calc_say(r)
        m = re.match(r"^(?:как\s+)?(?:будет\s+|сказать\s+)?(.+?)\s+по-?\s?(" + "|".join(LANGS) + r")\w*$", seg) or \
            re.match(r"^переведи\s+(.+?)\s+на\s+(" + "|".join(LANGS) + r")\w*", seg)
        if m:
            return lambda p=m[1], l=LANGS[m[2]]: s.translate(p, l)
        return None
