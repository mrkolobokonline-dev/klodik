"""Внешний вид: 20 своих пиксельных шапок/костюмов, свои скины из %APPDATA%\\Klodik\\skins, частицы эмоций
и рисование Клодика по слоям: тело, руки (поза), ноги, глаза, брови, рот, румянец, шапка."""
from .common import *  # noqa: F401,F403

# шапка → клетки (столбец, строка, ширина, высота, цвет); строки < 0 — над телом. Всё нарисовано с нуля.
HAT_ART = {
    "chef": [(3, -1, 10, 1, "#f4f4f4"), (4, -4, 8, 3, "#ffffff"), (3, -5, 4, 2, "#ffffff"), (9, -5, 4, 2, "#ffffff"),
             (6, -6, 4, 2, "#ffffff")],
    "helmet": [(4, -3, 8, 1, "#f2c230"), (3, -2, 10, 1, "#f2c230"), (1, -1, 14, 1, "#d9a400"), (7, -3, 2, 2, "#d9a400")],
    "astronaut": [(1, -2, 14, 1, "#d9dde3"), (2, -4, 12, 2, "#e6e9ee"), (4, -5, 8, 1, "#e6e9ee"), (5, -4, 6, 2, "#8fd0ff"),
                  (12, -6, 1, 2, "#999999"), (12, -7, 1, 1, "#e0445a")],
    "wizard": [(2, -1, 12, 1, "#5a3fa8"), (4, -2, 8, 1, "#5a3fa8"), (5, -3, 6, 1, "#5a3fa8"), (6, -4, 4, 1, "#5a3fa8"),
               (7, -5, 2, 1, "#5a3fa8"), (8, -6, 1, 1, "#5a3fa8"), (5, -2, 1, 1, "#ffd84a"), (8, -4, 1, 1, "#ffd84a")],
    "pirate": [(1, -1, 14, 1, "#2b2b2b"), (3, -3, 10, 2, "#2b2b2b"), (1, -2, 2, 1, "#2b2b2b"), (13, -2, 2, 1, "#2b2b2b"),
               (7, -3, 2, 1, "#f4f4f4")],
    "crown": [(4, -1, 8, 1, "#e8b923"), (4, -3, 1, 2, "#e8b923"), (7, -3, 2, 2, "#e8b923"), (11, -3, 1, 2, "#e8b923"),
              (5, -1, 1, 1, "#e0445a"), (10, -1, 1, 1, "#4c8fd9")],
    "ushanka": [(2, -3, 12, 3, "#7a5a3a"), (3, -3, 10, 1, "#9c7a55"), (0, -1, 2, 4, "#7a5a3a"), (14, -1, 2, 4, "#7a5a3a"),
                (7, -2, 2, 1, "#d4af37")],
    "cowboy": [(0, -1, 16, 1, "#8b5a2b"), (4, -3, 8, 2, "#8b5a2b"), (5, -4, 6, 1, "#8b5a2b"), (4, -2, 8, 1, "#5c3a1a")],
    "beret": [(2, -1, 11, 1, "#c0392b"), (3, -2, 10, 1, "#c0392b"), (11, -3, 1, 1, "#c0392b")],
    "tophat": [(1, -1, 14, 1, "#1b1b1b"), (4, -5, 8, 4, "#1b1b1b"), (4, -2, 8, 1, "#c0392b")],
    "hood": [(1, -2, 14, 2, "#3e4a3d"), (4, -3, 8, 1, "#3e4a3d"), (1, 0, 1, 5, "#3e4a3d"), (14, 0, 1, 5, "#3e4a3d")],
    "knight": [(2, -3, 12, 3, "#9aa3ad"), (2, 0, 12, 1, "#7d858e"), (7, -5, 2, 2, "#c0392b")],
    "panama": [(1, -1, 14, 1, "#e8d9a8"), (3, -3, 10, 2, "#e8d9a8"), (3, -2, 10, 1, "#4c8fd9")],
    "santa": [(2, -1, 12, 1, "#ffffff"), (4, -3, 8, 2, "#d94a4a"), (7, -4, 5, 1, "#d94a4a"), (11, -5, 2, 1, "#d94a4a"),
              (13, -5, 2, 2, "#ffffff")],
    "pumpkin": [(2, -4, 12, 4, "#e67e22"), (4, -4, 1, 4, "#d35400"), (11, -4, 1, 4, "#d35400"), (7, -5, 2, 1, "#2e7d32"),
                (5, -3, 1, 1, "#4a2a12"), (10, -3, 1, 1, "#4a2a12"), (6, -2, 4, 1, "#4a2a12")],
    "dj": [(2, -2, 12, 1, "#222222"), (1, -1, 1, 2, "#222222"), (14, -1, 1, 2, "#222222"), (0, 1, 2, 3, "#222222"),
           (14, 1, 2, 3, "#222222"), (0, 2, 1, 1, "#4c8fd9"), (15, 2, 1, 1, "#4c8fd9")],
    "geek": [],                                           # очки рисуются поверх глаз (см. FACE)
    "ninja": [(2, 1, 12, 1, "#1f2a44"), (14, 1, 2, 1, "#1f2a44"), (15, 2, 1, 2, "#1f2a44")],
    "wreath": [(2, -1, 12, 1, "#2e7d32"), (3, -2, 1, 1, "#e0445a"), (6, -2, 1, 1, "#ffd84a"), (9, -2, 1, 1, "#e0445a"),
               (12, -2, 1, 1, "#ffd84a"), (4, -1, 1, 1, "#7cc4ff")],
    "detective": [(1, -1, 14, 1, "#7a6a55"), (3, -3, 10, 2, "#7a6a55"), (3, -2, 10, 1, "#3b3328"), (7, -4, 2, 1, "#7a6a55")],
    "nightcap": [(2, -1, 12, 1, "#5b6ee1"), (4, -2, 9, 1, "#5b6ee1"), (7, -3, 6, 1, "#5b6ee1"), (11, -4, 3, 1, "#5b6ee1"),
                 (14, -5, 2, 2, "#ffffff")],
    "winter": [(3, -3, 10, 2, "#d94a4a"), (5, -3, 1, 2, "#b83838"), (9, -3, 1, 2, "#b83838"), (2, -1, 12, 1, "#ffffff"),
               (7, -4, 2, 1, "#ffffff")],
    "glasses": [],
    "pajama": [(2, -1, 12, 1, "#7f8fd1"), (4, -2, 8, 1, "#7f8fd1"), (8, -3, 4, 1, "#7f8fd1"), (12, -3, 2, 2, "#ffffff")],
}
# очки и маски — привязаны к глазам (сдвигаются, когда Клодик смотрит в сторону)
FACE = {
    "glasses": [(3, 2, 4, 2, "#111111"), (10, 2, 4, 2, "#111111"), (7, 2, 3, 1, "#111111"), (4, 2, 1, 1, "#777777"),
                (11, 2, 1, 1, "#777777")],
    "geek": [(3, 1, 4, 1, "#333333"), (3, 4, 4, 1, "#333333"), (3, 1, 1, 4, "#333333"), (6, 1, 1, 4, "#333333"),
             (10, 1, 4, 1, "#333333"), (10, 4, 4, 1, "#333333"), (10, 1, 1, 4, "#333333"), (13, 1, 1, 4, "#333333"),
             (7, 2, 3, 1, "#333333"), (8, 1, 1, 1, "#f4f4f4")],
}
NEW_HATS = {"chef": "Колпак повара", "astronaut": "Шлем космонавта", "wizard": "Колпак волшебника",
            "pirate": "Пиратская треуголка", "ushanka": "Шапка-ушанка", "cowboy": "Ковбойская шляпа", "beret": "Берет художника",
            "tophat": "Цилиндр фокусника", "hood": "Капюшон разбойника", "knight": "Рыцарский шлем", "panama": "Панама",
            "santa": "Новогодний колпак", "pumpkin": "Тыква (Хэллоуин)", "dj": "Наушники диджея", "geek": "Очки гика",
            "ninja": "Бандана ниндзя", "wreath": "Венок", "detective": "Шляпа детектива", "pajama": "Пижамный колпак"}
NEW_HAT_WORDS = {"повар": "chef", "космонавт": "astronaut", "шлем космо": "astronaut", "волшебн": "wizard",
                 "маг": "wizard", "пират": "pirate", "треуголк": "pirate", "ушанк": "ushanka", "ковбо": "cowboy",
                 "берет": "beret", "цилиндр": "tophat", "фокусн": "tophat", "капюшон": "hood", "разбойн": "hood",
                 "рыцар": "knight", "панам": "panama", "новогодн": "santa", "деда мороз": "santa", "тыкв": "pumpkin",
                 "наушник": "dj", "диджей": "dj", "гик": "geek", "бандан": "ninja", "ниндз": "ninja", "венок": "wreath",
                 "детектив": "detective", "пижам": "pajama"}
HATS.update(NEW_HATS)                                 # общий гардероб: старые + 20 новых
HAT_WORDS.update(NEW_HAT_WORDS)
SKINS = os.path.join(DATA_DIR, "skins")
_skin_cache = {}


def skins():
    """Свои скины: PNG в %APPDATA%\\Klodik\\skins (рисуются над головой). Только картинки — без кода."""
    try:
        return sorted(os.path.splitext(f)[0] for f in os.listdir(SKINS) if f.lower().endswith(".png"))
    except OSError:
        return []


def skin_image(name):
    if name not in _skin_cache:
        try:
            img = tk.PhotoImage(file=os.path.join(SKINS, name + ".png"))
            k = max(1, img.width() // 80)                  # не шире Клодика
            _skin_cache[name] = img.subsample(k) if k > 1 else img
        except tk.TclError:
            _skin_cache[name] = None
    return _skin_cache[name]


ARMS = {   # поза рук: (левая), (правая) — клетки
    "normal": [(0, 3, 2, 2), (14, 3, 2, 2)], "up": [(0, 0, 2, 2), (14, 0, 2, 2)],
    "wave": [(0, 3, 2, 2), (14, 0, 2, 2)], "hips": [(0, 4, 2, 1), (14, 4, 2, 1)],
    "face": [(3, 2, 4, 2), (9, 2, 4, 2)], "head": [(0, 3, 2, 2), (13, -1, 2, 2)],
    "clap": [(4, 3, 2, 2), (10, 3, 2, 2)], "out": [(-1, 3, 3, 1), (14, 3, 3, 1)], "down": [(0, 5, 2, 2), (14, 5, 2, 2)],
}
PARTICLE = {"stars": ("✦", "#ffd84a"), "drop": ("•", "#7cc4ff"), "zzz": ("z", "#a9503a"), "question": ("?", "#5b6ee1"),
            "hearts": ("♥", "#e0445a"), "exclaim": ("!", "#e0445a"), "blush": ("", ""), "steam": ("~", "#9aa3ad"),
            "sparkle": ("✧", "#ffd84a"), "notes": ("♪", "#5b6ee1"), "dots": ("…", "#6f5d55")}


def paint2(c, ox, oy, sp):
    """Клодик по слоям. sp: color, legs, squash, stretch, puff, arms, eyes, sh, brow, mouth, blush, hat, hat_dx, hat_dy."""
    color = sp.get("color", ORANGE)

    def px(col, row, w, h, fill=color):
        c.create_rectangle(ox + col * C, oy + row * C, ox + (col + w) * C, oy + (row + h) * C, fill=fill, outline="")
    st, puff, squash = sp.get("stretch", 0), sp.get("puff", 0), sp.get("squash", 0)
    px(2 - puff, -st, 12 + 2 * puff, 7 + st)                          # тело (выше — потянулся, шире — надулся)
    for a in ARMS.get(sp.get("arms", "normal"), ARMS["normal"]):
        px(*a)
    legs = sp.get("legs", -1)
    for i, col in enumerate((3, 5, 10, 12)):
        lifted = legs >= 0 and (i % 2) == legs
        px(col, 7, 1, (2 if lifted else 3) - squash)
    hat, sh = sp.get("hat", "none"), sp.get("sh", 0)
    eyes = sp.get("eyes", "open")
    if hat not in FACE:
        for i, col in enumerate((4 + sh, 11 + sh)):
            row, h = {"open": (2, 2), "closed": (3, 1), "up": (1, 2), "down": (3, 2), "wide": (1, 3), "angry": (2, 2),
                      "happy": (2, 1), "side": (2, 2)}.get(eyes, (2, 2))
            px(col, row, 1, h, EYE)
            if eyes == "happy":                            # ^ ^ — улыбается глазами
                px(col - 1, 3, 1, 1, EYE); px(col + 1, 3, 1, 1, EYE)
    brow = "angry" if eyes == "angry" else sp.get("brow")
    for i, col in enumerate((4 + sh, 11 + sh)):
        if brow == "angry":                                # брови домиком внутрь
            px(col - 1 if i == 0 else col + 1, 0, 1, 1, EYE); px(col, 1, 1, 1, EYE)
        elif brow == "raise" and i == 1:                    # одна бровь вверх — интерес
            px(col - 1, 0, 3, 1, EYE)
        elif brow == "sad":
            px(col + (1 if i == 0 else -1), 1, 1, 1, EYE)
    mouth = sp.get("mouth", -1)
    if mouth == "yawn":
        px(7, 4, 2, 2, EYE)
    elif mouth == "smile":
        px(6, 5, 1, 1, EYE); px(9, 5, 1, 1, EYE); px(7, 6, 2, 1, EYE)
    elif mouth == "o":
        px(7, 4, 2, 2, EYE)
    elif mouth in (0, 1):
        px(7, 5 - mouth, 2, 1, EYE)
    if sp.get("blush"):
        px(3, 4, 2, 1, "#ff8fa3"); px(11, 4, 2, 1, "#ff8fa3")
    hx, hy = sp.get("hat_dx", 0), sp.get("hat_dy", 0) - st
    if hat in FACE:
        for col, row, w, h, f in FACE[hat]:
            px(col + sh, row, w, h, f)
    elif hat.startswith("skin:"):
        img = skin_image(hat[5:])
        if img:
            c.create_image(ox + 8 * C + hx * C, oy + (hy - 1) * C, image=img, anchor="s")
    for col, row, w, h, f in HAT_ART.get(hat, []):
        px(col + hx, row + hy, w, h, f)


def particles(c, ox, oy, kind, phase, n):
    """Частицы эмоции над Клодиком; phase 0..1 — подъём и исчезновение."""
    if kind == "blush" or kind not in PARTICLE:
        return
    ch, col = PARTICLE[kind]
    for i in range(n):
        x = ox + (3 + i * 5 if n > 1 else 8) * C + (i % 2) * 6
        y = oy - 4 - phase * 22 - (i % 2) * 6
        c.create_text(x, y, text=ch * (i + 1 if kind == "zzz" else 1), fill=col, font=("Segoe UI", 11 + 2 * (i == 0), "bold"))
