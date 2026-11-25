"""Машина эмоций: эмоция + сила + контекст → клип. Словарь клипов — data/emotions.json (13 эмоций × 3 силы ×
3 варианта). Клип собирается из слоёв (поза, глаза, брови, рот, шапка, частицы) и движения; варианты не повторяются
подряд; очередь, приоритет, плавный выход. Режимы анимаций: max / moderate / min."""
import math

from .common import *  # noqa: F401,F403
from .policy import PKG_DATA

EMO = json.load(open(os.path.join(PKG_DATA, "emotions.json"), encoding="utf-8"))
K = {"light": 0.6, "medium": 1.0, "strong": 1.5}
DUR = {"light": 1.3, "medium": 1.9, "strong": 2.6}
PART = {"joy": "stars", "sad": "drop", "tired": "zzz", "doubt": "question", "tenderness": "hearts", "surprise": "exclaim",
        "embarrassed": "blush", "playful_anger": "steam", "pride": "sparkle", "gratitude": "hearts", "fear": "exclaim",
        "interest": "question", "boredom": "dots"}
COLOR = {"playful_anger": "#e0553f", "embarrassed": "#e5826a"}
PRIORITY = {"surprise": 3, "fear": 3, "playful_anger": 3, "joy": 2, "pride": 2, "gratitude": 2, "tenderness": 2,
            "embarrassed": 2, "doubt": 1, "interest": 1, "sad": 1, "tired": 1, "boredom": 0}


def sw(t, f):                                            # «качель» −1/+1 с частотой f
    return 1 if int(t * f) % 2 else -1


# описание клипа из emotions.json → поза в момент u (0..1), время t, сила k
POSE = {
    "подпрыгивает": lambda u, t, k: {"eyes": "happy", "mouth": "smile", "hop": 1},
    "хлопает": lambda u, t, k: {"arms": "clap" if int(t * 6 * k) % 2 else "out", "eyes": "happy", "mouth": "smile"},
    "танцует": lambda u, t, k: {"sway": sw(t, 3 * k), "legs": int(t * 4) % 2, "eyes": "closed", "mouth": "smile"},
    "зевает": lambda u, t, k: {"mouth": "yawn" if 0.2 < u < 0.8 else -1, "eyes": "closed", "arms": "up" if u < 0.6 else "normal"},
    "рисует на полу": lambda u, t, k: {"squash": 1, "arms": "down", "eyes": "down", "sh": sw(t, 2)},
    "смотрит по сторонам": lambda u, t, k: {"sh": sw(t, 1.5), "eyes": "side"},
    "наклоняет голову": lambda u, t, k: {"sh": 1, "hat_dx": 1, "brow": "raise"},
    "приближается к курсору": lambda u, t, k: {"eyes": "wide", "walk_to_cursor": 1},
    "поднимает бровь": lambda u, t, k: {"brow": "raise", "mouth": 0},
    "потягивается": lambda u, t, k: {"stretch": 1 if 0.15 < u < 0.85 else 0, "arms": "up", "eyes": "closed"},
    "клюёт носом": lambda u, t, k: {"eyes": "closed" if int(t * 1.5) % 2 else "down", "squash": int(t * 1.5) % 2},
    "садится": lambda u, t, k: {"squash": 1, "legs": -1, "eyes": "down"},
    "опускает уши/шапку": lambda u, t, k: {"hat_dy": 1, "eyes": "down", "brow": "sad"},
    "вздыхает": lambda u, t, k: {"squash": 1 if 0.3 < u < 0.7 else 0, "eyes": "down", "brow": "sad"},
    "идёт медленно": lambda u, t, k: {"eyes": "down", "slow_walk": 1, "legs": int(t * 3) % 2},
    "отпрыгивает": lambda u, t, k: {"eyes": "wide", "mouth": "o", "jump_away": 1},
    "глаза широко": lambda u, t, k: {"eyes": "wide", "mouth": "o"},
    "знак !": lambda u, t, k: {"eyes": "wide", "arms": "up"},
    "прячет лицо": lambda u, t, k: {"arms": "face", "blush": 1},
    "краснеет": lambda u, t, k: {"blush": 1, "eyes": "down", "sh": sw(t, 1)},
    "поправляет шапку": lambda u, t, k: {"arms": "head", "hat_dx": sw(t, 4) if u < 0.6 else 0, "blush": 1},
    "выпрямляется": lambda u, t, k: {"stretch": 1, "eyes": "happy"},
    "руки в боки": lambda u, t, k: {"arms": "hips", "stretch": 1, "mouth": "smile"},
    "сияет": lambda u, t, k: {"eyes": "happy", "mouth": "smile", "stretch": int(t * 3) % 2},
    "дрожит": lambda u, t, k: {"jitter": sw(t, 12), "eyes": "wide", "arms": "face" if k > 1 else "normal"},
    "прячется за краем": lambda u, t, k: {"eyes": "wide", "hide_edge": 1},
    "оглядывается": lambda u, t, k: {"sh": sw(t, 4), "eyes": "wide"},
    "чешет затылок": lambda u, t, k: {"arms": "head", "brow": "raise", "sh": sw(t, 3) if u > 0.5 else 0},
    "знак ?": lambda u, t, k: {"brow": "raise", "eyes": "up"},
    "качает головой": lambda u, t, k: {"sh": sw(t, 3), "eyes": "down", "brow": "sad"},
    "кланяется": lambda u, t, k: {"squash": 1 if 0.25 < u < 0.75 else 0, "eyes": "closed", "hat_dy": 1 if 0.25 < u < 0.75 else 0},
    "сердечко": lambda u, t, k: {"eyes": "happy", "mouth": "smile"},
    "машет": lambda u, t, k: {"arms": "wave" if int(t * 5) % 2 else "up", "mouth": "smile"},
    "мягко улыбается": lambda u, t, k: {"eyes": "happy", "mouth": "smile"},
    "сердечки": lambda u, t, k: {"eyes": "happy", "blush": 1},
    "греется": lambda u, t, k: {"squash": 1, "eyes": "closed", "arms": "face"},
    "топает": lambda u, t, k: {"legs": int(t * 8) % 2, "eyes": "angry", "squash": int(t * 8) % 2},
    "надувается": lambda u, t, k: {"puff": 1 if 0.2 < u < 0.8 else 0, "eyes": "angry", "arms": "out"},
    "облачко пара": lambda u, t, k: {"eyes": "angry", "arms": "hips"},
}


class Emotions:
    """Очередь клипов: emote() ставит клип, frame() отдаёт позу для текущего кадра."""
    def __init__(s):
        s.clip, s.queue, s.last = None, [], {}

    def emote(s, emo, level="medium", now=0.0, mode="max", style="lively"):
        if emo not in EMO["emotions"]:
            return None
        lv = ["light", "medium", "strong"]
        i = lv.index(level) + {"calm": -1, "lively": 0, "very": 1}.get(style, 0)
        level = lv[max(0, min(2, i))]
        clips = {k: v for k, v in EMO["emotions"][emo]["clips"].items() if f"_{level}_" in k}
        names = [n for n in clips if n != s.last.get(emo)] or list(clips)
        name = random.choice(names)                         # не повторять один и тот же вариант подряд
        s.last[emo] = name
        clip = {"emo": emo, "level": level, "name": name, "desc": clips[name], "t0": now, "dur": DUR[level], "mode": mode}
        if s.clip and PRIORITY.get(emo, 1) < PRIORITY.get(s.clip["emo"], 1) and now < s.clip["t0"] + s.clip["dur"]:
            s.queue = (s.queue + [clip])[-3:]               # важнее идёт сейчас — эта подождёт
        else:
            s.clip = clip
        return clip

    def frame(s, now):
        c = s.clip
        if c and now >= c["t0"] + c["dur"]:
            s.clip = c = None
            if s.queue:
                s.clip = c = s.queue.pop(0)
                c["t0"] = now
        if not c:
            return None
        u = (now - c["t0"]) / c["dur"]
        k = K[c["level"]]
        pose = dict(POSE.get(c["desc"], lambda *a: {})(u, now, k))
        if c["mode"] == "min":                              # минимум: только лицо, без частиц и движений
            pose = {k2: v for k2, v in pose.items() if k2 in ("eyes", "mouth", "brow")}
        else:
            kind = PART.get(c["emo"])
            if kind and not (c["mode"] == "moderate" and c["level"] == "light"):
                pose["particles"] = (kind, (u * 1.5) % 1.0, {"light": 1, "medium": 2, "strong": 3}[c["level"]])
            if kind == "blush":
                pose["blush"] = 1
        if c["emo"] in COLOR and c["mode"] != "min":
            pose["color"] = COLOR[c["emo"]]
        pose["emo"] = c["emo"]
        return pose


def micro(t, mode):
    """Микроанимации в простое: дыхание, переступание, поправить шапку (моргание и взгляд — в Pet.draw)."""
    if mode == "min":
        return {}
    out = {}
    if (t % 3.2) < 0.35:
        out["squash"] = 1                                  # дыхание
    if mode == "max":
        if (t % 11) < 0.4:
            out["legs"] = int(t * 5) % 2                   # переступает
        if (t % 37) < 0.6:
            out["hat_dx"] = sw(t, 6)                       # поправляет шапку
    return out
