"""Комп: режимы-сценарии, работа с буфером (ИИ), файлы и папки, системные команды с переспросом «точно?»."""
from .common import *  # noqa: F401,F403
from .apps import *  # noqa: F401,F403
from .winapi import *  # noqa: F401,F403
from .monitor import *  # noqa: F401,F403
from .brain import *  # noqa: F401,F403
from .voice import *  # noqa: F401,F403
from .sprites import *  # noqa: F401,F403
from .pet_tasks import read_json, write_json

MODES = os.path.join(DATA_DIR, "modes.json")
DEFAULT_MODES = {"игр": "открой steam, открой discord", "работ": "открой chrome"}
HOME = os.environ.get("USERPROFILE", "")
FOLDERS = {"загрузк": os.path.join(HOME, "Downloads"), "документ": 0x05, "рабоч": 0x10, "изображени": 0x27,
           "картинк": 0x27, "фото": 0x27, "видео": 0x0E, "музык": 0x0D}
YES = re.compile(r"^(?:да|ага|угу|точно|давай|подтверждаю|конечно|делай)\b")
NO = re.compile(r"^(?:нет|не надо|отмена|отмени|стоп|не)\b")
CLIP_TASKS = {"переведи": "Переведи этот текст (на русский, если он не на русском; иначе на английский). Только перевод:",
              "сократи": "Сократи этот текст в 2–3 раза, сохранив смысл. Только результат:",
              "исправь": "Исправь ошибки и опечатки в этом тексте, ничего больше не меняя. Только исправленный текст:",
              "объясни": "Объясни простыми словами, о чём этот текст, в 2–3 предложениях:",
              "перескажи": "Перескажи этот текст в 2–3 предложениях:"}
SKIP_DIRS = {"appdata", "node_modules", ".git", "$recycle.bin", "__pycache__", ".venv", "venv"}


def folder_path(v):
    return v if isinstance(v, str) else special_dir(v)


def user_dirs():
    """Мои папки — и «системные» (их OneDrive может перенести), и обычные в профиле."""
    extra = [os.path.join(HOME, n) for n in ("Documents", "Desktop", "Pictures", "OneDrive")]
    return [p for p in dict.fromkeys([folder_path(v) for v in FOLDERS.values()] + extra) if p and os.path.isdir(p)]


def find_files(q, roots=None, limit=5, budget=200000):
    """Файлы и папки, в имени которых есть все слова запроса (с учётом кириллица/латиница). Свежие — выше."""
    words = [w for w in q.lower().split() if len(w) > 1]
    if not words:
        return []
    tw = [tr(w) for w in words]
    hits, seen = [], 0
    for root in roots or user_dirs():
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d.lower() not in SKIP_DIRS and not d.startswith(".")]
            for name in filenames + dirnames:
                seen += 1
                low = os.path.splitext(name)[0].lower()
                if all(w in low for w in words) or all(t in tr(low) for t in tw):
                    p = os.path.join(dirpath, name)
                    try:
                        hits.append((low == q.lower(), os.path.getmtime(p), p))
                    except OSError:
                        pass
            if seen > budget:                              # не сканируем весь диск бесконечно
                break
    return [p for _, _, p in sorted(hits, reverse=True)[:limit]]


def newest(folder):
    try:
        files = [os.path.join(folder, f) for f in os.listdir(folder)]
        files = [f for f in files if os.path.isfile(f) and not f.lower().endswith((".tmp", ".crdownload", ".part"))]
        return max(files, key=os.path.getmtime) if files else None
    except OSError:
        return None


def dir_size(path, budget=[0]):
    total = 0
    try:
        for e in os.scandir(path):
            try:
                if e.is_symlink():
                    continue
                total += dir_size(e.path) if e.is_dir() else e.stat().st_size
            except OSError:
                pass
    except OSError:
        pass
    return total


class PetPC:
    def pc_load(s):
        s.modes = read_json(MODES, {}) or dict(DEFAULT_MODES)
        s.confirm = None                                  # (вопрос, что сделать, до какого времени)

    # --- переспрос «точно?» для опасного ---
    def ask_confirm(s, question, fn):
        s.confirm = (question, fn, s.clock + 20)
        s.say(question + " Скажи «да» или «нет».", 20, speak=True)

    def answer_confirm(s, text):
        """Ответ на «точно?» → True, если это был ответ."""
        if not s.confirm or s.clock > s.confirm[2]:
            s.confirm = None
            return False
        t = text.lower().strip()
        if YES.match(t):
            fn, s.confirm = s.confirm[1], None
            fn()
            return True
        if NO.match(t):
            s.confirm = None
            s.say("Ок, не буду.", 2)
            return True
        return False

    # --- режимы ---
    def find_mode(s, name):
        name = name.lower().strip()
        return next((k for k in s.modes if name.startswith(k) or k.startswith(name[:4]) or match(name, k) > 0.75), None)

    def save_mode(s, name, cmds):
        key = re.sub(r"(?:ы|а|у|ой|ов|ам|ами)$", "", name.lower().strip()) or name.lower()
        s.modes[key] = cmds.strip(" .,")
        write_json(MODES, s.modes)
        s.say(f"Запомнил режим «{name}»: {s.modes[key]}. Скажи «режим {name}».", 5, speak=True)

    def run_mode(s, name):
        k = s.find_mode(name)
        if not k:
            return s.say(f"Режима «{name}» нет. Создай: «запомни режим {name}: открой …»", 4, speak=True)
        s.say(f"Режим «{name}»!", 2, speak=True)
        s.local_command(s.modes[k])

    def list_modes(s):
        s.say("Режимы:\n" + "\n".join(f"• {k}…: {v}" for k, v in s.modes.items()), 10)

    def delete_mode(s, name):
        k = s.find_mode(name)
        if k:
            del s.modes[k]
            write_json(MODES, s.modes)
        s.say(f"Удалил режим «{name}»" if k else f"Режима «{name}» нет", 2)

    # --- буфер обмена: ИИ над скопированным текстом ---
    def clip_task(s, verb):
        try:
            text = s.root.clipboard_get().strip()
        except tk.TclError:
            text = ""
        if not text:
            return s.say("В буфере пусто. Скопируй текст (Ctrl+C) и попроси ещё раз.", 4, speak=True)
        s.say("Сейчас поработаю с текстом…", 2)
        s.thinking = True

        def go():
            try:
                out = s.llm("Ты помощник. Пиши по-русски, без вступлений и пояснений.",
                            f"{CLIP_TASKS[verb]}\n\n{text[:6000]}", 1200)
                s.answers.put(("clip_" + ("say" if verb in ("объясни", "перескажи") else "copy"),
                               out or "Мозги не ответили — проверь, что выбран «ИИ на компе»."))
            except (OSError, ValueError, KeyError) as e:
                s.answers.put(("err", str(e)))
        threading.Thread(target=go, daemon=True).start()

    def clip_result(s, kind, text):
        s.thinking = False
        s.state, s.timer = "idle", 1.0
        if kind == "clip_copy":
            s.root.clipboard_clear()
            s.root.clipboard_append(text)
            s.say(f"Готово, результат в буфере — вставь Ctrl+V.\n{text[:200]}{'…' if len(text) > 200 else ''}", 8,
                  speak=False)
            if s.tts_on:
                s.speaker.say("Готово, результат в буфере.")
        else:
            s.say(text, 15, speak=True)

    # --- файлы и папки ---
    def open_path(s, p, what):
        s.fx.start(p)
        s.say(f"Открываю {what}", 2)

    def find_file(s, q, open_it):
        s.say(f"Ищу «{q}»…", 3)

        def go():
            s.answers.put(("files", json.dumps({"q": q, "open": open_it, "hits": find_files(q)}, ensure_ascii=False)))
        threading.Thread(target=go, daemon=True).start()

    def files_result(s, payload):
        d = json.loads(payload)
        hits = d["hits"]
        if not hits:
            return s.say(f"Не нашёл «{d['q']}» в твоих папках", 3, speak=True)
        if d["open"]:
            s.open_path(hits[0], os.path.basename(hits[0]))
        s.found = hits
        s.say("Нашёл:\n" + "\n".join(f"{i}. {os.path.basename(p)}" for i, p in enumerate(hits, 1))
              + ("" if d["open"] else "\nСкажи «открой первый»."), 10)

    def open_found(s, n):
        hits = getattr(s, "found", [])
        if not 1 <= n <= len(hits):
            return s.say("Сначала скажи «найди файл …»", 2)
        s.open_path(hits[n - 1], os.path.basename(hits[n - 1]))

    def space_report(s):
        s.say("Считаю, что занимает место… (минутку)", 4)

        def go():
            sizes = []
            for e in os.scandir(HOME):
                if e.is_dir() and not e.name.startswith("."):
                    sizes.append((dir_size(e.path), e.name))
            sizes.sort(reverse=True)
            free = shutil.disk_usage("C:\\").free / 2**30
            s.answers.put(("info", f"Больше всего места в твоей папке занимают:\n" +
                           "\n".join(f"• {n} — {b / 2**30:.1f} ГБ" for b, n in sizes[:5]) + f"\nНа диске C свободно {free:.0f} ГБ."))
        threading.Thread(target=go, daemon=True).start()

    # --- система ---
    def type_text(s, text):
        s.root.clipboard_clear()
        s.root.clipboard_append(text)
        s.root.after(250, s.fx.paste)                      # вставка в окно, где сейчас курсор
        s.say(f"Печатаю: {text[:60]}", 2)

    def pc_command(s, seg):
        """Команды компа → функция или None."""
        if m := re.match(r"^(?:включи\s+|запусти\s+|давай\s+)?режим\s+(\w+)$", seg):
            return lambda n=m[1]: s.run_mode(n)
        if re.search(r"какие (?:у меня )?режимы|список режимов", seg):
            return s.list_modes
        if m := re.match(r"^удали\s+режим\s+(\w+)", seg):
            return lambda n=m[1]: s.delete_mode(n)
        for verb in CLIP_TASKS:
            if re.search(rf"^{verb}\w*\s+(?:то\s+)?(?:что\s+)?(?:я\s+)?(?:скопировал|скопированн|из буфера|буфер|текст)", seg):
                return lambda v=verb: s.clip_task(v)
        if re.search(r"(?:открой|покажи)\s+(?:последн\w+\s+(?:загрузк|скачанн)|что\s+я\s+скачал)", seg):
            return lambda: (lambda p: s.open_path(p, os.path.basename(p)) if p else s.say("В загрузках пусто", 2))(
                newest(folder_path(FOLDERS["загрузк"])))
        if m := re.match(r"^(?:открой|покажи)\s+(?:папку\s+)?(" + "|".join(FOLDERS) + r")\w*$", seg):
            return lambda k=m[1]: s.open_path(folder_path(FOLDERS[k]), "папку")
        if m := re.match(r"^(?:найди|поищи|где)\s+(?:мой\s+)?(?:файл|папку|документ|фото)\s+(.+)", seg):
            return lambda q=m[1]: s.find_file(q, False)
        if m := re.match(r"^открой\s+файл\s+(.+)", seg):
            return lambda q=m[1]: s.find_file(q, True)
        if m := re.match(r"^открой\s+(первый|второй|третий|четв[её]ртый|пятый)$", seg):
            return lambda n=["первый", "второй", "третий", "четвертый", "пятый"].index(m[1].replace("ё", "е")) + 1: s.open_found(n)
        if re.search(r"что\s+(?:жр[её]т|занимает)\s+(?:всё\s+)?место|куда делось место", seg):
            return s.space_report
        if re.search(r"^(?:заблокируй|блокировка|запри)\b", seg):
            return lambda: s.gate("lock", "заблокировать экран", lambda: (
                s.log("lock", "экран", "сделано"), s.say("Блокирую. Пока!", 1, speak=True), s.root.after(800, s.fx.lock)))
        if re.search(r"отмени\s+(?:выключение|перезагрузку)", seg):
            return lambda: (s.fx.abort_shutdown(), s.log("abort_shutdown", "", "сделано"),
                            s.say("Выключение отменил", 2, speak=True))
        if m := re.search(r"(выключи|перезагрузи)\s+(?:комп\w*|пк|систему)(?:\s+через\s+(\d+)\s+(мин\w*|час\w*))?", seg):
            secs = int(m[2]) * (3600 if m[3] and m[3].startswith("час") else 60) if m[2] else 30
            restart = m[1].startswith("перезагр")
            word = "перезагрузить" if restart else "выключить"

            def go():
                s.fx.shutdown(secs, restart)
                s.push_undo("выключение", s.fx.abort_shutdown)
                s.say(f"Ок, {'перезагрузка' if restart else 'выключение'} через {fmt_secs(secs)}. "
                      "Передумаешь — «отмени выключение».", 5, speak=True)
            return lambda: s.gate("restart" if restart else "shutdown",
                                  f"{word} компьютер через {fmt_secs(secs)} (несохранённое пропадёт)", go)
        if re.search(r"усыпи\s+комп|спящий режим|отправь\s+комп\w*\s+в\s+сон", seg):
            return lambda: s.gate("sleep", "усыпить компьютер", s.fx.sleep_pc)
        return None
