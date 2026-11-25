"""Ум: память о тебе, дневник и итоги дня (сам доучивается на своих ошибках), свежие фразы от ИИ,
подсказки «сам предлагает» и утренняя сводка. Всё на компе: ИИ — Ollama, без интернета и токенов."""
import datetime as dt

from .common import *  # noqa: F401,F403
from .apps import *  # noqa: F401,F403
from .winapi import *  # noqa: F401,F403
from .monitor import *  # noqa: F401,F403
from .brain import *  # noqa: F401,F403
from .voice import *  # noqa: F401,F403
from .sprites import *  # noqa: F401,F403
from .pet_tasks import read_json, write_json
from .tasks import fmt_when

MEMORY = os.path.join(DATA_DIR, "memory.json")       # факты о тебе
DAY = os.path.join(DATA_DIR, "day.json")             # что было сегодня: команды, ошибки, игры
DIARY = os.path.join(DATA_DIR, "diary.json")         # итоги прошлых дней
FRESH = os.path.join(DATA_DIR, "phrases.json")       # свежие фразы от ИИ
ABOUT_ME = re.compile(r"\b(?:я|меня|мне|мной|мой|моя|моё|мое|мои|моего|моей|у меня)\b")


def today():
    return dt.date.today().isoformat()


class PetSmart:
    def smart_load(s):
        s.memory = read_json(MEMORY, [])
        s.day = read_json(DAY, {})
        s.fresh = read_json(FRESH, [])
        s.hinted = {}                                    # какие подсказки уже давал (чтобы не занудствовать)
        s.game_t = 0.0
        if s.day.get("date") not in (None, today()):
            threading.Thread(target=s.close_day, daemon=True).start()   # вчерашний день не подведён — подводим
        elif not s.day:
            s.day = {"date": today(), "cmds": {}, "fails": [], "chat": 0, "games": {}}
        s.morning_due = s.day.get("morning") != today()

    def day_save(s):
        write_json(DAY, s.day)

    def day_note(s, kind, text):
        """Отметка в дневник дня: что выполнил, что не понял, сколько болтали."""
        if s.day.get("date") != today():
            return
        if kind == "cmd":
            s.day["cmds"][text] = s.day["cmds"].get(text, 0) + 1
        elif kind == "fail" and text not in s.day["fails"]:
            s.day["fails"] = (s.day["fails"] + [text])[-40:]
        elif kind == "chat":
            s.day["chat"] = s.day.get("chat", 0) + 1
        s.day_save()

    # --- ИИ без характера Клодика (для служебных задач) ---
    def llm(s, system, prompt, tokens=400):
        if s.brain != "ollama":
            return None
        models = ollama_models()
        model = pick_model(models) if models else None
        if not model:
            return None
        d = ollama_call("/api/chat", {"model": model, "stream": False, "keep_alive": "10m",
                                      "options": {"num_predict": tokens, "temperature": 0.8},
                                      "messages": [{"role": "system", "content": system},
                                                   {"role": "user", "content": prompt}]}, 300)
        return d["message"]["content"].strip()

    # --- память о тебе ---
    def memory_text(s):
        return "; ".join(f["fact"] for f in s.memory[-20:])

    def remember(s, fact, quiet=False):
        fact = fact.strip(" .,!")
        if len(fact) < 3:
            return
        if any(match(fact, f["fact"]) > 0.85 for f in s.memory):
            return quiet or s.say("Это я уже помню!", 2)
        s.memory = (s.memory + [{"fact": fact, "t": time.time()}])[-200:]
        write_json(MEMORY, s.memory)
        if not quiet:
            s.say(f"Запомнил: {fact}", 3)

    def recall(s):
        if not s.memory:
            return s.say("Я про тебя пока ничего не знаю. Скажи «запомни, что я люблю…»", 4)
        s.say("Что я о тебе знаю:\n" + "\n".join("• " + f["fact"] for f in s.memory[-12:]), 12)

    def forget_fact(s, what):
        what = what.strip(" .,")
        if re.match(r"^(?:вс[её])?\s*(?:обо мне|про меня)?$", what):
            s.memory = []
            write_json(MEMORY, s.memory)
            return s.say("Забыл всё о тебе. Начнём знакомство заново!", 3)
        hit = [f for f in s.memory if what in f["fact"].lower() or match(what, f["fact"]) > 0.6]
        s.memory = [f for f in s.memory if f not in hit]
        write_json(MEMORY, s.memory)
        s.say(f"Забыл: {hit[0]['fact']}" if hit else "Такого я и не помнил", 2)

    def learn_facts(s, said):
        """После разговора тихо выписываю новые факты о тебе (в фоне, Ollama)."""
        if not ABOUT_ME.search(said.lower()) or not s.on("learn_facts"):
            return

        def go():
            try:
                out = s.llm("Ты выделяешь факты о пользователе из его фразы. Отвечай списком, по одному факту в строке, "
                            "от третьего лица («любит Dota 2», «зовут Олег»). Только устойчивые факты: имя, интересы, "
                            "семья, работа, планы, привычки. Если фактов нет — ответь словом «нет».",
                            f"Фраза пользователя: «{said}»\nУже известно: {s.memory_text() or 'ничего'}", 120)
            except (OSError, ValueError, KeyError):
                return
            for line in (out or "").splitlines():
                f = line.strip(" -•*0123456789.").strip()
                if f and f.lower() != "нет" and len(f) < 120:
                    s.answers.put(("fact", f))
        threading.Thread(target=go, daemon=True).start()

    # --- игры: сколько и во что (для сводки и подсказок) ---
    def track_game(s, dt_s):
        if not s.gaming:
            s.game_t = 0.0
            return
        h = u32.GetForegroundWindow()
        pid = wt.DWORD()
        u32.GetWindowThreadProcessId(h, ctypes.byref(pid))
        name = os.path.splitext(proc_name(pid.value))[0] or "игра"
        if s.day.get("date") == today():
            s.day["games"][name] = s.day["games"].get(name, 0) + dt_s
        s.game_t += dt_s

    # --- сам предлагает ---
    def hints(s):
        now, hour = time.time(), time.localtime().tm_hour

        def once(key, every, text):
            if now - s.hinted.get(key, 0) > every:
                s.hinted[key] = now
                s.say(text, 8, speak=True)
                return True
        if s.game_t > 3 * 3600 and once("game", 3 * 3600, "Ты уже 3 часа в игре — может, перерыв и водички?"):
            return
        if 1 <= hour < 5 and not s.gaming and once("late", 6 * 3600, "Уже глубокая ночь… Может, спать? Я покараулю комп."):
            return
        if s.clock > 2 * 3600 and not s.gaming and once("break", 2 * 3600, "Два часа за компом — разомнись минутку!"):
            return
        fails = s.day.get("fails", [])
        if len(fails) >= 3 and once("fails", 4 * 3600, "Я сегодня не понял несколько твоих фраз. Ночью разберусь, "
                                                         "а можешь пройти подстройку: «подстройся под мой голос»."):
            return

    # --- итоги дня: дневник, свежие фразы, самообучение на ошибках ---
    def close_day(s):
        d = s.day or {}
        if not s.on("diary"):                             # итоги выключены — просто начинаем новый день
            s.day = {"date": today(), "cmds": {}, "fails": [], "chat": 0, "games": {}}
            return s.day_save()
        games = ", ".join(f"{g} — {fmt_secs(t)}" for g, t in sorted(d.get("games", {}).items(), key=lambda x: -x[1])[:5])
        top = ", ".join(f"«{c}» ×{n}" for c, n in sorted(d.get("cmds", {}).items(), key=lambda x: -x[1])[:8])
        facts = s.memory_text()
        summary, phrases = "", []
        try:
            out = s.llm("Ты Клодик — пиксельный помощник на рабочем столе. Пиши только по-русски.",
                        f"Мой день ({d.get('date')}):\nкоманды: {top or 'нет'}\nигры: {games or 'нет'}\n"
                        f"болтали раз: {d.get('chat', 0)}\nчто я не понял: {'; '.join(d.get('fails', [])[:15]) or 'нет'}\n"
                        f"что я знаю о хозяине: {facts or 'мало'}\n\n"
                        "1) Первой строкой: «ИТОГ: …» — 2 коротких предложения, итоги дня от твоего лица, по-дружески.\n"
                        "2) Потом 25 строк: «Ф: …» — новые короткие смешные фразы, которые ты скажешь во время "
                        "прогулки по экрану завтра (до 60 символов, учитывай интересы хозяина, без повторов).", 900)
            for line in (out or "").splitlines():          # ИИ пишет фразы то «Ф: …», то «1) …» — берём оба
                line = line.strip()
                if line.upper().startswith("ИТОГ:"):
                    summary = line.split(":", 1)[1].strip()
                    continue
                p = re.sub(r"^(?:ф:|\d+[).]|[-•*])\s*", "", line, flags=re.I).strip(" «»\"")
                if p != line.strip(" «»\"") and 3 < len(p) <= 70 and not any(match(p, q) > 0.8 for q in phrases):
                    phrases.append(p)
        except (OSError, ValueError, KeyError) as e:
            log_error(f"итоги дня: {e}")
        learned = s.learn_from_fails(d.get("fails", []))
        if d.get("date"):
            diary = read_json(DIARY, [])
            diary = (diary + [{"date": d["date"], "summary": summary, "games": d.get("games", {}),
                               "cmds": sum(d.get("cmds", {}).values()), "learned": learned}])[-60:]
            write_json(DIARY, diary)
        if phrases:
            s.fresh = phrases
            write_json(FRESH, phrases)
        if d.get("date") != today():
            s.day = {"date": today(), "cmds": {}, "fails": [], "chat": 0, "games": {}}
            s.day_save()

    def learn_from_fails(s, fails):
        """Ночью разбираю непонятые фразы: ИИ угадывает команду, я проверяю, что она правда команда, и запоминаю."""
        n = 0
        for f in fails[:15]:
            if f in s.learned:
                continue
            try:
                out = s.llm(SYSTEM, f"Фраза с распознавания голоса: «{f}». Если это искажённая команда — ответь "
                                    "«CMD: <команда>», иначе ответь «нет».", 60)
            except (OSError, ValueError, KeyError):
                break
            m = re.match(r"\s*CMD:\s*(.+)", out or "")
            if m:
                cmd = m[1].strip().strip("«»\"'")
                if s.local_command(cmd, dry=True):
                    s.learned[f] = cmd
                    n += 1
        if n:
            s._vocab = None
            save_learned(s.learned)
        return n

    def walk_phrase(s):
        pool = (s.fresh or []) + PHRASES
        return random.choice(s.fresh if s.fresh and random.random() < 0.7 else pool)

    # --- утренняя сводка: всё, что есть на компе, без интернета ---
    def morning(s):
        s.morning_due = False
        s.day["morning"] = today()
        s.day_save()
        h = time.localtime().tm_hour
        hello = "Доброе утро" if h < 12 else "Добрый день" if h < 18 else "Добрый вечер"
        hello += f", {s.addr()}!" if s.addr() else "!"
        now = s.now()
        end_of_day = dt.datetime.combine(dt.date.today(), dt.time(23, 59)).timestamp()
        todays = [r for r in s.reminders if r["t"] <= end_of_day]
        parts = [hello]
        if todays:
            r = todays[0]
            parts.append(f"Напоминаний на сегодня: {len(todays)}, первое {fmt_when(r['t'], now)}"
                         + (f" — {r['text']}." if r["text"] else "."))
        if s.notes:
            parts.append(f"В списке дел {len(s.notes)}: {', '.join(s.notes[:3])}{'…' if len(s.notes) > 3 else ''}.")
        diary = read_json(DIARY, [])
        if diary:
            y = diary[-1]
            if y.get("games"):
                g, t = max(y["games"].items(), key=lambda x: x[1])
                parts.append(f"Вчера ты больше всего играл в {g} — {fmt_secs(t)}.")
            if y.get("learned"):
                parts.append(f"За ночь я выучил {y['learned']} новых команд.")
            if y.get("summary"):
                parts.append(y["summary"])
        s.stats.poll()
        if s.stats.disk_free is not None and s.stats.disk_free < 20:
            parts.append(f"На диске C осталось всего {s.stats.disk_free:.0f} ГБ.")
        s.say(" ".join(parts), 20, speak=True)

    def smart_tick(s):
        """Раз в 10 секунд: игры, подсказки, смена дня, утренняя сводка."""
        s.track_game(10)
        if s.day.get("date") != today() and not getattr(s, "closing", False):
            s.closing = True

            def go():
                s.close_day()
                s.closing = False
            threading.Thread(target=go, daemon=True).start()
        if s.clock > 20 and not getattr(s, "alive_marked", False):
            s.alive_marked = True
            from .update import mark_alive
            mark_alive()                                   # «новая версия запустилась» — откат не нужен
            s.daily_backup()
        if (s.morning_due and time.localtime().tm_hour >= 5 and s.clock > 8 and not s.gaming and not s.busy
                and s.on("morning") and not s.quiet_now() and "name" in s.ob["done"]):
            s.morning()
        if not s.busy and not s.gaming:
            if s.on("hints") and not s.quiet_now():
                (s.on("game_talk") and s.diablo_hint()) or s.hints()
        if FROZEN and s.day.get("date") == today() and s.day.get("upd") != today() and s.clock > 60 and s.on("updates"):
            s.day["upd"] = today()                        # раз в день: нет ли новой версии
            s.day_save()
            s.check_update()

    def smart_command(s, seg):
        """Команды памяти → функция или None."""
        if re.search(r"что ты (?:обо мне|про меня) (?:знаешь|помнишь)|что ты помнишь|что ты знаешь обо мне", seg):
            return s.recall
        if m := re.match(r"^забудь,?\s+(?:что\s+)?(.+)", seg):
            if not re.search(r"выученн", m[1]):
                return lambda w=m[1]: s.forget_fact(w)
        if (m := re.match(r"^запомни,?\s+(?:что\s+)?(.+)", seg)) and ABOUT_ME.search(m[1]):
            return lambda f=m[1]: s.remember(re.sub(r"^я\s+", "", f))
        if re.search(r"(?:итоги|дневник)\s+(?:дня|за день)|как прош[её]л день", seg):
            return s.show_diary
        if re.search(r"утренн\w+ сводк|что сегодня|сводка", seg):
            return s.morning
        return None

    def show_diary(s):
        diary = read_json(DIARY, [])
        if not diary:
            d = s.day
            return s.say(f"Сегодня: выполнил {sum(d.get('cmds', {}).values())} команд, болтали {d.get('chat', 0)} раз. "
                         "Итоги подведу ночью.", 6, speak=True)
        y = diary[-1]
        s.say(f"{y['date']}: {y.get('summary') or 'день как день'} Выучил: {y.get('learned', 0)}.", 10, speak=True)
