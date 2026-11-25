"""Дела без ИИ: разбор «когда» для напоминаний («завтра в 9», «в пятницу в 18:30», «через 2 часа»)
и калькулятор («сколько будет 15% от 3400», «корень из 144»)."""
import ast
import datetime as dt
import math

from .common import *  # noqa: F401,F403

WEEKDAYS = {"понедельник": 0, "вторник": 1, "сред": 2, "четверг": 3, "пятниц": 4, "суббот": 5, "воскресен": 6}
MONTHS = {"январ": 1, "феврал": 2, "март": 3, "апрел": 4, "ма": 5, "июн": 6, "июл": 7, "август": 8, "сентябр": 9,
          "октябр": 10, "ноябр": 11, "декабр": 12}
DAY_WORDS = ("сегодня", "завтра", "послезавтра")
WD_NAMES = ("в понедельник", "во вторник", "в среду", "в четверг", "в пятницу", "в субботу", "в воскресенье")


def parse_when(seg, now):
    """→ (unix-время, о чём напомнить) или (None, seg), если времени в фразе нет."""
    t = num_words(seg.lower()).replace("полчаса", "30 мин").replace("полтора часа", "90 мин")
    cuts = []                                            # куски фразы про время — вырежем из текста напоминания
    m = re.search(r"\b(?:через|на)\s+((?:\d+\s+(?:час\w*|мин\w*|сек\w*)\s*)+)", t)
    if m or re.search(r"засеки|таймер", t):
        secs = parse_duration(m[1] if m else t)
        if secs:
            return now + secs, clean_note(re.sub(r"\b(?:через|на)?\s*\d+\s+(?:час\w*|мин\w*|сек\w*)", " ", t), [])
    base = dt.datetime.fromtimestamp(now)
    day = hour = minute = None
    if "послезавтра" in t:
        day = base.date() + dt.timedelta(days=2)
    elif "завтра" in t:
        day = base.date() + dt.timedelta(days=1)
    elif "сегодня" in t:
        day = base.date()
    wd = re.search(r"\bв(?:о)?\s+(" + "|".join(WEEKDAYS) + r")\w*", t)
    if day is None and wd:
        want = WEEKDAYS[wd[1]]
        day = base.date() + dt.timedelta(days=(want - base.weekday()) % 7)
        cuts.append(wd[0])
    dm = re.search(r"\b(\d{1,2})\s+(" + "|".join(MONTHS) + r")\w*", t) or re.search(r"\b(\d{1,2})\.(\d{1,2})\b", t)
    if day is None and dm:
        mon = MONTHS.get(dm[2]) or int(dm[2]) if not dm[2].isdigit() else int(dm[2])
        try:
            day = dt.date(base.year, mon, int(dm[1]))
            if day < base.date():
                day = dt.date(base.year + 1, mon, int(dm[1]))
            cuts.append(dm[0])
        except ValueError:
            day = None
    tm = re.search(r"\bв\s+(\d{1,2})(?:[:.\s](\d{2})\b)?(?:\s+час\w*)?(?:\s+(утра|дня|вечера|ночи))?", t)
    if "в полдень" in t:
        hour, minute = 12, 0
        cuts.append("в полдень")
    elif "в полночь" in t:
        hour, minute = 0, 0
        cuts.append("в полночь")
    elif tm and int(tm[1]) < 24:
        hour, minute = int(tm[1]), int(tm[2] or 0)
        part = tm[3] or ""
        if part in ("дня", "вечера") and hour < 12:
            hour += 12
        if part == "ночи" and hour == 12:
            hour = 0
        cuts.append(tm[0])
    elif (u := re.search(r"\b(утром|днём|днем|вечером|ночью)\b", t)) and day is not None:
        hour, minute = {"утром": 9, "днём": 14, "днем": 14, "вечером": 19, "ночью": 23}[u[1]], 0
        cuts.append(u[0])
    if day is None and hour is None:
        return None, seg
    if hour is None:
        hour, minute = 9, 0                               # «завтра напомни…» — утром в 9
    when = dt.datetime.combine(day or base.date(), dt.time(hour, minute))
    if when <= base:                                      # время уже прошло: сегодня → завтра, день недели → +7
        when += dt.timedelta(days=7 if wd and day is not None and not any(w in t for w in DAY_WORDS) else 1)
    return when.timestamp(), clean_note(t, cuts + list(DAY_WORDS)[::-1])


def clean_note(t, cuts):
    """Убирает из фразы куски про время и служебные слова — остаётся, о чём напомнить."""
    for c in cuts:
        if c:
            t = t.replace(c, " ")
    t = re.sub(r"\b(?:напомни(?:те)?|поставь|напоминание|засеки|таймер|будильник|разбуди|мне|меня)\b", " ", t)
    t = re.sub(r"^\s*(?:что|чтобы)\s+", "", re.sub(r"\s+", " ", t).strip())
    return t.strip(" ,.-")


def fmt_when(ts, now):
    """«через 25 мин», «сегодня в 18:30», «завтра в 9:00», «в пятницу (28.11) в 10:00»."""
    if ts - now < 3600:
        return "через " + fmt_secs(max(1, ts - now))
    w, b = dt.datetime.fromtimestamp(ts), dt.datetime.fromtimestamp(now).date()
    hm = f"{w.hour}:{w.minute:02d}"
    if w.date() == b:
        return f"сегодня в {hm}"
    if w.date() == b + dt.timedelta(days=1):
        return f"завтра в {hm}"
    if (w.date() - b).days < 7:
        return f"{WD_NAMES[w.weekday()]} в {hm}"
    return f"{w.day:02d}.{w.month:02d} в {hm}"


# ---------- калькулятор ----------
CALC_TRIGGER = re.compile(r"^(?:сколько будет|сколько|посчитай|вычисли|реши|подсчитай)\s+(.+)")
OPS = {ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b, ast.Mult: lambda a, b: a * b,
       ast.Div: lambda a, b: a / b, ast.Mod: lambda a, b: a % b,
       ast.Pow: lambda a, b: a ** b if abs(b) <= 100 else (_ for _ in ()).throw(ValueError("слишком большая степень"))}


def _eval(node):
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in OPS:
        return OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        v = _eval(node.operand)
        return -v if isinstance(node.op, ast.USub) else v
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "sqrt" and len(node.args) == 1:
        return math.sqrt(_eval(node.args[0]))
    raise ValueError("не арифметика")


def calc(seg):
    """Пример словами → строка с ответом, или None, если это не пример."""
    t = num_words(seg.lower()).replace(",", ".")
    m = CALC_TRIGGER.match(t)
    expr = m[1] if m else t
    if not m and not re.search(r"\d\s*(?:плюс|минус|умнож|помнож|раздел|подел|делить|[+\-*/×x])\s*\d", expr):
        return None
    e = re.sub(r"(\d+(?:\.\d+)?)\s*(?:%|процент\w*)\s+от\s+(\d+(?:\.\d+)?)", r"(\1*\2/100)", expr)
    for pat, rep in ((r"корень\s+(?:квадратный\s+)?из\s+(\d+(?:\.\d+)?)", r"sqrt(\1)"), (r"в\s+квадрате", "**2"),
                     (r"в\s+кубе", "**3"), (r"в\s+степени", "**"), (r"плюс", "+"), (r"минус", "-"),
                     (r"(?:умножить|умножь|помножить|умноженное)\s*(?:на)?|[×x]", "*"),
                     (r"(?:разделить|раздели|поделить|подели|делить|деленное|делённое)\s*(?:на)?", "/"),
                     (r"\bравно\b|=|\?", ""), (r"\bскобка открывается\b", "("), (r"\bскобка закрывается\b", ")")):
        e = re.sub(pat, rep, e)
    if not re.fullmatch(r"[\d.\s+\-*/()%]*(?:sqrt[\d.\s+\-*/()%]*)*", e) or not re.search(r"\d", e):
        return None
    try:
        v = _eval(ast.parse(e.strip(), mode="eval"))
    except (ValueError, SyntaxError, ZeroDivisionError, OverflowError, TypeError):
        return None
    if isinstance(v, float) and v.is_integer() and abs(v) < 1e15:
        v = int(v)
    s = f"{v:,}".replace(",", " ") if isinstance(v, int) else f"{round(v, 6):,}".replace(",", " ").replace(".", ",")
    return f"{expr.strip()} = {s}"
