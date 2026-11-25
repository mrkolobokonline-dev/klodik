"""Рисунки и окошки: сам Клодик, облачко, печенька, бульдозер, снег, друг."""
from .common import *  # noqa: F401,F403
from .apps import *  # noqa: F401,F403
from .winapi import *  # noqa: F401,F403
from .monitor import *  # noqa: F401,F403
from .brain import *  # noqa: F401,F403
from .voice import *  # noqa: F401,F403

# ---------- рисование ----------
def paint(c, ox, oy, color, legs, squash, eyes, sh, mouth, hat):
    """Пиксельный Клодик 16×10 клеток: тело, ручки, 4 ножки, глаза, шапка."""
    def px(col, row, w, h, fill=color):
        c.create_rectangle(ox + col * C, oy + row * C, ox + (col + w) * C, oy + (row + h) * C, fill=fill, outline="")
    px(2, 0, 12, 7)
    px(0, 3, 2, 2)
    px(14, 3, 2, 2)
    for i, col in enumerate((3, 5, 10, 12)):          # ножки: пары по очереди поднимаются
        lifted = legs >= 0 and (i % 2) == legs
        px(col, 7, 1, (2 if lifted else 3) - squash)
    if hat != "glasses":
        for i, col in enumerate((4 + sh, 11 + sh)):
            row, h = {"open": (2, 2), "closed": (3, 1), "up": (1, 2), "down": (3, 2), "wide": (1, 3),
                      "angry": (2, 2)}[eyes]
            px(col, row, 1, h, EYE)
            if eyes == "angry":                            # брови домиком внутрь — злится
                px(col - 1 if i == 0 else col + 1, 0, 1, 1, EYE)
                px(col, 1, 1, 1, EYE)
    if mouth == "yawn":
        px(7, 4, 2, 2, EYE)
    elif mouth in (0, 1):
        px(7, 5 - mouth, 2, 1, EYE)
    if hat == "helmet":
        px(4, -3, 8, 1, "#f2c230"); px(3, -2, 10, 1, "#f2c230"); px(1, -1, 14, 1, "#d9a400"); px(7, -3, 2, 2, "#d9a400")
    elif hat == "crown":
        g = "#e8b923"
        px(4, -1, 8, 1, g); px(4, -3, 1, 2, g); px(7, -3, 2, 2, g); px(11, -3, 1, 2, g)
        px(5, -1, 1, 1, "#e0445a"); px(10, -1, 1, 1, "#4c8fd9")
    elif hat == "glasses":
        px(3 + sh, 2, 4, 2, "#111"); px(10 + sh, 2, 4, 2, "#111"); px(7 + sh, 2, 3, 1, "#111")
        px(4 + sh, 2, 1, 1, "#777"); px(11 + sh, 2, 1, 1, "#777")
    elif hat == "nightcap":
        b = "#5b6ee1"
        px(2, -1, 12, 1, b); px(4, -2, 9, 1, b); px(7, -3, 6, 1, b); px(11, -4, 3, 1, b); px(14, -5, 2, 2, "white")
    elif hat == "winter":
        px(3, -3, 10, 2, "#d94a4a"); px(5, -3, 1, 2, "#b83838"); px(9, -3, 1, 2, "#b83838")
        px(2, -1, 12, 1, "white"); px(7, -4, 2, 1, "white")


def floating(root):
    w = tk.Toplevel(root)
    w.overrideredirect(True)
    w.attributes("-topmost", True)
    return w


def sprite_window(root, w, h):
    win = floating(root)
    win.attributes("-transparentcolor", KEY)
    c = tk.Canvas(win, width=w, height=h, bg=KEY, highlightthickness=0)
    c.pack()
    return win, c


class Bubble:
    def __init__(s, root):
        s.w = floating(root)
        s.l = tk.Label(s.w, bg=PAPER, fg=INK, font=("Segoe UI", 10), wraplength=260, justify="left", compound="left",
                       padx=10, pady=6, highlightthickness=2, highlightbackground=DARK)
        s.l.pack()
        s.l.bind("<Button-1>", lambda e: s.hide())
        s.until, s.size, s.pos = 0, (0, 0), None
        s.w.withdraw()

    def show(s, text, secs, image=None):
        if s.until and s.l.cget("text") == text:
            s.until = time.time() + secs
            return
        s.l.config(text=text, image=image or "")
        s.l.image = image
        s.until = time.time() + secs
        s.w.update_idletasks()
        s.size, s.pos = (s.w.winfo_reqwidth(), s.w.winfo_reqheight()), None
        s.w.deiconify()

    def hide(s):
        s.until = 0
        s.w.withdraw()

    def follow(s, cx, bottom, L, R):
        if not s.until:
            return
        if time.time() > s.until:
            return s.hide()
        bw, bh = s.size
        pos = (int(max(L, min(cx - bw / 2, R - bw))), int(max(0, bottom - bh)))
        if pos != s.pos:
            s.pos = pos
            s.w.geometry(f"+{pos[0]}+{pos[1]}")


class Prop:
    """Печенька или мячик: падает, прыгает, его можно схватить и кинуть."""
    SIZE = 26

    def __init__(s, pet, kind, x, y):
        s.pet, s.kind, s.x, s.y, s.vx, s.vy = pet, kind, x, y, 0.0, 0.0
        s.w, c = sprite_window(pet.root, s.SIZE, s.SIZE)
        s.cv = c
        px = lambda col, row, w, h, fill: c.create_rectangle(col * 2, row * 2, (col + w) * 2, (row + h) * 2,
                                                             fill=fill, outline="")
        rows = ((4, 9), (2, 11), (1, 12), (1, 12), (0, 13), (0, 13), (0, 13), (0, 13), (0, 13), (1, 12), (1, 12),
                (2, 11), (4, 9))
        for row, (a, b) in enumerate(rows):
            px(a, row, b - a, 1, "#4c8fd9" if kind == "ball" else "#c98b4a")
        if kind == "ball":
            px(3, 3, 2, 2, "white")
        else:
            for col, row in ((3, 4), (7, 3), (9, 7), (4, 8), (7, 10)):
                px(col, row, 2, 2, "#4a2a12")
        c.bind("<ButtonPress-1>", s.press)
        c.bind("<B1-Motion>", s.motion)
        c.bind("<ButtonRelease-1>", s.release)
        s.hold, s.hist, s.pos = None, [], None
        s.place()

    @property
    def ground(s):
        return s.pet.B - s.SIZE

    def on_ground(s):
        return s.y >= s.ground - 30

    def press(s, e):
        s.hold, s.hist = (e.x, e.y), []

    def motion(s, e):
        s.x, s.y = e.x_root - s.hold[0], e.y_root - s.hold[1]
        s.hist = (s.hist + [(e.x_root, e.y_root, time.perf_counter())])[-5:]
        s.place()

    def release(s, e):
        if len(s.hist) >= 2:
            (x0, y0, t0), (x1, y1, t1) = s.hist[0], s.hist[-1]
            dt = max(t1 - t0, 0.01)
            s.vx, s.vy = max(-1500, min(1500, (x1 - x0) / dt)), max(-1500, min(1500, (y1 - y0) / dt))
        s.hold = None

    def step(s, dt):
        if s.hold:
            return
        s.vy += G * dt
        s.x += s.vx * dt
        s.y += s.vy * dt
        if s.y >= s.ground:
            s.y, s.vy = s.ground, (-s.vy * 0.55 if s.vy > 100 else 0.0)
            s.vx *= 0.9 if s.vy else 0.97 ** (dt / 0.04)
        if s.x <= s.pet.L or s.x >= s.pet.R - s.SIZE:
            s.x, s.vx = max(s.pet.L, min(s.x, s.pet.R - s.SIZE)), -s.vx * 0.7
        s.vx *= 0.99 ** (dt / 0.04)
        s.place()

    def place(s):
        pos = (int(s.x), int(s.y))
        if pos != s.pos:
            s.pos = pos
            s.w.geometry(f"{s.SIZE}x{s.SIZE}+{pos[0]}+{pos[1]}")

    def destroy(s):
        s.w.destroy()


class Dozer:
    """Пиксельный бульдозер, за рулём Клодик в каске. Едет слева направо, отвал справа."""
    DW, DH, SPEED = 170, 85, 300.0

    def __init__(s, pet):
        s.pet = pet
        s.w, s.c = sprite_window(pet.root, s.DW, s.DH)
        s.x, s.y, s.key, s.pos = float(pet.L - s.DW), float(pet.B - s.DH), None, None
        s.place()

    def blade(s):
        return s.x + 150

    def place(s):
        pos = (int(s.x), int(s.y))
        if pos != s.pos:
            s.pos = pos
            s.w.geometry(f"{s.DW}x{s.DH}+{pos[0]}+{pos[1]}")

    def step(s, dt, t):
        s.x += s.SPEED * dt
        s.place()
        key = (int(t * 16) % 3, int(t * 6) % 3, (t % 3) < 0.15)
        if key == s.key:
            return
        s.key = key
        tread, smoke, blink = key
        c = s.c
        c.delete("all")
        px = lambda col, row, w, h, fill: c.create_rectangle(col * C, row * C, (col + w) * C, (row + h) * C,
                                                             fill=fill, outline="")
        px(3 + smoke % 2, 2 - smoke, 2, 2, "#c8c8c8")                     # дымок
        px(4, 3, 1, 5, "#444")                                            # труба
        px(11, 1, 11, 8, "#f2b705")                                       # кабина
        px(12, 2, 9, 5, "#bfe3ff")                                        # стекло
        px(13, 4, 7, 3, ORANGE)                                           # Клодик
        px(13, 3, 7, 1, "#ffcf33"); px(15, 2, 3, 1, "#ffcf33")            # каска
        if not blink:
            px(15, 5, 1, 1, EYE); px(18, 5, 1, 1, EYE)
        px(1, 8, 22, 5, "#f2b705"); px(1, 8, 22, 1, "#ffd23f")           # корпус
        px(23, 8, 1, 1, "#fff3c4")                                        # фара
        px(23, 10, 4, 2, "#d9a400")                                       # рычаг
        px(27, 5, 3, 12, "#8f8f8f"); px(29, 5, 1, 12, "#6a6a6a"); px(26, 15, 4, 2, "#6a6a6a")  # отвал
        px(1, 13, 24, 4, "#333")                                          # гусеница
        for wx in (3, 8, 13, 18, 22):
            px(wx, 14, 2, 2, "#666")
        for k in range(8):
            col = 1 + (k * 3 + tread) % 24
            px(col, 13, 1, 1, "#888"); px(col, 16, 1, 1, "#888")

    def destroy(s):
        s.w.destroy()


class Snow:
    """Снег по всему экрану. Окно пропускает клики насквозь и прячется, когда открыта полноэкранная игра."""
    N = 70

    def __init__(s, pet):
        s.pet = pet
        s.Wd, s.Hd = pet.R - pet.L, pet.B - pet.T
        s.w, s.c = sprite_window(pet.root, s.Wd, s.Hd)
        s.w.geometry(f"{s.Wd}x{s.Hd}+{pet.L}+{pet.T}")
        s.w.update_idletasks()
        hwnd = u32.GetParent(s.w.winfo_id()) or s.w.winfo_id()
        u32.SetWindowLongW(hwnd, -20, u32.GetWindowLongW(hwnd, -20) | 0x80000 | 0x20)   # layered + сквозь клики
        s.flakes = []
        for _ in range(s.N):
            sz = random.choice((2, 3, 3, 4))
            f = [random.uniform(0, s.Wd), random.uniform(0, s.Hd), random.uniform(25, 70), random.uniform(0, 6.3), sz,
                 s.c.create_rectangle(0, 0, sz, sz, fill="white", outline="")]
            s.flakes.append(f)
        s.hidden = False

    def step(s, dt):
        if s.hidden:
            return
        for f in s.flakes:
            f[1] += f[2] * dt
            f[3] += dt
            x = f[0] + math.sin(f[3]) * 12
            if f[1] > s.Hd:
                f[0], f[1] = random.uniform(0, s.Wd), -5
            s.c.coords(f[5], x, f[1], x + f[4], f[1] + f[4])

    def set_hidden(s, hide):
        if hide != s.hidden:
            s.hidden = hide
            s.w.withdraw() if hide else s.w.deiconify()

    def destroy(s):
        s.w.destroy()


class Buddy:
    """Друг Клодика: гуляет рядом, обнимается, через 3 минуты уходит."""
    HELLO = ["Привет, дружище!", "Как дела?", "Пошли гулять!", "Дай пять!", "Ты сегодня огонь"]
    REPLY = ["О, привет!", "Дай пять!", "Ура, друг!", "Нормально, гуляю"]

    def __init__(s, pet):
        s.pet = pet
        s.w, s.c = sprite_window(pet.root, W, H)
        s.bubble = Bubble(pet.root)
        left = pet.x > (pet.L + pet.R) / 2
        s.x, s.y, s.vy = float(pet.L + 30 if left else pet.R - W - 30), float(pet.T + 40), 0.0
        s.dir, s.state, s.timer, s.life, s.hearts = 1 if left else -1, "walk", 3.0, 180.0, 0.0
        s.leaving, s.key, s.pos, s.drag = False, None, None, None
        s.c.bind("<ButtonPress-1>", lambda e: setattr(s, "drag", (e.x, e.y)))
        s.c.bind("<B1-Motion>", s.motion)
        s.c.bind("<ButtonRelease-1>", lambda e: setattr(s, "drag", None))
        s.bubble.show("Привет! Я друг Клодика", 3)

    def motion(s, e):
        if s.drag:
            s.x, s.y, s.vy = e.x_root - s.drag[0], e.y_root - s.drag[1], 0.0

    def leave(s):
        if not s.leaving:
            s.leaving = True
            s.dir = -1 if s.x < (s.pet.L + s.pet.R) / 2 else 1
            s.bubble.show("Пока-пока!", 2)

    def update(s, dt, t):
        p = s.pet
        s.life -= dt
        s.hearts = max(0.0, s.hearts - dt)
        if s.life <= 0:
            s.leave()
        ground = p.B - H
        moving = False
        if s.drag:
            pass
        elif s.y < ground or s.vy < 0:
            s.vy += G * dt
            s.y = min(ground, s.y + s.vy * dt)
            if s.y >= ground:
                s.vy = 0.0
        elif s.leaving:
            s.x += s.dir * RUN * dt
            moving = True
            if s.x < p.L - W or s.x > p.R:
                return s.destroy()
        else:
            dist = p.x - s.x
            if s.state == "walk":
                s.x += s.dir * WALK * 1.2 * dt
                moving = True
            s.timer -= dt
            if s.timer <= 0:
                if abs(dist) > 220:
                    s.state, s.dir, s.timer = "walk", (1 if dist > 0 else -1), random.uniform(2, 4)
                else:
                    s.state, s.dir, s.timer = random.choice(("idle", "walk")), random.choice((-1, 1)), random.uniform(1.5, 4)
            if abs(dist) < 90 and not s.hearts and random.random() < dt / 6:
                s.hearts = p.hearts = 1.6
                s.bubble.show(random.choice(s.HELLO), 2.5)
                p.say(random.choice(s.REPLY), 2.5)
            s.x = max(p.L, min(s.x, p.R - W))
        pos = (int(s.x), int(s.y))
        if pos != s.pos:
            s.pos = pos
            s.w.geometry(f"{W}x{H}+{pos[0]}+{pos[1]}")
        s.bubble.follow(s.x + W / 2, s.y + 32, p.L, p.R)
        legs = int(t * 8) % 2 if moving else -1
        eyes = "closed" if s.hearts or (t % 3.7) < 0.15 else "open"
        sh = s.dir if moving else (1 if p.x > s.x else -1)
        key = (legs, eyes, sh, bool(s.hearts))
        if key != s.key:
            s.key = key
            s.c.delete("all")
            paint(s.c, OX, H - 10 * C, BUDDY, legs, 0, eyes, sh, -1, "none")
            if s.hearts:
                s.c.create_text(W / 2, H - 10 * C - 10, text="♥", fill="#e0445a", font=("Segoe UI", 12, "bold"))

    def destroy(s):
        s.w.destroy()
        s.bubble.w.destroy()
        s.pet.buddy = None
