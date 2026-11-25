"""Мозг (раздел 4): понять → контекст → план из шагов (с «почему») → проверить права → выполнить инструментами →
проверить результат → журнал. Плюс: правила из поправок («так не делай»), отклонённые подсказки, база
«проблема → решение», недельный отчёт и плагины (пишет сам, сначала песочница, ставит после «да»)."""
from .common import *  # noqa: F401,F403
from .apps import *  # noqa: F401,F403
from .winapi import *  # noqa: F401,F403
from .monitor import *  # noqa: F401,F403
from .ai import parse_json
from .pet_tasks import read_json, write_json
from .policy import read_journal
from . import tools as T

RULES = os.path.join(DATA_DIR, "rules.json")
KB = os.path.join(DATA_DIR, "kb.json")
WEEKLY = os.path.join(DATA_DIR, "weekly")
PLUGINS = os.path.join(DATA_DIR, "plugins")
TASK_WORDS = re.compile(r"^(?:сделай|настрой|поменяй|поставь|установи|удали программу|почисти|очисти|проверь|ускорь|"
                        r"оптимизируй|исправь|почини|переключи|убавь|прибавь|включи тёмную|включи светлую|"
                        r"включи режим|смени тему|яркость|громкость на|что с интернетом|почему|не работает)", re.I)
PROBLEM = re.compile(r"почини|исправь|не работает|тормоз|глюч|ошибк|пропал|сломал", re.I)
PLAN_SYS = "Ты планировщик действий Клодика (помощника на Windows). Отвечай только JSON, по-русски."


class PetBrain:
    def brain_load(s):
        s.rules = read_json(RULES, [])
        s.kb = read_json(KB, [])
        s.plan_now = None
        s.last_hint = None
        s.plugins = s.load_plugins()

    # --- план ---
    def context(s):
        h = u32.GetForegroundWindow()
        n = u32.GetWindowTextLengthW(h)
        buf = ctypes.create_unicode_buffer(n + 1)
        u32.GetWindowTextW(h, buf, n + 1)
        pid = wt.DWORD()
        u32.GetWindowThreadProcessId(h, ctypes.byref(pid))
        recent = "; ".join(f"{e['action']} {e['target'][:30]} → {e['result'][:20]}" for e in read_journal(6))
        return f"активное окно «{buf.value[:60]}» ({proc_name(pid.value)}); недавно: {recent or 'ничего'}; ПК: {s.stats.summary()}"

    def plan_task(s, text):
        """Сложная просьба → план от ИИ (без личного в облако) → показать → подтвердить → выполнить."""
        tools = "\n".join(f"- {k}: {v[1]}" for k, v in T.TOOLS.items())
        similar = [k for k in s.kb if match(text, k["problem"]) > 0.6][:3]
        cloud = s.ai.can_cloud()
        prompt = (f"Просьба владельца: «{text}»\n"
                  + ("" if cloud else f"Контекст: {s.context()}\n")        # контекст ПК — только локальной модели
                  + f"Инструменты:\n{tools}\n"
                  + (f"Правила владельца (нарушать нельзя): {'; '.join(r['text'] for r in s.rules)}\n" if s.rules else "")
                  + (f"Раньше помогло: {json.dumps(similar, ensure_ascii=False)}\n" if similar else "")
                  + "Верни JSON: {\"say\": \"коротко, что сделаешь\", \"steps\": [{\"tool\": \"имя\", \"args\": {...}, "
                    "\"why\": \"зачем, простыми словами\"}]}. Максимум 5 шагов. Только инструменты из списка. Если "
                    "подходящего нет — steps: [] и в say совет, как сделать вручную. Ничего не выдумывай.")
        s.thinking, s.state, s.timer = True, "idle", 10**6
        s.say("Думаю, как это сделать…", 3)

        def go():
            try:
                d = parse_json(s.ai.ask(PLAN_SYS, prompt, task="plan", private=False, want_json=True, tokens=700))
                s.answers.put(("plan", json.dumps({"text": text, **d}, ensure_ascii=False)))
            except Exception as e:  # нет мозгов/сети — скажем, а не упадём
                s.answers.put(("err", str(e)))
        threading.Thread(target=go, daemon=True).start()

    def plan_ready(s, payload):
        s.thinking = False
        s.state, s.timer = "idle", 2
        d = json.loads(payload)
        steps = [st for st in d.get("steps", []) if isinstance(st, dict) and st.get("tool") in T.TOOLS][:5]
        blocked = [st for st in steps if s.rule_blocks(st)]
        steps = [st for st in steps if st not in blocked]
        if not steps:
            s.emote("doubt", "light")
            return s.say(d.get("say") or "Не знаю, как это сделать своими инструментами.", 8, speak=True)
        decisions = [s.decide(T.tool_action(st["tool"], st.get("args", {}))) for st in steps]
        if "forbidden" in decisions:
            s.log("plan", d["text"], "запрещено политикой")
            return s.say("В плане есть то, что я не делаю никогда (политика безопасности). Не буду.", 6, speak=True)
        where = "☁ " if s.ai.where == "cloud" else "⌂ "
        lines = [f"{i}. {st.get('why') or st['tool']}" for i, st in enumerate(steps, 1)]
        if blocked:
            lines.append(f"(пропустил {len(blocked)} шаг — ты просил так не делать)")
        s.plan_now = {"text": d["text"], "steps": steps}
        s.say(where + (d.get("say") or "План:") + "\n" + "\n".join(lines), 15, speak=False)
        if s.tts_on:
            s.speaker.say(d.get("say") or "Вот план.")
        if "advise" in decisions:
            return s.say(where + "План (я Советник — сделай сам):\n" + "\n".join(lines), 15)
        if all(x == "auto" for x in decisions):
            return s.run_plan()
        if "double" in decisions:
            return s.ask_confirm("В плане важные шаги. Выполнить?", lambda: s.ask_second("plan", d["text"], s.run_plan))
        s.ask_confirm("Выполнить план?", s.run_plan)

    def run_plan(s):
        p = s.plan_now
        if not p:
            return
        s.say("Выполняю…", 2)

        def go():
            ok_all = True
            for i, st in enumerate(p["steps"], 1):
                try:
                    msg = s.exec_tool(st["tool"], st.get("args", {}))
                    s.answers.put(("plan_step", f"✓ {i}. {msg}"))
                    s.log(st["tool"], json.dumps(st.get("args", {}), ensure_ascii=False)[:80], f"сделано: {msg}"[:100])
                except Exception as e:  # шаг не вышел — останавливаемся и объясняем
                    ok_all = False
                    s.log(st["tool"], json.dumps(st.get("args", {}), ensure_ascii=False)[:80], f"ошибка: {e}")
                    s.answers.put(("plan_step", f"✗ {i}. Не вышло: {e}. Остальное не делаю — скажи, попробовать иначе?"))
                    break
            if ok_all:
                if PROBLEM.search(p["text"]):              # «проблема → решение» на будущее
                    s.kb = (s.kb + [{"problem": p["text"], "steps": p["steps"]}])[-200:]
                    write_json(KB, s.kb)
                s.answers.put(("plan_step", "Готово!"))
        threading.Thread(target=go, daemon=True).start()

    def exec_tool(s, name, a):
        """Выполнить инструмент (в фоне). Возвращает короткий итог; где можно — кладёт откат."""
        if name == "command":
            s.answers.put(("run_cmd", str(a.get("text", ""))))
            return f"команда «{a.get('text', '')}»"
        if name == "set_volume":
            prev = T.get_volume()
            T.set_volume(a.get("percent", 30))
            s.push_undo("громкость", lambda: T.set_volume(prev))
            return f"громкость {int(float(a.get('percent', 30)))}% (было {prev}%)"
        if name == "set_brightness":
            prev = T.get_brightness()
            T.set_brightness(a.get("percent", 60))
            s.push_undo("яркость", lambda: T.set_brightness(prev))
            return f"яркость {a.get('percent')}% (было {prev}%)"
        if name == "power_plan":
            prev = T.get_power_plan()
            T.set_power_plan(a.get("plan", "balanced"))
            if prev:
                s.push_undo("схема питания", lambda: T.set_power_plan(prev))
            return f"схема питания: {a.get('plan')}"
        if name == "theme":
            prev = T.get_theme()
            T.set_theme(a.get("mode", "dark"))
            s.push_undo("тема", lambda: T.set_theme(prev))
            return f"тема: {'тёмная' if a.get('mode') == 'dark' else 'светлая'}"
        if name in ("install_app", "uninstall_app"):
            found = T.winget_find(str(a.get("name", "")))
            if not found:
                raise RuntimeError(f"в winget нет «{a.get('name')}»")
            nm, pid, src = found
            verb = "install" if name == "install_app" else "uninstall"
            r = run_quiet(["winget", verb, "--id", pid, "-e", "--silent", "--accept-source-agreements"]
                          + (["--accept-package-agreements"] if verb == "install" else []), encoding="utf-8",
                          errors="replace", timeout=1800)
            if r.returncode:
                raise RuntimeError((r.stdout or r.stderr or "").strip().splitlines()[-1][:120] if (r.stdout or r.stderr) else "ошибка winget")
            return f"{'поставил' if verb == 'install' else 'удалил'} {nm} ({pid}, источник {src})"
        if name == "list_autostart":
            return "в автозапуске: " + ", ".join(T.autostart()[:25])
        if name == "clean_temp":
            junk = T.temp_junk()
            from .policy import recycle
            n, size = 0, 0
            for path, sz in junk:
                try:
                    recycle(path)
                    n, size = n + 1, size + sz
                except Exception:  # файл занят — пропускаем
                    pass
            return f"убрал в корзину {n} временных файлов ({size / 2**20:.0f} МБ)"
        if name == "internet_check":
            ip, web, ms = T.internet()
            ping = next((x for pair in ms for x in pair if x), "?")
            return ("интернет есть" if web else "сайты не открываются" if ip else "интернета нет") + f", пинг {ping} мс"
        if name == "flush_dns":
            run_quiet(["ipconfig", "/flushdns"], timeout=20)
            return "кэш DNS сброшен"
        if name == "powershell":
            out, err, code = T.ps(str(a.get("command", "")), timeout=120)
            if code:
                raise RuntimeError(err[:150] or "команда не выполнилась")
            return (out or "готово")[:300]
        if name == "pc_summary":
            s.stats.poll()
            return s.stats.summary().replace("\n", "; ")
        raise RuntimeError(f"нет инструмента {name}")

    # --- поправки, отклонённые подсказки ---
    def rule_blocks(s, step):
        return any(r.get("tool") == step["tool"] and (not r.get("target") or r["target"] in json.dumps(step.get("args", {}),
                                                                                                     ensure_ascii=False))
                   for r in s.rules)

    def add_rule(s):
        last = read_journal(1)
        if not last:
            return s.say("А что именно так не делать? Я ещё ничего не делал.", 3)
        e = last[-1]
        s.rules = (s.rules + [{"text": f"не делать: {e['action']} {e['target']}", "tool": e["action"],
                               "target": e["target"][:40], "t": time.time()}])[-50:]
        write_json(RULES, s.rules)
        s.emote("embarrassed", "light")
        s.say(f"Понял, больше так не делаю: {e['action']} {e['target'][:30]}. Правило можно убрать: «забудь правила».",
              5, speak=True)

    def reject_hint(s):
        if s.last_hint and s.clock - s.last_hint[1] < 40:
            rej = set(s.prefs.get("rejected", []))
            rej.add(s.last_hint[0])
            s.prefs["rejected"] = sorted(rej)
            s.save()
            s.last_hint = None
            s.say("Хорошо, больше не предлагаю. Вернуть: «верни предложения».", 3, speak=True)
            return True
        return False

    # --- недельный отчёт ---
    def weekly_report(s, show=True):
        diary = read_json(os.path.join(DATA_DIR, "diary.json"), [])[-7:]
        try:
            errs = [re.sub(r"^\S+ \S+ ", "", l).strip()[:80] for l in open(os.path.join(DATA_DIR, "errors.log"),
                                                                             encoding="utf-8").read().splitlines()]
        except OSError:
            errs = []
        top_err = sorted({e: errs.count(e) for e in errs if e}.items(), key=lambda x: -x[1])[:3]
        fails = s.day.get("fails", [])[-10:]
        facts = (f"дни: {'; '.join(d.get('summary', '') for d in diary)}\nкоманд выполнено: {sum(d.get('cmds', 0) for d in diary)}\n"
                 f"выучил фраз: {sum(d.get('learned', 0) for d in diary)}\nповторяющиеся сбои: {top_err}\n"
                 f"не понял: {fails}\nрешений в базе: {len(s.kb)}")

        def go():
            try:
                out = s.llm("Ты Клодик. Пиши по-русски, коротко, по пунктам.",
                            facts + "\n\nНапиши недельный отчёт: 1) что узнал, 2) что починил/выучил, 3) 2–3 новые функции, "
                                    "которые стоит добавить (по тому, что я не понял), 4) какие сбои повторяются и что с "
                                    "ними сделать.", 600) or facts
            except (OSError, ValueError, KeyError):
                out = facts
            os.makedirs(WEEKLY, exist_ok=True)
            open(os.path.join(WEEKLY, time.strftime("%Y-%m-%d.md")), "w", encoding="utf-8").write(out)
            if show:
                s.answers.put(("info", "Недельный отчёт:\n" + out[:700]))
        threading.Thread(target=go, daemon=True).start()

    # --- плагины ---
    def load_plugins(s):
        out = []
        for d in sorted(os.listdir(PLUGINS)) if os.path.isdir(PLUGINS) else []:
            man = read_json(os.path.join(PLUGINS, d, "plugin.json"), None)
            if man:
                man["dir"] = os.path.join(PLUGINS, d)
                out.append(man)
        return out

    def run_plugin(s, man, text, sandbox=False):
        """Плагин — отдельный процесс (Klodik --plugin), с таймаутом; в песочнице — пустая временная папка и тест-флаг."""
        import tempfile
        cwd = tempfile.mkdtemp(prefix="klodik_sandbox_") if sandbox else man["dir"]
        cmd = [sys.executable] + ([] if FROZEN else [os.path.abspath(sys.argv[0])]) + \
              ["--plugin", os.path.join(man["dir"], "plugin.py"), text]
        env = {k: v for k, v in os.environ.items() if k.upper() in ("SYSTEMROOT", "TEMP", "TMP", "PATH", "USERPROFILE",
                                                                     "APPDATA", "LOCALAPPDATA")}
        env["KLODIK_SANDBOX"] = "1" if sandbox else "0"
        r = run_quiet(cmd, cwd=cwd, env=env, timeout=20, encoding="utf-8", errors="replace")
        return (r.stdout or r.stderr or "").strip()[:500]

    def plugin_for(s, text):
        for man in s.plugins:
            if man.get("enabled", True) and man.get("pattern") and re.search(man["pattern"], text, re.I):
                return man
        return None

    def write_plugin(s, idea):
        """ИИ пишет плагин → окно с кодом и правами → песочница → «Установить» (после «да»)."""
        s.say("Пишу плагин, минутку…", 4)

        def go():
            try:
                d = parse_json(s.ai.ask(
                    "Ты пишешь маленькие плагины-скрипты на Python для помощника Клодика. Только JSON.",
                    f"Задача: {idea}\nВерни JSON: {{\"name\": \"латиницей_без_пробелов\", \"description\": \"…\", "
                    f"\"permissions\": [\"например read_files\", \"network\"], \"pattern\": \"регулярка русской фразы, "
                    f"которая запускает плагин\", \"code\": \"полный код plugin.py: читает фразу из sys.argv[1], печатает "
                    f"ответ в stdout; если os.environ.get('KLODIK_SANDBOX')=='1' — ничего не меняет, только печатает, что "
                    f"сделал бы. Только стандартная библиотека. Ничего не удалять и не отправлять наружу без явной задачи.\"}}",
                    task="code", private=False, want_json=True, tokens=1500))
                s.answers.put(("plugin_draft", json.dumps(d, ensure_ascii=False)))
            except Exception as e:  # модель не ответила
                s.answers.put(("err", str(e)))
        threading.Thread(target=go, daemon=True).start()

    def plugin_draft(s, payload):
        d = json.loads(payload)
        if not d.get("code") or not re.fullmatch(r"[a-z0-9_]{2,40}", str(d.get("name", ""))):
            return s.say("Плагин не получился — попробуй описать задачу проще.", 4, speak=True)
        w = tk.Toplevel(s.root)
        w.title(f"Плагин «{d['name']}»")
        w.attributes("-topmost", True)
        w.configure(bg=PAPER, padx=10, pady=10)
        tk.Label(w, text=f"{d.get('description', '')}\nПрава: {', '.join(d.get('permissions', [])) or 'нет'}\n"
                         f"Запускается фразой: {d.get('pattern')}", bg=PAPER, fg=INK, justify="left",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        t = tk.Text(w, width=100, height=22, font=("Consolas", 9))
        t.insert("1.0", d["code"])
        t.pack(fill="both", expand=True, pady=6)
        out = tk.Label(w, text="", bg=PAPER, fg=DARK, justify="left", wraplength=700)
        out.pack(anchor="w")
        man = {"name": d["name"], "description": d.get("description", ""), "permissions": d.get("permissions", []),
               "pattern": d.get("pattern", ""), "enabled": True, "dir": os.path.join(PLUGINS, d["name"])}

        def save_files():
            os.makedirs(man["dir"], exist_ok=True)
            open(os.path.join(man["dir"], "plugin.py"), "w", encoding="utf-8").write(t.get("1.0", "end"))
            write_json(os.path.join(man["dir"], "plugin.json"), {k: v for k, v in man.items() if k != "dir"})

        def test():
            save_files()
            man["enabled"] = False
            write_json(os.path.join(man["dir"], "plugin.json"), {k: v for k, v in man.items() if k != "dir"})
            out.config(text="Песочница: " + (s.run_plugin(man, "тест", sandbox=True) or "(пусто)"))

        def install():
            def ok():
                save_files()
                man["enabled"] = True
                write_json(os.path.join(man["dir"], "plugin.json"), {k: v for k, v in man.items() if k != "dir"})
                s.plugins = s.load_plugins()
                s.say(f"Плагин «{d['name']}» установлен и включён.", 4, speak=True)
                w.destroy()
            s.gate("plugin_install", f"установить плагин «{d['name']}» (права: {', '.join(man['permissions']) or 'нет'})", ok)
        row = tk.Frame(w, bg=PAPER)
        row.pack(anchor="w")
        tk.Button(row, text="Проверить в песочнице", command=test, relief="flat").pack(side="left", padx=2)
        tk.Button(row, text="Установить", command=install, relief="flat", bg=ORANGE, fg="white").pack(side="left", padx=2)
        tk.Button(row, text="Отмена", command=w.destroy, relief="flat").pack(side="left", padx=2)
        s.say("Вот код плагина — проверь в песочнице и установи, если нравится.", 5, speak=True)

    def brain_command(s, seg, raw):
        if re.search(r"^(?:так не делай|больше так не делай|не делай так)", seg):
            return s.add_rule
        if re.search(r"забудь правила|убери правила", seg):
            return lambda: (s.rules.clear(), write_json(RULES, s.rules), s.say("Правила очищены.", 2))
        if re.search(r"какие (?:у тебя )?правила", seg):
            return lambda: s.say("Правила:\n" + "\n".join(r["text"] for r in s.rules) if s.rules else "Правил нет.", 8)
        if re.search(r"верни предложени", seg):
            return lambda: (s.prefs.pop("rejected", None), s.save(), s.say("Снова буду предлагать.", 2))
        if re.search(r"недельн\w+ отч[её]т|отч[её]т за неделю", seg):
            return s.weekly_report
        if m := re.match(r"^(?:напиши|сделай|создай)\s+плагин\s+(.+)", raw, re.I):
            return lambda i=m[1]: s.write_plugin(i)
        if man := s.plugin_for(raw):
            return lambda: threading.Thread(target=lambda: s.answers.put(("info", s.run_plugin(man, raw) or "…")),
                                            daemon=True).start()
        if re.search(r"(?:только|работай)\s+локально|без облака", seg):
            return lambda: (s.set_pref("local_only", True), s.say("Теперь только локально, без облака.", 3, speak=True))
        if re.search(r"можно (?:в )?облак|разреши облако", seg):
            return lambda: (s.set_pref("local_only", False), s.say("Ок, сложное могу спрашивать у Gemini (без личного).",
                                                                   3, speak=True))
        return None
