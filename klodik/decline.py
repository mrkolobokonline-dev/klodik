"""Склонение имени владельца: звательный (как обращаться), родительный, дательный — UA/RU/EN.
Правила для типовых мужских и женских имён; если правило не уверено — sure=False, Клодик один раз уточнит."""

HUSH = "жчшщ"
SOFT_R = {"ігор", "лазар", "іван"}                       # р/н с мягкой основой: Ігоря, Ігорю (Іван — твёрдый, но звательный Іване)
UA_FEMALE_SOFT = {"ия", "ія"}


def decline(name, lang="ru"):
    """→ {"vocative", "genitive", "dative", "sure"}; dative может быть «Олексієві/Олексію»."""
    n = name.strip()
    low = n.lower()
    f = lambda voc, gen, dat, sure=True: {"vocative": voc, "genitive": gen, "dative": dat, "sure": sure}
    if not n:
        return f("", "", "", False)
    if lang == "en":
        return f(n, n + "'s", n)
    if lang == "uk":
        if low.endswith("ій"):                             # Олексій, Андрій, Сергій
            st = n[:-2]
            return f(st + "ію", st + "ія", f"{st}ієві/{st}ію")
        if low.endswith("й"):                              # Матвей → неуверенно
            st = n[:-1]
            return f(st + "ю", st + "я", st + "ю", False)
        if low.endswith("о"):                              # Дмитро, Петро
            st = n[:-1]
            return f(st + "е", st + "а", st + "у")
        if low.endswith(("а", "я")):                       # Саша, Микола, Марія
            st, last = n[:-1], low[-2] if len(low) > 1 else ""
            if low.endswith("ія"):
                return f(st + "є", st + "ї", st + "ї")
            if low.endswith("я"):
                return f(st + "ю", st + "і", st + "і", False)
            gen = st + ("і" if last in HUSH else "и")
            return f(st + "о", gen, st + "і")
        if low[-1] in "гкх":                               # Олег → «Олеже»/«Олегу» — спорно, уточним
            return f(n + "у", n + "а", n + "у", False)
        if low in SOFT_R or low.endswith("ор"):            # Ігор → Ігоре, Ігоря, Ігорю
            return f(n + "е", n + "я", n + "ю")
        if low[-1] in "бвдзлмнпрстфц":                     # Максим, Іван, Богдан
            return f(n + "е", n + "а", n + "у")
        return f(n, n, n, False)
    # русский: звательного падежа нет — обращаемся именем как есть
    if low.endswith(("ей", "ий", "ай", "ой")):             # Олексей, Алексей, Николай
        st = n[:-1]
        return f(n, st + "я", st + "ю")
    if low.endswith("а"):                                  # Саша, Маша, Никита
        st, last = n[:-1], low[-2] if len(low) > 1 else ""
        return f(n, st + ("и" if last in HUSH + "гкх" else "ы"), st + "е")
    if low.endswith("я"):                                  # Илья, Таня
        st = n[:-1]
        return f(n, st + "и", st + ("и" if low.endswith("ия") else "е"))
    if low[-1] in "бвгджзклмнпрстфхцчшщ":                  # Максим, Олег, Игорь (без ь)
        return f(n, n + "а", n + "у")
    if low.endswith("ь"):                                  # Игорь → Игоря, Игорю
        st = n[:-1]
        return f(n, st + "я", st + "ю")
    return f(n, n, n, False)


def guess_lang(name):
    """По буквам: і/ї/є/ґ — украинский, латиница — английский, иначе русский."""
    if any(ch in name.lower() for ch in "іїєґ"):
        return "uk"
    if name and all(ord(ch) < 128 for ch in name if ch.isalpha()):
        return "en"
    return "ru"
