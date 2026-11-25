"""Окно настроек Клодика: вкладки Голос, Характер, Мозг, Режимы, Память, Команды."""
from tkinter import ttk

from .common import *  # noqa: F401,F403
from .apps import save_learned
from .voice import VOICES
from .pet_fun import PERSONAS
from .pet_pc import write_json, MODES
from .pet_smart import MEMORY

HELP = """Позвать: «Клодик» (или зажми правый Ctrl). 20 секунд после команды — можно без имени.
Программы: открой Steam · закрой Дискорд · сверни/разверни/покажи окно · что можешь запустить
Окна: разгреби все окна (бульдозер) · закрой все окна · залезь на окно / слезь
Звук: громче / тише на 20 · выключи звук · пауза · следующий трек
Поиск: найди рецепт борща · найди файл отчёт · открой первый · открой загрузки · последняя загрузка
Дела: напомни завтра в 9 позвонить маме · засеки 5 минут · какие напоминания · отмени напоминание про маму
Список: запиши купить хлеб · что в списке · вычеркни хлеб · открой список
Счёт и язык: сколько будет 15% от 3400 · переведи доброе утро на английский
Буфер: переведи/сократи/исправь/объясни то, что скопировал · напечатай привет
Память: запомни, что я люблю… · что ты обо мне знаешь · забудь, что я… · итоги дня · утренняя сводка
Режимы: запомни режим работы: открой хром и фигму · режим работы · какие режимы
Комп: заблокируй · выключи комп через час (переспросит) · отмени выключение · что жрёт место
Игры: камень ножницы бумага · угадай число · викторина · лови печеньки · сколько я сегодня играл
Характер: будь дерзким / пиратом / как Джарвис / добрым · потанцуй · надень корону · включи снег
Голос: говори тише/громче · смени голос на Руслана · молчи · говори вслух · подстройся под мой голос
Ещё: покорми · мячик · позови друга · сфоткай · как там комп · иди спать · ко мне"""


def open_settings(p):
    if getattr(p, "settings_win", None) and p.settings_win.winfo_exists():
        return p.settings_win.lift()
    w = p.settings_win = tk.Toplevel(p.root)
    w.title("Клодик — настройки")
    w.attributes("-topmost", True)
    w.configure(bg=PAPER, padx=10, pady=10)
    nb = ttk.Notebook(w)
    nb.pack(fill="both", expand=True)

    def tab(name):
        f = tk.Frame(nb, bg=PAPER, padx=14, pady=10)
        nb.add(f, text=name)
        return f

    def title(f, text):
        tk.Label(f, text=text, bg=PAPER, fg=INK, font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(6, 2))

    # Голос
    f = tab("Голос")
    tk.Checkbutton(f, text="Слушать «Клодик» (микрофон, офлайн)", variable=p.listen_var, bg=PAPER,
                   command=lambda: p.set_listen(p.listen_var.get())).pack(anchor="w")
    tk.Checkbutton(f, text="Говорить вслух", variable=p.tts_var, bg=PAPER,
                   command=lambda: p.set_tts(p.tts_var.get())).pack(anchor="w")
    title(f, "Голос Клодика")
    for k, v in VOICES.items():
        tk.Radiobutton(f, text=v, value=k, variable=p.voice_var, bg=PAPER, command=lambda k=k: p.set_voice(k)).pack(anchor="w")
    title(f, "Громкость голоса")
    sc = tk.Scale(f, from_=10, to=100, orient="horizontal", variable=p.vol_var, bg=PAPER, length=260)
    sc.pack(anchor="w")
    sc.bind("<ButtonRelease-1>", lambda e: p.set_volume(p.vol_var.get()))
    tk.Button(f, text="Подстроить уши под мой голос", command=p.calibrate, relief="flat", bg=ORANGE, fg="white",
              padx=10).pack(anchor="w", pady=(10, 0))
    tk.Label(f, text="Говорить без имени: зажми правый Ctrl.", bg=PAPER, fg=DARK).pack(anchor="w", pady=(6, 0))

    # Характер
    f = tab("Характер")
    title(f, "Характер")
    for k, (name, _, _) in PERSONAS.items():
        tk.Radiobutton(f, text=name, value=k, variable=p.persona_var, bg=PAPER,
                       command=lambda k=k: p.set_persona(k)).pack(anchor="w")
    title(f, "Гардероб")
    for k, v in HATS.items():
        tk.Radiobutton(f, text=v, value=k, variable=p.hat_var, bg=PAPER, command=lambda k=k: p.set_hat(k)).pack(anchor="w")

    # Мозг
    f = tab("Мозг")
    title(f, "Чем Клодик болтает")
    for k, v in BRAINS.items():
        tk.Radiobutton(f, text=v, value=k, variable=p.brain_var, bg=PAPER, command=lambda k=k: p.set_brain(k)).pack(anchor="w")
    tk.Label(f, text="Команды (открыть, напомнить, посчитать…) работают без ИИ и без интернета.",
             bg=PAPER, fg=DARK, wraplength=380, justify="left").pack(anchor="w", pady=(8, 0))

    # Режимы
    f = tab("Режимы")
    lb = tk.Listbox(f, width=60, height=8)
    lb.pack(fill="x")

    def fill_modes():
        lb.delete(0, "end")
        for k, v in p.modes.items():
            lb.insert("end", f"{k}…  →  {v}")
    fill_modes()

    def del_mode():
        sel = lb.curselection()
        if sel:
            del p.modes[list(p.modes)[sel[0]]]
            write_json(MODES, p.modes)
            fill_modes()
    tk.Button(f, text="Удалить выбранный", command=del_mode, relief="flat").pack(anchor="w", pady=4)
    row = tk.Frame(f, bg=PAPER)
    row.pack(fill="x", pady=(6, 0))
    name, cmds = tk.Entry(row, width=12), tk.Entry(row, width=40)
    name.insert(0, "название")
    cmds.insert(0, "открой steam, открой discord")
    name.pack(side="left")
    cmds.pack(side="left", padx=4)
    tk.Button(row, text="Добавить", relief="flat", bg=ORANGE, fg="white",
              command=lambda: (p.save_mode(name.get(), cmds.get()), fill_modes())).pack(side="left")

    # Память
    f = tab("Память")
    title(f, "Что я знаю о тебе")
    mem = tk.Listbox(f, width=60, height=7)
    mem.pack(fill="x")
    title(f, "Выученные фразы (как я тебя понимаю)")
    lrn = tk.Listbox(f, width=60, height=6)
    lrn.pack(fill="x")

    def fill_mem():
        mem.delete(0, "end")
        for x in p.memory:
            mem.insert("end", x["fact"])
        lrn.delete(0, "end")
        for k, v in p.learned.items():
            lrn.insert("end", f"«{k}» → {v}")
    fill_mem()

    def del_fact():
        sel = mem.curselection()
        if sel:
            p.memory.pop(sel[0])
            write_json(MEMORY, p.memory)
            fill_mem()

    def del_learned():
        sel = lrn.curselection()
        if sel:
            p.learned.pop(list(p.learned)[sel[0]])
            p._vocab = None
            save_learned(p.learned)
            fill_mem()
    row = tk.Frame(f, bg=PAPER)
    row.pack(anchor="w", pady=4)
    tk.Button(row, text="Забыть факт", command=del_fact, relief="flat").pack(side="left")
    tk.Button(row, text="Забыть фразу", command=del_learned, relief="flat").pack(side="left", padx=4)

    # Команды
    f = tab("Команды")
    t = tk.Text(f, width=92, height=20, wrap="word", font=("Segoe UI", 9), bg="white", relief="flat")
    t.insert("1.0", HELP)
    t.config(state="disabled")
    t.pack(fill="both", expand=True)
    return w
