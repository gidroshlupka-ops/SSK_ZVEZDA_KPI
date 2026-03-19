"""\nizolde.py — UI Engine v5
SSK Zvezda | The First Whistle
─────────────────────────────────────────────────────────────────
Исправления v5:
 • Топбар — фиксированная высота, ровный текст
 • Настройки — CTkComboBox со светлыми стрелками
 • Настройки — поля всегда заполнены из config.ini
 • Цветные графики (зелёный/янтарь/красный)
 • Realtime-обновление таблиц при изменении данных в Supabase
 • Вкладка Справка — руководство пользователя
 • Telegram-алерты автоматически, не по кнопке
 • Импорт SQLite → Supabase в один клик
"""
import requests  # Уберет ошибку "Unresolved reference 'requests'"
import sys, logging, threading, configparser
from pathlib import Path
from datetime import datetime
from tkinter import filedialog
import tkinter as tk

import customtkinter as ctk

log = logging.getLogger("izolde")
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# ══════════════════════════════════════════════════════════════════════════════
# ПАЛИТРА
# ══════════════════════════════════════════════════════════════════════════════
BG         = "#FFFFFF"
BG_PANEL   = "#F5F5F5"
BG_CARD    = "#FAFAFA"
BG_ROW_A   = "#FFFFFF"
BG_ROW_B   = "#F7F7F7"
BG_ROW_SEL = "#E8E8E8"
BG_HDR     = "#1A1A1A"
BG_LOW     = "#FFF0F0"
BG_TOPBAR  = "#1A1A1A"
BG_SIDEBAR = "#F2F2F2"
BG_INPUT   = "#FFFFFF"
BORDER     = "#DDDDDD"
BORDER_D   = "#1A1A1A"
BORDER_MID = "#AAAAAA"
TEXT       = "#1A1A1A"
TEXT_MID   = "#555555"
TEXT_SOFT  = "#888888"
TEXT_INV   = "#FFFFFF"
TEXT_HDR   = "#FFFFFF"
CLR_OK     = "#1A7A3A"
CLR_WARN   = "#8A5A00"
CLR_CRIT   = "#AA1A1A"
CLR_BLUE   = "#1A4A8A"
NAV_SEL    = "#E4E4E4"

# Графики — цветная схема
CHART_GREEN  = "#27AE60"
CHART_AMBER  = "#E67E22"
CHART_RED    = "#E74C3C"
CHART_BLUE   = "#2980B9"
CHART_PURPLE = "#8E44AD"
CHART_TEAL   = "#16A085"
CHART_GRAY   = "#7F8C8D"

FONT_MAIN  = ("Arial", 12)
FONT_BOLD  = ("Arial", 12, "bold")
FONT_SMALL = ("Arial", 10)
FONT_SM_B  = ("Arial", 10, "bold")
FONT_MICRO = ("Arial", 9)
FONT_HDR   = ("Arial", 14, "bold")
FONT_TITLE = ("Arial", 17, "bold")
FONT_INV_B = ("Arial", 13, "bold")

def Fc(size=12, bold=False):
    return ctk.CTkFont(family="Arial", size=size, weight="bold" if bold else "normal")


# ── Кнопки ────────────────────────────────────────────────────────────────────
def Btn(parent, text, cmd, w=120, h=32, style="primary"):
    S = {
        "primary": dict(fg_color="#1A1A1A", hover_color="#333",    text_color="#FFF",    border_width=0),
        "ghost":   dict(fg_color="#FFF",    hover_color="#F0F0F0", text_color="#1A1A1A", border_width=1, border_color="#1A1A1A"),
        "danger":  dict(fg_color="#FFF",    hover_color="#FFF0F0", text_color="#AA1A1A", border_width=1, border_color="#AA1A1A"),
        "subtle":  dict(fg_color="#F0F0F0", hover_color="#E4E4E4", text_color="#555",    border_width=1, border_color="#CCC"),
        "green":   dict(fg_color="#1A7A3A", hover_color="#155A2A", text_color="#FFF",    border_width=0),
    }
    s = S.get(style, S["primary"])
    return ctk.CTkButton(parent, text=text, command=cmd, width=w, height=h,
                         font=Fc(11, bold=True), corner_radius=3, **s)


def Divider(parent, padx=0, pady=4):
    tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", padx=padx, pady=pady)


def SectionLbl(parent, text):
    f = tk.Frame(parent, bg=BG)
    f.pack(fill="x", padx=20, pady=(18, 6))
    tk.Label(f, text=text.upper(), bg=BG, fg=TEXT_MID, font=FONT_SM_B).pack(side="left")
    tk.Frame(f, bg=BORDER, height=1).pack(side="left", fill="x", expand=True, padx=(10,0), pady=7)


def Entry(parent, var, show="", w=320, **kw):
    e = ctk.CTkEntry(parent, textvariable=var, width=w, height=34, show=show,
                     fg_color=BG_INPUT, border_color=BORDER_D,
                     text_color=TEXT, font=Fc(12), **kw)
    _patch_entry_clipboard(e)
    return e


def _patch_entry_clipboard(widget):
    """
    Патч Ctrl+C/V/X/A для CTkEntry на Windows.
    Работает даже в дочерних окнах (CTkToplevel с grab_set).
    """
    def _apply():
        try:
            inner = widget._entry  # tk.Entry внутри CTkEntry
        except AttributeError:
            return

        inner.configure(insertbackground=TEXT)

        # Прямые биндинги на внутренний tk.Entry
        def _paste(e):
            try:
                inner.event_generate("<<Paste>>")
            except Exception:
                try:
                    txt = inner.clipboard_get()
                    try:    inner.delete("sel.first", "sel.last")
                    except Exception: pass
                    inner.insert("insert", txt)
                except Exception:
                    pass
            return "break"

        def _copy(e):
            inner.event_generate("<<Copy>>")
            return "break"

        def _cut(e):
            inner.event_generate("<<Cut>>")
            return "break"

        def _selall(e):
            inner.select_range(0, "end")
            inner.icursor("end")
            return "break"

        for seq, fn in [
            ("<Control-v>", _paste), ("<Control-V>", _paste),
            ("<Control-c>", _copy),  ("<Control-C>", _copy),
            ("<Control-x>", _cut),   ("<Control-X>", _cut),
            ("<Control-a>", _selall),("<Control-A>", _selall),
            ("<Control-z>", lambda e: (inner.event_generate("<<Undo>>"), "break")[1]),
        ]:
            inner.bind(seq, fn, add=False)
            widget.bind(seq, fn, add=False)  # и на сам CTkEntry тоже

        # Правый клик — контекстное меню
        def _ctx(e):
            try:
                m = tk.Menu(inner, tearoff=0)
                m.add_command(label="Вырезать",     command=lambda: inner.event_generate("<<Cut>>"))
                m.add_command(label="Копировать",   command=lambda: inner.event_generate("<<Copy>>"))
                m.add_command(label="Вставить",     command=lambda: _paste(None))
                m.add_separator()
                m.add_command(label="Выделить всё", command=lambda: _selall(None))
                m.tk_popup(e.x_root, e.y_root)
            except Exception:
                pass
        inner.bind("<Button-3>", _ctx, add=False)

    # Применяем сразу + повторно после отрисовки
    def _schedule():
        _apply()
        try:
            root = widget.winfo_toplevel()
            root.after(50,  _apply)
            root.after(200, _apply)
        except Exception:
            pass

    widget.bind("<Map>", lambda e: _schedule(), add="+")
    try:
        widget.after(50, _apply)
    except Exception:
        pass

def Combo(parent, var, values, w=280):
    """ComboBox с белыми стрелками (button_color=белый, button_hover=серый)."""
    return ctk.CTkComboBox(
        parent, variable=var, values=values, width=w, height=34,
        fg_color=BG_INPUT, border_color=BORDER_D,
        text_color=TEXT, font=Fc(12),
        button_color="#555555",
        button_hover_color="#333333",
        dropdown_fg_color="#FFFFFF",
        dropdown_text_color=TEXT,
        dropdown_hover_color="#F0F0F0",
    )


# ══════════════════════════════════════════════════════════════════════════════
# SCROLL UTILS
# ══════════════════════════════════════════════════════════════════════════════
def bind_scroll_tree(widget, canvas):
    def _w(e):
        if e.num == 4:   canvas.yview_scroll(-3, "units")
        elif e.num == 5: canvas.yview_scroll( 3, "units")
        else:            canvas.yview_scroll(-1*(e.delta//120), "units")
    widget.bind("<MouseWheel>", _w, add="+")
    widget.bind("<Button-4>",   _w, add="+")
    widget.bind("<Button-5>",   _w, add="+")
    for child in widget.winfo_children():
        bind_scroll_tree(child, canvas)


def make_scroll_frame(parent):
    outer  = tk.Frame(parent, bg=BG)
    canvas = tk.Canvas(outer, bg=BG, highlightthickness=0, bd=0)
    vsb    = tk.Scrollbar(outer, orient="vertical", command=canvas.yview,
                          width=10, bg=BG_PANEL, troughcolor=BG, relief="flat", bd=0)
    vsb.pack(side="right", fill="y")
    canvas.pack(fill="both", expand=True)
    canvas.configure(yscrollcommand=vsb.set)
    inner = tk.Frame(canvas, bg=BG)
    win   = canvas.create_window((0,0), window=inner, anchor="nw")
    inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>", lambda e: canvas.itemconfig(win, width=e.width))
    def _w(e):
        if e.num==4:   canvas.yview_scroll(-3,"units")
        elif e.num==5: canvas.yview_scroll( 3,"units")
        else:          canvas.yview_scroll(-1*(e.delta//120),"units")
    for w in (canvas, inner, outer):
        w.bind("<MouseWheel>", _w, add="+")
        w.bind("<Button-4>",   _w, add="+")
        w.bind("<Button-5>",   _w, add="+")
    inner._canvas      = canvas
    inner._bind_scroll = lambda w: bind_scroll_tree(w, canvas)
    return outer, inner, canvas


# ══════════════════════════════════════════════════════════════════════════════
# INFINITE TABLE
# ══════════════════════════════════════════════════════════════════════════════
class InfiniteTable(tk.Frame):
    PAGE_SIZE = 50
    ROW_H     = 28

    def __init__(self, parent, columns, load_fn, count_fn=None,
                 color_fn=None, on_select=None, **kw):
        super().__init__(parent, bg=BG, **kw)
        self.columns   = columns
        self.load_fn   = load_fn
        self.count_fn  = count_fn
        self.color_fn  = color_fn
        self.on_select = on_select
        self._rows     = []
        self._total    = 0
        self._loading  = False
        self._sel_fr   = None
        self._sel_bg   = None
        self._sel_id   = None
        self._search   = ""
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg=BG_HDR, height=self.ROW_H)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        for title, w in self.columns:
            tk.Label(hdr, text=title, width=1, bg=BG_HDR, fg=TEXT_HDR,
                     font=FONT_SM_B, anchor="w", padx=8
                     ).pack(side="left", fill="y", ipadx=max(0, w//2-6))

        wrap = tk.Frame(self, bg=BG); wrap.pack(fill="both", expand=True)
        self._canvas = tk.Canvas(wrap, bg=BG, highlightthickness=0, bd=0)
        vsb = tk.Scrollbar(wrap, orient="vertical", command=self._on_vscroll,
                           width=10, bg=BG_PANEL, troughcolor=BG, relief="flat", bd=0)
        vsb.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)
        self._canvas.configure(yscrollcommand=vsb.set)
        self._body = tk.Frame(self._canvas, bg=BG)
        self._win  = self._canvas.create_window((0,0), window=self._body, anchor="nw")
        self._body.bind("<Configure>", lambda e: self._canvas.configure(
            scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>", lambda e: self._canvas.itemconfig(
            self._win, width=e.width))
        self._status = tk.Label(self, text="", bg=BG_PANEL, fg=TEXT_SOFT,
                                font=FONT_MICRO, anchor="e", padx=8)
        self._status.pack(fill="x", side="bottom")
        self._bind_wheel(self._canvas)
        self._bind_wheel(self._body)
        self._bind_wheel(self)

    def _bind_wheel(self, w):
        def _f(e):
            if e.num==4:   self._canvas.yview_scroll(-3,"units")
            elif e.num==5: self._canvas.yview_scroll( 3,"units")
            else:          self._canvas.yview_scroll(-1*(e.delta//120),"units")
            self.after(80, self._check_load_more)
        w.bind("<MouseWheel>", _f, add="+")
        w.bind("<Button-4>",   _f, add="+")
        w.bind("<Button-5>",   _f, add="+")

    def _on_vscroll(self, *args):
        self._canvas.yview(*args)
        self.after(80, self._check_load_more)

    def _check_load_more(self):
        if self._loading or len(self._rows) >= self._total > 0: return
        try:
            _, bot = self._canvas.yview()
            if bot >= 0.78: self._load_more()
        except Exception: pass

    def reload(self, search=""):
        self._search = search
        self._rows   = []
        self._total  = 0
        for w in self._body.winfo_children(): w.destroy()
        self._sel_fr = self._sel_id = None
        self._canvas.yview_moveto(0)
        self._load_more()
        if self.count_fn:
            threading.Thread(target=self._bg_count, daemon=True).start()

    def _bg_count(self):
        n = self.count_fn(self._search)
        self._total = n
        self.after(0, self._upd_status)

    def _load_more(self):
        if self._loading: return
        self._loading = True
        offset = len(self._rows)
        search = self._search

        def _do():
            try:
                rows = self.load_fn(search, self.PAGE_SIZE, offset)
                self.after(0, self._append, rows)
            except Exception as e:
                log.error("load_more: %s", e)
                self._loading = False
        threading.Thread(target=_do, daemon=True).start()

    def _append(self, new_rows):
        if not new_rows:
            self._loading = False
            if not self._total and self.count_fn:
                threading.Thread(target=self._bg_count, daemon=True).start()
            return
        base = len(self._rows)
        self._rows.extend(new_rows)
        for i, row in enumerate(new_rows):
            gi = base + i
            colors = self.color_fn(gi, row) if self.color_fn else None
            bg  = colors[0] if colors else (BG_ROW_A if gi%2==0 else BG_ROW_B)
            fgs = colors[1] if colors else [TEXT]*len(self.columns)
            fr  = tk.Frame(self._body, bg=bg, height=self.ROW_H)
            fr.pack(fill="x"); fr.pack_propagate(False)
            row_id = row[0]
            for j, ((_, w), val, fg) in enumerate(zip(self.columns, row, fgs)):
                lbl = tk.Label(fr, text=str(val), bg=bg, fg=fg,
                               font=FONT_SMALL, anchor="w", padx=8,
                               width=1, cursor="hand2")
                lbl.pack(side="left", fill="y", ipadx=max(0, w//2-6))
                lbl.bind("<Button-1>", lambda e, r=row_id, f=fr, b=bg: self._click(r,f,b))
                self._bind_wheel(lbl)
            fr.bind("<Button-1>", lambda e, r=row_id, f=fr, b=bg: self._click(r,f,b))
            self._bind_wheel(fr)
        self._loading = False
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        self._upd_status()
        if not self._total and self.count_fn:
            threading.Thread(target=self._bg_count, daemon=True).start()

    def _click(self, row_id, frame, orig_bg):
        if self._sel_fr and self._sel_fr.winfo_exists():
            self._sel_fr.configure(bg=self._sel_bg)
            for w in self._sel_fr.winfo_children():
                if isinstance(w, tk.Label): w.configure(bg=self._sel_bg)
        self._sel_fr = frame; self._sel_bg = orig_bg; self._sel_id = row_id
        frame.configure(bg=BG_ROW_SEL)
        for w in frame.winfo_children():
            if isinstance(w, tk.Label): w.configure(bg=BG_ROW_SEL)
        if self.on_select: self.on_select(row_id)

    def _upd_status(self):
        shown = len(self._rows); total = self._total
        self._status.configure(
            text=f"Показано: {shown} из {total}" if total else f"Записей: {shown}")

    @property
    def selected_id(self): return self._sel_id


# ══════════════════════════════════════════════════════════════════════════════
# VTable (ресурсы, KPI и т.д.)
# ══════════════════════════════════════════════════════════════════════════════
class VTable(tk.Frame):
    ROW_H = 28

    def __init__(self, parent, columns, on_select=None, **kw):
        super().__init__(parent, bg=BG, **kw)
        self.columns   = columns
        self.on_select = on_select
        self._sel_fr = self._sel_bg = self._sel_id = None
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg=BG_HDR, height=self.ROW_H)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        for title, w in self.columns:
            tk.Label(hdr, text=title, width=1, bg=BG_HDR, fg=TEXT_HDR,
                     font=FONT_SM_B, anchor="w", padx=8
                     ).pack(side="left", fill="y", ipadx=max(0, w//2-6))
        wrap = tk.Frame(self, bg=BG); wrap.pack(fill="both", expand=True)
        self._canvas = tk.Canvas(wrap, bg=BG, highlightthickness=0, bd=0)
        vsb = tk.Scrollbar(wrap, orient="vertical", command=self._canvas.yview,
                           width=10, bg=BG_PANEL, troughcolor=BG, relief="flat", bd=0)
        vsb.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)
        self._canvas.configure(yscrollcommand=vsb.set)
        self._body = tk.Frame(self._canvas, bg=BG)
        self._win  = self._canvas.create_window((0,0), window=self._body, anchor="nw")
        self._body.bind("<Configure>", lambda e: self._canvas.configure(
            scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>", lambda e: self._canvas.itemconfig(
            self._win, width=e.width))
        self._bw(self._canvas); self._bw(self._body); self._bw(self)

    def _bw(self, w):
        w.bind("<MouseWheel>", lambda e: self._canvas.yview_scroll(-1*(e.delta//120),"units"), add="+")
        w.bind("<Button-4>",   lambda e: self._canvas.yview_scroll(-3,"units"), add="+")
        w.bind("<Button-5>",   lambda e: self._canvas.yview_scroll( 3,"units"), add="+")

    def render(self, rows, color_fn=None):
        for w in self._body.winfo_children(): w.destroy()
        self._sel_fr = self._sel_id = None
        for i, row in enumerate(rows):
            colors = color_fn(i, row) if color_fn else None
            bg     = colors[0] if colors else (BG_ROW_A if i%2==0 else BG_ROW_B)
            fgs    = colors[1] if colors else [TEXT]*len(self.columns)
            fr = tk.Frame(self._body, bg=bg, height=self.ROW_H)
            fr.pack(fill="x"); fr.pack_propagate(False)
            row_id = row[0]
            for j, ((_, w), val, fg) in enumerate(zip(self.columns, row, fgs)):
                lbl = tk.Label(fr, text=str(val), bg=bg, fg=fg,
                               font=FONT_SMALL, anchor="w", padx=8, width=1, cursor="hand2")
                lbl.pack(side="left", fill="y", ipadx=max(0, w//2-6))
                lbl.bind("<Button-1>", lambda e, r=row_id, f=fr, b=bg: self._click(r,f,b))
                self._bw(lbl)
            fr.bind("<Button-1>", lambda e, r=row_id, f=fr, b=bg: self._click(r,f,b))
            self._bw(fr)
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        self._canvas.yview_moveto(0)

    def _click(self, rid, frame, orig_bg):
        if self._sel_fr and self._sel_fr.winfo_exists():
            self._sel_fr.configure(bg=self._sel_bg)
            for w in self._sel_fr.winfo_children():
                if isinstance(w, tk.Label): w.configure(bg=self._sel_bg)
        self._sel_fr = frame; self._sel_bg = orig_bg; self._sel_id = rid
        frame.configure(bg=BG_ROW_SEL)
        for w in frame.winfo_children():
            if isinstance(w, tk.Label): w.configure(bg=BG_ROW_SEL)
        if self.on_select: self.on_select(rid)

    @property
    def selected_id(self): return self._sel_id


# ══════════════════════════════════════════════════════════════════════════════
# LOGIN
# ══════════════════════════════════════════════════════════════════════════════
class LoginWindow(ctk.CTk):
    def __init__(self, cfg, on_success):
        super().__init__()
        self.cfg = cfg; self.on_success = on_success
        self.title("ССК Звезда — Вход")
        self.geometry("420x460"); self.resizable(False, False)
        self.configure(fg_color=BG)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self._build()

    def _build(self):
        # Ровный топбар
        top = tk.Frame(self, bg=BG_TOPBAR, height=56)
        top.pack(fill="x"); top.pack_propagate(False)
        tk.Label(top, text="ССК «ЗВЕЗДА»", bg=BG_TOPBAR, fg=TEXT_INV,
                 font=("Arial", 16, "bold")).pack(expand=True)

        body = tk.Frame(self, bg=BG)
        body.pack(expand=True, fill="both", padx=40, pady=16)
        tk.Label(body, text="Вход в систему учёта KPI", bg=BG,
                 fg=TEXT_MID, font=FONT_MAIN).pack(pady=(0,16))

        def fld(lbl, var, show=""):
            tk.Label(body, text=lbl, bg=BG, fg=TEXT,
                     font=FONT_SM_B, anchor="w").pack(fill="x")
            e = ctk.CTkEntry(body, textvariable=var, height=36, show=show,
                             corner_radius=3, fg_color=BG_INPUT,
                             border_color=BORDER_D, text_color=TEXT, font=Fc(12))
            e.pack(fill="x", pady=(2, 10))
            _patch_entry_clipboard(e)
            return e

        self.v_u = ctk.StringVar(value="admin")
        self.v_p = ctk.StringVar(value="admin")
        fld("Логин", self.v_u)
        pe = fld("Пароль", self.v_p, "•")

        self.v_r = ctk.BooleanVar()
        ctk.CTkCheckBox(body, text="Запомнить меня", variable=self.v_r,
                        font=Fc(11), fg_color=BORDER_D, hover_color=TEXT_MID,
                        checkmark_color=BG, border_color=BORDER,
                        text_color=TEXT_MID).pack(pady=4)

        self.st = tk.Label(body, text="", bg=BG, fg=CLR_CRIT, font=FONT_SMALL)
        self.st.pack(pady=4)
        Btn(body, "Войти", self._login, w=300, h=40).pack(pady=4, fill="x")
        pe.bind("<Return>", lambda e: self._login())

    def _login(self):
        from modules.rubuska import verify_login, save_session
        u, p = self.v_u.get().strip(), self.v_p.get().strip()
        if not u or not p: self.st.configure(text="Заполните все поля."); return
        self.st.configure(text="Проверка...", fg=TEXT_MID); self.update()

        def _do():
            ok = verify_login(u, p)
            def _cb():
                if ok:
                    if self.v_r.get():
                        save_session(u, self.cfg.getboolean("app","hardware_bind",fallback=False))
                    self.destroy(); self.on_success(u)
                else:
                    self.st.configure(text="Неверный логин или пароль.", fg=CLR_CRIT)
                    self.v_p.set("")
            self.after(0, _cb)
        threading.Thread(target=_do, daemon=True).start()


# ══════════════════════════════════════════════════════════════════════════════
# MAIN APP
# ══════════════════════════════════════════════════════════════════════════════
class MainApp(ctk.CTk):
    def __init__(self, username, cfg):
        super().__init__()
        self.username = username; self.cfg = cfg
        self._tray = None; self._worker = None
        self._is_true_fullscreen = False
        self._prev_geometry = None
        self.title("ССК Звезда — Система учёта KPI")
        self.geometry("1380x860"); self.minsize(1200, 700)
        self.configure(fg_color=BG)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        _ico = Path(__file__).parent.parent / "assets" / "izolde.ico"
        if _ico.exists():
            try: self.iconbitmap(str(_ico))
            except: pass
        self._pages = {}
        self._current_page = None
        self._build()
        # F11 — настоящий fullscreen поверх панели задач, Esc — выход
        self.bind("<F11>", lambda e: self._toggle_true_fullscreen())
        self.bind("<Escape>", lambda e: self._exit_true_fullscreen())
        self.after(400, self._start_engine)
        self.after(3000, self._refresh_badge)

    def _toggle_true_fullscreen(self):
        if self._is_true_fullscreen:
            self._exit_true_fullscreen()
        else:
            self._enter_true_fullscreen()

    def _enter_true_fullscreen(self):
        if self._is_true_fullscreen:
            return
        try:
            self._prev_geometry = self.geometry()
        except Exception:
            self._prev_geometry = None
        self._is_true_fullscreen = True
        try:
            self.overrideredirect(True)
        except Exception:
            pass
        try:
            w = self.winfo_screenwidth()
            h = self.winfo_screenheight()
            self.geometry(f"{w}x{h}+0+0")
        except Exception:
            pass
        try:
            # на Windows помогает реально перекрыть панель задач
            self.attributes("-topmost", True)
            self.lift()
            self.focus_force()
        except Exception:
            pass

    def _exit_true_fullscreen(self):
        if not self._is_true_fullscreen:
            return
        self._is_true_fullscreen = False
        try:
            self.attributes("-topmost", False)
        except Exception:
            pass
        try:
            self.overrideredirect(False)
        except Exception:
            pass
        try:
            if self._prev_geometry:
                self.geometry(self._prev_geometry)
        except Exception:
            pass

    # ── Layout ────────────────────────────────────────────────────────────────
    def _build(self):
        # ── Topbar — строго фиксированная высота 52px
        top = tk.Frame(self, bg=BG_TOPBAR, height=52)
        top.pack(fill="x"); top.pack_propagate(False)

        # Левая часть — название
        tk.Label(top, text="ССК «ЗВЕЗДА»  —  СИСТЕМА УЧЁТА KPI",
                 bg=BG_TOPBAR, fg=TEXT_INV,
                 font=("Arial", 13, "bold")).place(x=20, y=0, height=52)

        # Правая часть — уведомления + пользователь
        self._usr_lbl = tk.Label(top, text="", bg=BG_TOPBAR,
                                 fg="#BBBBBB", font=("Arial", 10))
        self._usr_lbl.place(relx=1.0, x=-150, y=0, height=52, anchor="ne")

        bell_f = tk.Frame(top, bg=BG_TOPBAR)
        bell_f.place(relx=1.0, x=-16, y=0, height=52, anchor="ne")
        self._bell = tk.Label(bell_f, text="🔔", bg=BG_TOPBAR,
                              fg=TEXT_INV, font=("Segoe UI", 14), cursor="hand2")
        self._bell.pack(side="left", pady=14)
        self._bell_cnt = tk.Label(bell_f, text="", bg=BG_TOPBAR,
                                  fg="#FF6B6B", font=FONT_SM_B)
        self._bell_cnt.pack(side="left")
        self._bell.bind("<Button-1>", lambda e: self._show("notifications"))

        threading.Thread(target=self._load_uname, daemon=True).start()

        # Разделитель
        tk.Frame(self, bg=BORDER_D, height=1).pack(fill="x")

        body = tk.Frame(self, bg=BG); body.pack(fill="both", expand=True)
        self._build_sidebar(body)
        self.content = tk.Frame(body, bg=BG)
        self.content.pack(fill="both", expand=True, side="left")
        self._show("dashboard")

    def _load_uname(self):
        from modules.rubuska import get_admin
        a    = get_admin(self.username)
        name = a["full_name"] if a and a.get("full_name") else self.username
        self.after(0, lambda: self._usr_lbl.configure(text=f"  {name}  "))

    def _build_sidebar(self, parent):
        sb = tk.Frame(parent, bg=BG_SIDEBAR, width=196)
        sb.pack(fill="y", side="left"); sb.pack_propagate(False)
        tk.Frame(sb, bg=BORDER, width=1).pack(fill="y", side="right")
        tk.Label(sb, text="НАВИГАЦИЯ", bg=BG_SIDEBAR, fg=TEXT_SOFT,
                 font=("Arial", 9, "bold")).pack(pady=(16, 8), padx=14, anchor="w")

        self._nav = {}
        nav = [("dashboard","Дашборд"), ("employees","Сотрудники"),
               ("resources","Ресурсы"), ("kpi","KPI"),
               ("reports","Отчёты"), ("council","Совет"),
               ("notifications","Уведомления"), ("docs","Справка"),
               ("settings","Настройки")]
        for key, lbl in nav:
            b = tk.Label(sb, text=f"   {lbl}", bg=BG_SIDEBAR, fg=TEXT,
                         font=FONT_MAIN, anchor="w", cursor="hand2", height=2)
            b.pack(fill="x")
            b.bind("<Button-1>", lambda e, k=key: self._show(k))
            b.bind("<Enter>",    lambda e, w=b, k=key: w.configure(
                bg=NAV_SEL if k != self._current_page else NAV_SEL))
            b.bind("<Leave>",    lambda e, w=b, k=key: w.configure(
                bg=NAV_SEL if k == self._current_page else BG_SIDEBAR))
            self._nav[key] = b

        tk.Frame(sb, bg=BORDER, height=1).pack(fill="x", side="bottom")
        tk.Label(sb, text="v5.0  ·  ССК Звезда", bg=BG_SIDEBAR,
                 fg=TEXT_SOFT, font=("Arial", 8)).pack(
            side="bottom", padx=14, pady=10, anchor="w")

    def _show(self, key):
        self._current_page = key
        for k, b in self._nav.items():
            b.configure(bg=NAV_SEL if k==key else BG_SIDEBAR,
                        fg=TEXT if k==key else TEXT_MID,
                        font=FONT_BOLD if k==key else FONT_MAIN)
        for p in self._pages.values(): p.pack_forget()
        # Настройки пересоздаём каждый раз — иначе поля не обновляются
        if key == "settings" and "settings" in self._pages:
            self._pages["settings"].destroy()
            del self._pages["settings"]
        builders = {
            "dashboard":     self._build_dashboard,
            "employees":     self._build_employees,
            "resources":     self._build_resources,
            "kpi":           self._build_kpi,
            "reports":       self._build_reports,
            "council":       self._build_council,
            "notifications": self._build_notifs_page,
            "docs":          self._build_docs,
            "settings":      self._build_settings,
        }
        if key not in self._pages:
            if key in builders: builders[key]()
        if key in self._pages: self._pages[key].pack(fill="both", expand=True)

    def _page(self, key, title, subtitle=""):
        p  = tk.Frame(self.content, bg=BG)
        self._pages[key] = p
        ph = tk.Frame(p, bg=BG, height=58); ph.pack(fill="x"); ph.pack_propagate(False)
        tk.Frame(ph, bg=BG_TOPBAR, width=4).pack(fill="y", side="left")
        ri = tk.Frame(ph, bg=BG); ri.pack(side="left", fill="y", padx=16)
        tk.Label(ri, text=title,    bg=BG, fg=TEXT, font=FONT_TITLE).pack(anchor="w", pady=(10,0))
        if subtitle:
            tk.Label(ri, text=subtitle, bg=BG, fg=TEXT_SOFT, font=FONT_SMALL).pack(anchor="w")
        tk.Frame(p, bg=BORDER, height=1).pack(fill="x")
        return p

    def _toolbar(self, parent):
        tb = tk.Frame(parent, bg=BG_PANEL, height=48)
        tb.pack(fill="x"); tb.pack_propagate(False)
        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x")
        return tb

    # ══════════════════════════════════════════════════════════════════════════
    # DASHBOARD — цветные графики
    # ══════════════════════════════════════════════════════════════════════════
    def _build_dashboard(self):
        p = self._page("dashboard","Дашборд","Аналитика и сводные показатели")
        outer, scroll, canvas = make_scroll_frame(p)
        outer.pack(fill="both", expand=True)

        cards = tk.Frame(scroll, bg=BG); cards.pack(fill="x", padx=20, pady=(16,8))
        self._dcards = {}
        CARD_COLORS = [("#27AE60","#E8F8F0"),("#E74C3C","#FEF0EE"),
                       ("#2980B9","#EBF5FB"),("#E67E22","#FEF9E7")]
        for (key, lbl, ico), (acc, light) in zip(
            [("employees","Сотрудников","👥"),("low","На минимуме","⚠"),
             ("kpi_avg","Средний KPI","📊"),("notifs","Уведомлений","🔔")],
            CARD_COLORS):
            c = tk.Frame(cards, bg=light, highlightthickness=1,
                         highlightbackground=acc)
            c.pack(side="left", expand=True, fill="x", padx=6)
            tk.Frame(c, bg=acc, height=3).pack(fill="x")
            tk.Label(c, text=ico, bg=light, font=("Segoe UI",20)).pack(pady=(10,2))
            v = tk.Label(c, text="—", bg=light, fg=acc, font=("Arial",22,"bold"))
            v.pack()
            tk.Label(c, text=lbl, bg=light, fg=TEXT_MID, font=FONT_SMALL).pack(pady=(2,10))
            self._dcards[key] = v

        grid = tk.Frame(scroll, bg=BG); grid.pack(fill="x", padx=20, pady=8)
        self._clbls = {}
        for key, title, row, col in [("bar","KPI по отделам",0,0),
                                      ("line","Динамика за 6 месяцев",0,1),
                                      ("pie","Структура персонала",1,0),
                                      ("top","Топ-8 сотрудников",1,1)]:
            cell = tk.Frame(grid, bg=BG_CARD, highlightthickness=1,
                            highlightbackground=BORDER)
            cell.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
            tk.Frame(cell, bg=BG_TOPBAR, height=2).pack(fill="x")
            tk.Label(cell, text=title, bg=BG_CARD, fg=TEXT,
                     font=FONT_BOLD).pack(pady=(8,4), padx=8, anchor="w")
            lbl = tk.Label(cell, text="Загрузка...", bg=BG_CARD,
                           fg=TEXT_SOFT, font=FONT_SMALL)
            lbl.pack(expand=True, pady=(0,10))
            self._clbls[key] = lbl
        grid.grid_columnconfigure(0, weight=1); grid.grid_columnconfigure(1, weight=1)
        grid.grid_rowconfigure(0, weight=1); grid.grid_rowconfigure(1, weight=1)

        Btn(scroll,"⟳  Обновить дашборд",self._refresh_dashboard,
            w=200,h=34,style="ghost").pack(pady=12)
        scroll._bind_scroll(scroll)
        self._refresh_dashboard()

    def _refresh_dashboard(self):
        def _do():
            from modules.rubuska import (get_all_employees, get_low_resources,
                get_dept_avg_kpi, get_kpi_trend, get_top_employees, get_notification_count)
            emps  = get_all_employees(limit=9999)
            low   = get_low_resources()
            d_avg = get_dept_avg_kpi()
            trend = get_kpi_trend(6)
            top   = get_top_employees(8)
            n_cnt = get_notification_count()
            avg   = round(sum(d_avg.values())/len(d_avg), 1) if d_avg else 0
            self.after(0, self._set_dcards, len(emps), len(low), avg, n_cnt)
            self.after(0, self._draw_bar,  d_avg)
            self.after(0, self._draw_line, trend)
            self.after(0, self._draw_pie,  emps)
            self.after(0, self._draw_top,  top)
        threading.Thread(target=_do, daemon=True).start()

    def _set_dcards(self, emp, low, kpi, notifs):
        self._dcards["employees"].configure(text=str(emp))
        self._dcards["low"].configure(text=str(low))
        self._dcards["kpi_avg"].configure(
            text=f"{kpi:.1f}",
            fg=CHART_GREEN if kpi>=80 else (CLR_CRIT if kpi<40 else CHART_AMBER))
        self._dcards["notifs"].configure(text=str(notifs))

    def _photo(self, fig):
        try:
            from io import BytesIO; from PIL import Image, ImageTk
            buf = BytesIO()
            fig.savefig(buf, format="png", dpi=96, bbox_inches="tight", facecolor="#FAFAFA")
            buf.seek(0)
            return ImageTk.PhotoImage(Image.open(buf))
        except Exception as e:
            log.warning("photo: %s", e); return None

    def _set_chart(self, key, photo):
        if photo:
            self._clbls[key].configure(image=photo, text="")
            self._clbls[key].image = photo

    def _draw_bar(self, d_avg):
        if not d_avg: return
        try:
            import matplotlib; matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            red_z = int(self.cfg.get("nautica","kpi_red_zone",fallback="40"))
            items = sorted(d_avg.items(), key=lambda x:x[1], reverse=True)
            depts = [x[0] for x in items]; scores = [x[1] for x in items]
            clrs  = [CHART_GREEN if s>=80 else (CHART_RED if s<red_z else CHART_AMBER) for s in scores]
            fig, ax = plt.subplots(figsize=(5.2, 2.8), facecolor="#FAFAFA")
            ax.set_facecolor("#FAFAFA"); ax.set_axisbelow(True)
            ax.xaxis.grid(True, color="#EEEEEE", linewidth=0.8)
            bars = ax.barh(depts, scores, color=clrs, edgecolor="#FAFAFA", height=0.52)
            for bar, s in zip(bars, scores):
                ax.text(bar.get_width()+0.5, bar.get_y()+bar.get_height()/2,
                        f"{s:.1f}", va="center", ha="left",
                        color="#444", fontsize=9, fontweight="bold", fontfamily="Arial")
            ax.set_xlim(0, 108)
            ax.axvline(80, color="#AAAAAA", linestyle="--", linewidth=1.2)
            ax.tick_params(colors="#555", labelsize=9)
            for sp in ["top","right","left"]: ax.spines[sp].set_visible(False)
            ax.spines["bottom"].set_color("#CCCCCC")
            plt.tight_layout(pad=0.5)
            self._set_chart("bar", self._photo(fig)); plt.close(fig)
        except Exception as e: log.warning("bar: %s", e)

    def _draw_line(self, trend):
        if not trend.get("periods"): return
        try:
            import matplotlib; matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            p = trend["periods"]; s = trend["scores"]
            fig, ax = plt.subplots(figsize=(5.2, 2.8), facecolor="#FAFAFA")
            ax.set_facecolor("#FAFAFA"); ax.yaxis.grid(True, color="#EEEEEE", linewidth=0.8)
            ax.plot(p, s, color=CHART_BLUE, linewidth=2.5, marker="o", markersize=6,
                    markerfacecolor="#FFF", markeredgecolor=CHART_BLUE, markeredgewidth=2)
            ax.fill_between(p, s, alpha=0.12, color=CHART_BLUE)
            for pi, si in zip(p, s):
                ax.text(pi, si+0.5, f"{si:.1f}", ha="center",
                        fontsize=8, color="#555", fontfamily="Arial")
            ax.axhline(80, color="#AAAAAA", linestyle="--", linewidth=1)
            ax.set_ylim(max(0,min(s)-10), min(105,max(s)+10))
            ax.tick_params(colors="#555", labelsize=8, rotation=20)
            for sp in ["top","right"]: ax.spines[sp].set_visible(False)
            for sp in ["bottom","left"]: ax.spines[sp].set_color("#CCCCCC")
            plt.tight_layout(pad=0.5)
            self._set_chart("line", self._photo(fig)); plt.close(fig)
        except Exception as e: log.warning("line: %s", e)

    def _draw_pie(self, emps):
        if not emps: return
        try:
            import matplotlib; matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from collections import Counter
            d     = Counter(e["department"] for e in emps)
            lbls  = list(d.keys()); vals = list(d.values())
            colors= [CHART_BLUE, CHART_GREEN, CHART_AMBER, CHART_RED, CHART_PURPLE, CHART_TEAL]
            fig, ax = plt.subplots(figsize=(5.2, 2.8), facecolor="#FAFAFA")
            ax.set_facecolor("#FAFAFA")
            wedges, texts, autos = ax.pie(vals, labels=lbls, autopct="%1.0f%%",
                colors=colors[:len(lbls)], startangle=90,
                textprops={"color":"#555","fontsize":9,"fontfamily":"Arial"},
                pctdistance=0.8, wedgeprops={"edgecolor":"#FAFAFA","linewidth":2})
            for at in autos:
                at.set_color("#FFF"); at.set_fontsize(8); at.set_fontweight("bold")
            plt.tight_layout(pad=0.3)
            self._set_chart("pie", self._photo(fig)); plt.close(fig)
        except Exception as e: log.warning("pie: %s", e)

    def _draw_top(self, top):
        if not top: return
        try:
            import matplotlib; matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            names  = [e["full_name"].split()[0]+" "+e["full_name"].split()[1][:1]+"."
                      if len(e["full_name"].split())>1 else e["full_name"] for e in top[:8]]
            scores = [e["avg_score"] for e in top[:8]]
            red_z  = int(self.cfg.get("nautica","kpi_red_zone",fallback="40"))
            clrs   = [CHART_GREEN if s>=80 else (CHART_RED if s<red_z else CHART_AMBER) for s in scores]
            fig, ax = plt.subplots(figsize=(5.2, 2.8), facecolor="#FAFAFA")
            ax.set_facecolor("#FAFAFA"); ax.set_axisbelow(True)
            ax.xaxis.grid(True, color="#EEEEEE", linewidth=0.8)
            bars = ax.barh(names, scores, color=clrs, edgecolor="#FAFAFA", height=0.55)
            for bar, s in zip(bars, scores):
                ax.text(bar.get_width()+0.3, bar.get_y()+bar.get_height()/2,
                        f"{s:.1f}", va="center", ha="left",
                        color="#444", fontsize=8, fontfamily="Arial")
            ax.set_xlim(max(0,min(scores)-5), min(108,max(scores)+7))
            ax.tick_params(colors="#555", labelsize=8)
            for sp in ["top","right","left"]: ax.spines[sp].set_visible(False)
            ax.spines["bottom"].set_color("#CCCCCC")
            plt.tight_layout(pad=0.5)
            self._set_chart("top", self._photo(fig)); plt.close(fig)
        except Exception as e: log.warning("top: %s", e)

    # ══════════════════════════════════════════════════════════════════════════
    # EMPLOYEES
    # ══════════════════════════════════════════════════════════════════════════
    EMP_COLS = [("ID",44),("ФИО",260),("Отдел",148),("Должность",196),
                ("Найм",96),("Зарплата",112),("Ст.",44)]

    def _build_employees(self):
        p  = self._page("employees","Сотрудники","Управление персоналом")
        tb = self._toolbar(p)
        self._eq = ctk.StringVar()
        ctk.CTkEntry(tb, placeholder_text="Поиск...", textvariable=self._eq,
                     width=300, height=30, fg_color=BG_INPUT, border_color=BORDER_D,
                     text_color=TEXT, font=Fc(11)).pack(side="left", padx=10, pady=9)
        self._eq.trace_add("write", lambda *_: self.after(300, self._emp_search))
        Btn(tb,"+ Добавить",self._emp_add, w=110,h=30).pack(side="left",padx=3)
        Btn(tb,"Изменить",  self._emp_edit,w=100,h=30,style="ghost").pack(side="left",padx=3)
        Btn(tb,"Удалить",   self._emp_del, w=90, h=30,style="danger").pack(side="left",padx=3)
        self._emp_status = tk.Label(tb, text="", bg=BG_PANEL, fg=CLR_CRIT, font=FONT_MICRO)
        self._emp_status.pack(side="right", padx=10)

        from modules.rubuska import get_employees_page, count_employees

        def cfn(i, row):
            active = row[6] == "✓"
            bg     = BG_ROW_A if i%2==0 else BG_ROW_B
            fgs    = ([TEXT]*6+[CLR_OK] if active else [TEXT_SOFT]*6+[CLR_CRIT])
            return bg, fgs

        self._etbl = InfiniteTable(
            p, self.EMP_COLS,
            load_fn=lambda s, lim, off: [
                (e["id"], e["full_name"], e["department"], e["position"],
                 e["hire_date"], f"{e['salary']:,.0f} ₽",
                 "✓" if e.get("active", 1) else "✗")
                for e in get_employees_page(s, lim, off)],
            count_fn=count_employees,
            color_fn=cfn,
            on_select=lambda rid: setattr(self,"_sel_emp",rid))
        self._etbl.pack(fill="both", expand=True)
        self._sel_emp = None
        self._etbl.reload()

    def _emp_search(self):
        self._etbl.reload(self._eq.get().strip())

    def _emp_reload(self):
        self._etbl.reload(self._eq.get().strip())

    def _emp_add(self):  EmpForm(self, "add",  on_save=self._emp_reload)
    def _emp_edit(self):
        if not self._sel_emp: return
        EmpForm(self, "edit", emp_id=self._sel_emp, on_save=self._emp_reload)
    def _emp_del(self):
        if not self._sel_emp: return
        from modules.rubuska import delete_employee
        threading.Thread(target=delete_employee, args=(self._sel_emp,), daemon=True).start()
        self._sel_emp = None
        self.after(600, self._emp_reload)

    # ══════════════════════════════════════════════════════════════════════════
    # RESOURCES
    # ══════════════════════════════════════════════════════════════════════════
    RES_COLS = [("ID",40),("Наименование",240),("Категория",130),
                ("Ед.",46),("Остаток",84),("Минимум",80),("Статус",90)]

    def _build_resources(self):
        p  = self._page("resources","Ресурсы","Учёт складских запасов")
        tb = self._toolbar(p)
        self._rq = ctk.StringVar()
        ctk.CTkEntry(tb, placeholder_text="Поиск...", textvariable=self._rq,
                     width=260, height=30, fg_color=BG_INPUT, border_color=BORDER_D,
                     text_color=TEXT, font=Fc(11)).pack(side="left", padx=10, pady=9)
        self._rq.trace_add("write", lambda *_: self._res_filter())
        Btn(tb,"+ Добавить",self._res_add, w=110,h=30).pack(side="left",padx=3)
        Btn(tb,"Изменить",  self._res_edit,w=100,h=30,style="ghost").pack(side="left",padx=3)
        Btn(tb,"Удалить",   self._res_del, w=90, h=30,style="danger").pack(side="left",padx=3)
        self._rtbl = VTable(p, self.RES_COLS,
                            on_select=lambda rid: setattr(self,"_sel_res",rid))
        self._rtbl.pack(fill="both", expand=True)
        self._sel_res = None; self._res_cache = []
        self._res_reload()

    def _res_reload(self):
        def _do():
            from modules.rubuska import get_all_resources
            data = get_all_resources()
            self.after(0, lambda: setattr(self,"_res_cache",data))
            self.after(0, self._res_filter)
        threading.Thread(target=_do, daemon=True).start()

    def _res_filter(self):
        q    = self._rq.get().strip().lower()
        data = [r for r in self._res_cache if q in r["name"].lower() or q in r["category"].lower()] if q else self._res_cache

        def cfn(i, row):
            low = row[6] == "⚠ Низко"
            bg  = BG_LOW if low else (BG_ROW_A if i%2==0 else BG_ROW_B)
            fgs = [TEXT]*6 + [CLR_CRIT if low else CLR_OK]
            return bg, fgs

        rows = [(r["id"],r["name"],r["category"],r["unit"],
                 r["quantity"],r["min_quantity"],
                 "⚠ Низко" if r["quantity"]<=r["min_quantity"] else "✓ Норма") for r in data]
        self._rtbl.render(rows, cfn)

    def _res_add(self):  ResForm(self, "add",  on_save=self._res_reload)
    def _res_edit(self):
        if not self._sel_res: return
        ResForm(self, "edit", res_id=self._sel_res, on_save=self._res_reload)
    def _res_del(self):
        if not self._sel_res: return
        from modules.rubuska import delete_resource
        threading.Thread(target=delete_resource, args=(self._sel_res,), daemon=True).start()
        self._sel_res = None; self.after(500, self._res_reload)

    # ══════════════════════════════════════════════════════════════════════════
    # KPI
    # ══════════════════════════════════════════════════════════════════════════
    KPI_COLS = [("ФИО",260),("Отдел",148),("Период",76),("KPI",66),("Задач",64)]

    def _build_kpi(self):
        p = self._page("kpi","KPI","Показатели эффективности")
        cw = tk.Frame(p, bg=BG_CARD, height=240); cw.pack(fill="x"); cw.pack_propagate(False)
        self._kpi_chart = tk.Label(cw, text="Загрузка...", bg=BG_CARD,
                                   fg=TEXT_SOFT, font=FONT_MAIN)
        self._kpi_chart.pack(expand=True)
        tk.Frame(p, bg=BORDER, height=1).pack(fill="x")
        tb = self._toolbar(p)
        Btn(tb,"+ KPI",   self._kpi_add,  w=100,h=30).pack(side="left",padx=10,pady=9)
        Btn(tb,"⟳ Обновить",self._kpi_load,w=120,h=30,style="ghost").pack(side="left",padx=3)
        tk.Frame(p, bg=BORDER, height=1).pack(fill="x")
        self._ktbl = VTable(p, self.KPI_COLS)
        self._ktbl.pack(fill="both", expand=True)
        self._kpi_load()

    def _kpi_load(self):
        def _do():
            from modules.rubuska import get_kpi_summary, get_dept_avg_kpi
            data  = get_kpi_summary(); d_avg = get_dept_avg_kpi()
            self.after(0, self._kpi_render, data)
            threading.Thread(target=self._kpi_chart_draw, args=(d_avg,), daemon=True).start()
        threading.Thread(target=_do, daemon=True).start()

    def _kpi_render(self, data):
        red_z = int(self.cfg.get("nautica","kpi_red_zone",fallback="40"))

        def cfn(i, row):
            try: sc = float(row[3])
            except: sc = 0
            bg  = BG_ROW_A if i%2==0 else BG_ROW_B
            c   = CLR_OK if sc>=80 else (CLR_CRIT if sc<red_z else CLR_WARN)
            fgs = [TEXT, TEXT_MID, TEXT_SOFT, c, TEXT_MID]
            return bg, fgs

        rows = [(r["full_name"],r["department"],r["period"],
                 f"{r['avg_score']:.1f}",str(r["total_tasks"])) for r in data[:150]]
        self._ktbl.render(rows, cfn)

    def _kpi_chart_draw(self, dept_avg):
        if not dept_avg: return
        try:
            import matplotlib; matplotlib.use("Agg")
            import matplotlib.pyplot as plt, matplotlib.patches as mpatches
            red_z  = int(self.cfg.get("nautica","kpi_red_zone",fallback="40"))
            items  = sorted(dept_avg.items(), key=lambda x:x[1], reverse=True)
            depts  = [x[0] for x in items]; scores = [x[1] for x in items]
            colors = [CHART_GREEN if s>=80 else (CHART_RED if s<red_z else CHART_AMBER) for s in scores]
            fig, ax = plt.subplots(figsize=(11,2.6), facecolor="#FAFAFA")
            ax.set_facecolor("#FAFAFA"); ax.set_axisbelow(True)
            ax.xaxis.grid(True, color="#EEEEEE", linewidth=0.8)
            bars = ax.barh(depts, scores, color=colors, edgecolor="#FAFAFA", height=0.5)
            for bar, s in zip(bars, scores):
                ax.text(bar.get_width()+0.5, bar.get_y()+bar.get_height()/2,
                        f"{s:.1f}", va="center", ha="left",
                        color="#444", fontsize=10, fontweight="bold", fontfamily="Arial")
            ax.set_xlim(0, 108)
            ax.axvline(80, color="#AAAAAA", linestyle="--", linewidth=1.2)
            ax.text(80.5, len(depts)-0.05, "норма 80", color="#AAAAAA", fontsize=9, va="top")
            if red_z:
                ax.axvline(red_z, color="#FFAAAA", linestyle=":", linewidth=1)
            patches = [mpatches.Patch(color=CHART_GREEN, label="≥ 80  норма"),
                       mpatches.Patch(color=CHART_AMBER,  label="средний"),
                       mpatches.Patch(color=CHART_RED,    label=f"< {red_z}  критично")]
            ax.legend(handles=patches, loc="lower right", fontsize=9,
                      facecolor="#FAFAFA", edgecolor="#CCCCCC")
            ax.tick_params(colors="#555", labelsize=10)
            for sp in ["top","right","left"]: ax.spines[sp].set_visible(False)
            ax.spines["bottom"].set_color("#CCCCCC")
            plt.tight_layout(pad=0.5)
            photo = self._photo(fig); plt.close(fig)
            self.after(0, lambda: (
                self._kpi_chart.configure(image=photo, text=""),
                setattr(self._kpi_chart, "image", photo)))
        except Exception as e: log.warning("kpi chart: %s", e)

    def _kpi_add(self): KpiForm(self, on_save=self._kpi_load)

    # ══════════════════════════════════════════════════════════════════════════
    # ОТЧЁТЫ
    # ══════════════════════════════════════════════════════════════════════════
    def _build_reports(self):
        p = self._page("reports","Отчёты","Генерация документов Word")
        outer, scroll, canvas = make_scroll_frame(p)
        outer.pack(fill="both", expand=True)

        hero = tk.Frame(scroll, bg=BG_CARD, highlightthickness=1,
                        highlightbackground=BORDER)
        hero.pack(fill="x", padx=20, pady=(16,8))
        tk.Frame(hero, bg=BG_TOPBAR, height=2).pack(fill="x")
        inn  = tk.Frame(hero, bg=BG_CARD); inn.pack(fill="x", padx=20, pady=16)
        left = tk.Frame(inn, bg=BG_CARD);  left.pack(side="left", padx=(0,20))
        AV   = 140
        self._av = tk.Canvas(left, width=AV, height=AV, bg=BG_CARD, highlightthickness=0)
        self._av.pack(); self._load_murka(AV)
        self._av.configure(cursor="hand2")
        self._av.bind("<Button-1>", lambda e: MurkaChat(self, self.cfg))
        tk.Label(left, text="Murka GPT", bg=BG_CARD, fg=CHART_BLUE,
                 font=FONT_BOLD, cursor="hand2").pack(pady=(6,0))
        tk.Label(left, text="Нажми чтобы поговорить →", bg=BG_CARD,
                 fg=TEXT_SOFT, font=FONT_MICRO, cursor="hand2").pack()

        right = tk.Frame(inn, bg=BG_CARD); right.pack(side="left", fill="both", expand=True)
        tk.Label(right, text="Формирование отчёта", bg=BG_CARD,
                 fg=TEXT, font=FONT_HDR).pack(anchor="w")
        tk.Label(right, text="Документ Microsoft Word (.docx) — официальный формат ССК Звезда",
                 bg=BG_CARD, fg=TEXT_MID, font=FONT_SMALL).pack(anchor="w", pady=(2,10))

        def frow(lbl, widget_fn):
            r = tk.Frame(right, bg=BG_CARD); r.pack(anchor="w", pady=3)
            tk.Label(r, text=lbl, bg=BG_CARD, fg=TEXT,
                     font=FONT_SM_B, width=12, anchor="w").pack(side="left")
            widget_fn(r)
            return r

        self._rpt_p = ctk.StringVar(value=datetime.now().strftime("%Y-%m"))
        def _period_row(r):
            e = ctk.CTkEntry(r, textvariable=self._rpt_p,
                 width=120, height=30, fg_color=BG_INPUT,
                 border_color=BORDER_D, text_color=TEXT, font=Fc(12))
            e.pack(side="left", padx=8)
            _patch_entry_clipboard(e)
        frow("Период:", _period_row)

        self._rpt_dir = ctk.StringVar(
            value=self.cfg.get("nautica","report_path",fallback="").strip() or str(Path.home()))

        def _dir_row(r):
            e = ctk.CTkEntry(r, textvariable=self._rpt_dir, width=280, height=30,
                             fg_color=BG_INPUT, border_color=BORDER_D,
                             text_color=TEXT, font=Fc(10))
            e.pack(side="left", padx=8)
            _patch_entry_clipboard(e)
            Btn(r, "...", lambda: (d := filedialog.askdirectory()) and self._rpt_dir.set(d),
                w=36, h=30, style="subtle").pack(side="left")
        frow("Папка:", _dir_row)

        self._rpt_st = tk.Label(right, text="", bg=BG_CARD,
                                fg=CLR_OK, font=FONT_SMALL)
        self._rpt_st.pack(anchor="w", pady=6)
        Btn(right,"Сформировать отчёт",self._gen_report,w=220,h=38).pack(anchor="w",pady=4)
        scroll._bind_scroll(scroll)

    def _load_murka(self, AV):
        cv = self._av; cv.delete("all")
        cv.create_oval(2,2,AV-2,AV-2, outline=BORDER_D, width=1)
        for ext in ["murka.png","murka.jpg","murka.jpeg"]:
            fp = Path(__file__).parent.parent/"assets"/ext
            if fp.exists():
                try:
                    from PIL import Image, ImageTk, ImageDraw as ID
                    sz  = AV-16
                    img = Image.open(fp).convert("RGBA").resize((sz,sz), Image.LANCZOS)
                    msk = Image.new("L",(sz,sz),0); ID.Draw(msk).ellipse([0,0,sz,sz],fill=255)
                    img.putalpha(msk); photo = ImageTk.PhotoImage(img)
                    cv.create_image(AV//2,AV//2,image=photo); cv._photo=photo; return
                except: break
        cv.create_text(AV//2,AV//2,text="M",font=("Arial",40,"bold"),fill=TEXT_MID)

    def _gen_report(self):
        self._rpt_st.configure(text="Формирование...", fg=CLR_WARN); self.update()
        def _do():
            try:
                from modules.rubuska import (get_dept_avg_kpi, get_kpi_summary,
                    get_all_employees, get_all_resources, get_low_resources)
                from modules.nautica import generate_report
                out_dir = self._rpt_dir.get().strip() or str(Path.home())
                path    = generate_report(
                    period=self._rpt_p.get().strip() or datetime.now().strftime("%Y-%m"),
                    dept_avg=get_dept_avg_kpi(), kpi_summary=get_kpi_summary(),
                    employees=get_all_employees(), resources=get_all_resources(),
                    low_resources=get_low_resources(),
                    output_dir=out_dir,
                    kpi_red_zone=int(self.cfg.get("nautica","kpi_red_zone",fallback="40")))
                self.after(0, lambda: self._rpt_st.configure(
                    text=f"✓ {Path(path).name}", fg=CLR_OK))
            except Exception as e:
                self.after(0, lambda: self._rpt_st.configure(
                    text=f"Ошибка: {e}", fg=CLR_CRIT))
        threading.Thread(target=_do, daemon=True).start()

    # ══════════════════════════════════════════════════════════════════════════
    # COUNCIL
    # ══════════════════════════════════════════════════════════════════════════
    COUNCIL_COLS = [("ID",44),("Логин",160),("ФИО",250),("Роль",100),("Создан",140)]

    def _build_council(self):
        from modules.rubuska import get_admin
        self._my_role = (get_admin(self.username) or {}).get("role","admin")
        p  = self._page("council","Совет","Управление учётными записями")
        tb = self._toolbar(p)
        if self._my_role == "superadmin":
            Btn(tb,"+ Добавить",self._council_add,w=140,h=30).pack(side="left",padx=10,pady=9)
            Btn(tb,"Удалить",   self._council_del,w=90, h=30,style="danger").pack(side="left",padx=3)
        else:
            tk.Label(tb, text="Только Главный Арбитр управляет учётными записями.",
                     bg=BG_PANEL, fg=TEXT_MID, font=FONT_SMALL).pack(side="left",padx=14)
        Btn(tb,"⟳",self._council_reload,w=34,h=30,style="subtle").pack(side="right",padx=8)
        self._ctbl = VTable(p, self.COUNCIL_COLS,
                            on_select=lambda rid: setattr(self,"_sel_council",rid))
        self._ctbl.pack(fill="both", expand=True)
        self._sel_council = None; self._council_reload()

    def _council_reload(self):
        def _do():
            from modules.rubuska import get_all_admins
            data = get_all_admins()
            self.after(0, self._council_render, data)
        threading.Thread(target=_do, daemon=True).start()

    def _council_render(self, data):
        def cfn(i, row):
            bg     = BG_ROW_A if i%2==0 else BG_ROW_B
            is_sup = row[3] == "superadmin"
            fgs    = [TEXT,TEXT,TEXT, CLR_WARN if is_sup else TEXT_MID, TEXT_SOFT]
            return bg, fgs
        rows = [(a["id"],a["username"],a["full_name"],a["role"],
                 str(a.get("created_at",""))[:10]) for a in data]
        self._ctbl.render(rows, cfn)

    def _council_add(self):  AdminForm(self, on_save=self._council_reload)
    def _council_del(self):
        if not self._sel_council: return
        from modules.rubuska import delete_admin
        threading.Thread(target=delete_admin,args=(self._sel_council,),daemon=True).start()
        self._sel_council = None; self.after(400, self._council_reload)

    # ══════════════════════════════════════════════════════════════════════════
    # УВЕДОМЛЕНИЯ
    # ══════════════════════════════════════════════════════════════════════════
    def _build_notifs_page(self):
        p  = self._page("notifications","Уведомления","Системные события")
        tb = self._toolbar(p)
        Btn(tb,"✓ Всё прочитано",self._notif_mark_read,w=180,h=30,style="ghost").pack(side="left",padx=10,pady=9)
        Btn(tb,"⟳",self._notif_reload,w=34,h=30,style="subtle").pack(side="right",padx=8)
        outer, scroll, canvas = make_scroll_frame(p)
        outer.pack(fill="both", expand=True)
        self._notif_scroll = scroll; self._notif_canvas = canvas
        scroll._bind_scroll(scroll)
        self._notif_reload()

    def _notif_reload(self):
        def _do():
            from modules.rubuska import get_unread_notifications
            notifs = get_unread_notifications()
            self.after(0, self._notif_render, notifs)
        threading.Thread(target=_do, daemon=True).start()

    def _notif_render(self, notifs):
        scroll = self._notif_scroll
        for w in scroll.winfo_children(): w.destroy()
        icons  = {"staff":"👤","kpi":"📊","low":"⚠️","":"🔔"}
        icon_colors = {"staff":CHART_BLUE,"kpi":CHART_AMBER,"low":CHART_RED,"":"TEXT_SOFT"}
        if not notifs:
            tk.Label(scroll, text="Нет непрочитанных уведомлений.",
                     bg=BG, fg=TEXT_SOFT, font=FONT_MAIN).pack(pady=30)
            return
        for n in notifs:
            kind = n.get("kind","")
            row  = tk.Frame(scroll, bg=BG_CARD, highlightthickness=1,
                            highlightbackground=BORDER)
            row.pack(fill="x", padx=20, pady=3)
            ik  = icons.get(kind,"🔔")
            acc = icon_colors.get(kind, CHART_BLUE)
            tk.Frame(row, bg=acc, width=3).pack(fill="y", side="left")
            tk.Label(row, text=ik, bg=BG_CARD, font=("Segoe UI",14)).pack(side="left", padx=12, pady=8)
            rf = tk.Frame(row, bg=BG_CARD); rf.pack(side="left", fill="x", expand=True)
            tk.Label(rf, text=n["message"], bg=BG_CARD, fg=TEXT,
                     font=FONT_MAIN, anchor="w", justify="left",
                     wraplength=700).pack(anchor="w", padx=4, pady=(6,2))
            tk.Label(rf, text=str(n.get("created_at",""))[:16], bg=BG_CARD,
                     fg=TEXT_SOFT, font=FONT_MICRO).pack(anchor="w", padx=4, pady=(0,6))
            bind_scroll_tree(row, self._notif_canvas)

    def _notif_mark_read(self):
        from modules.rubuska import mark_notifications_read
        threading.Thread(target=mark_notifications_read, daemon=True).start()
        self._bell_cnt.configure(text="")
        self.after(300, self._notif_reload)

    # ══════════════════════════════════════════════════════════════════════════
    # СПРАВКА — Руководство пользователя
    # ══════════════════════════════════════════════════════════════════════════
    def _build_docs(self):
        p = self._page("docs","Справка","Руководство пользователя")
        outer, scroll, canvas = make_scroll_frame(p)
        outer.pack(fill="both", expand=True)

        def sec(title, body, color=None):
            f = tk.Frame(scroll, bg=BG_CARD, highlightthickness=1,
                         highlightbackground=BORDER)
            f.pack(fill="x", padx=20, pady=5)
            tk.Frame(f, bg=color or BG_TOPBAR, height=3).pack(fill="x")
            tk.Label(f, text=title, bg=BG_CARD, fg=TEXT,
                     font=FONT_BOLD, anchor="w").pack(fill="x", padx=14, pady=(8,4))
            tk.Frame(f, bg=BORDER, height=1).pack(fill="x", padx=14)
            tk.Label(f, text=body, bg=BG_CARD, fg=TEXT_MID, font=FONT_MAIN,
                     anchor="nw", justify="left",
                     wraplength=900).pack(fill="x", padx=14, pady=(6,12))
            bind_scroll_tree(f, canvas)

        sec("Добро пожаловать в ССК Звезда KPI",
            "Система учёта KPI предназначена для мониторинга эффективности работы сотрудников "
            "ССК «Звезда», управления складскими запасами и формирования аналитических отчётов.\n\n"
            "Логин по умолчанию: admin  /  Пароль: admin\n"
            "После первого входа обязательно смените пароль в разделе Настройки!", CHART_BLUE)

        sec("Дашборд",
            "Главная страница с аналитикой предприятия.\n\n"
            "Карточки вверху показывают:\n"
            "  • Общее количество сотрудников в системе\n"
            "  • Количество позиций склада ниже минимума (требуют пополнения)\n"
            "  • Средний KPI по всем отделам\n"
            "  • Количество непрочитанных уведомлений\n\n"
            "Графики:\n"
            "  • KPI по отделам — горизонтальный бар-чарт с цветовой кодировкой\n"
            "  • Динамика — тренд среднего KPI за последние 6 месяцев\n"
            "  • Структура персонала — круговая диаграмма по отделам\n"
            "  • Топ-8 сотрудников — рейтинг лучших за текущий период\n\n"
            "Нажмите «⟳ Обновить дашборд» для ручного обновления.", CHART_BLUE)

        sec("Сотрудники — добавление и редактирование",
            "Вкладка «Сотрудники» содержит полный список персонала предприятия.\n\n"
            "Как работать:\n"
            "  1. Введите текст в поле «Поиск» — таблица отфильтруется по ФИО, отделу и должности\n"
            "  2. Кликните по строке — строка выделится серым цветом (это выбранный сотрудник)\n"
            "  3. Нажмите «Изменить» для редактирования или «Удалить» для удаления\n"
            "  4. Нажмите «+ Добавить» для создания нового сотрудника\n\n"
            "При прокрутке вниз таблица автоматически подгружает следующие записи "
            "(по 50 строк за раз). Строка статуса внизу показывает «Показано: X из Y».\n\n"
            "Статус сотрудника: ✓ — активен, ✗ — архивирован.", CHART_GREEN)

        sec("Ресурсы — складской учёт",
            "Вкладка «Ресурсы» управляет складскими запасами предприятия.\n\n"
            "Цветовая маркировка строк:\n"
            "  • Красный фон — количество ≤ минимального порога (нужно пополнить)\n"
            "  • Белый/серый — запас в норме\n\n"
            "Действия:\n"
            "  • «+ Добавить» — новая позиция склада\n"
            "  • «Изменить» — изменить количество или параметры (выберите строку сначала)\n"
            "  • «Удалить» — удалить позицию\n\n"
            "Telegram-уведомления о низких запасах отправляются автоматически раз в час "
            "если настроен бот (см. раздел Настройки → Telegram).", CHART_AMBER)

        sec("KPI — показатели эффективности",
            "Вкладка «KPI» отображает журнал показателей эффективности сотрудников.\n\n"
            "Цветовая кодировка KPI:\n"
            "  • Зелёный — KPI ≥ 80 (норма)\n"
            "  • Янтарный — средний показатель\n"
            "  • Красный — ниже красной зоны (порог настраивается в Настройках → Отчёты)\n\n"
            "Добавление записи:\n"
            "  1. Нажмите «+ KPI»\n"
            "  2. Выберите сотрудника из списка\n"
            "  3. Укажите период (ГГГГ-ММ), балл KPI (0–100) и количество выполненных задач\n\n"
            "При добавлении записи ниже красной зоны автоматически отправляется "
            "уведомление в Telegram.", CLR_CRIT)

        sec("Отчёты — формирование документов",
            "Вкладка «Отчёты» генерирует официальный аналитический отчёт в формате Word (.docx).\n\n"
            "Содержание отчёта:\n"
            "  1. Исполнительное резюме с ключевыми показателями\n"
            "  2. График KPI по подразделениям с детальной таблицей\n"
            "  3. Рейтинг топ-20 сотрудников\n"
            "  4. Список сотрудников в зоне риска (если есть)\n"
            "  5. Полная таблица складских запасов\n"
            "  6. Кадровый состав со средним стажем\n"
            "  7. Строки для подписей\n\n"
            "Настройка пути сохранения: укажите папку в поле «Папка» или нажмите «...» "
            "для выбора. Путь также сохраняется в Настройках → Отчёты.", CHART_PURPLE)

        sec("Совет — управление администраторами",
            "Вкладка «Совет» доступна только Главному Арбитру (роль superadmin).\n\n"
            "Возможности:\n"
            "  • Добавить нового арбитра (администратора) системы\n"
            "  • Удалить существующего арбитра\n"
            "  • Просмотреть список всех учётных записей с датами создания\n\n"
            "При использовании Supabase новый арбитр сразу может войти с любого "
            "компьютера — данные хранятся в облаке, не локально.\n\n"
            "Аккаунт superadmin защищён от удаления.", CHART_TEAL)

        sec("Уведомления — что и когда приходит",
            "Система автоматически создаёт уведомления при следующих событиях:\n\n"
            "  👤 Сотрудники:\n"
            "       • Добавление нового сотрудника\n\n"
            "  📊 KPI:\n"
            "       • Запись KPI ниже красной зоны (критический показатель)\n\n"
            "  ⚠️ Ресурсы:\n"
            "       • Позиция склада опустилась ниже минимума\n\n"
            "Значок 🔔 в верхней панели показывает количество непрочитанных уведомлений. "
            "Кликните по нему для перехода к вкладке Уведомления.\n\n"
            "Telegram-бот дублирует критические события в мессенджер (настройка в Настройках).", CHART_AMBER)

        sec("Синхронизация — как работает Supabase",
            "При настроенном Supabase все данные хранятся в облачной PostgreSQL базе.\n\n"
            "Принцип работы:\n"
            "  • Каждое действие (добавить/изменить/удалить) напрямую записывается в Supabase\n"
            "  • Приложение проверяет изменения каждые 15 секунд\n"
            "  • Если другой пользователь добавил сотрудника — таблица обновится автоматически\n"
            "  • Новые администраторы сразу видны на всех компьютерах\n\n"
            "Конфликты исключены: каждая операция атомарна (INSERT/UPDATE/DELETE напрямую в БД).\n\n"
            "Без Supabase приложение работает с локальной SQLite — только на одном компьютере.", CHART_BLUE)

        sec("Настройки — описание полей",
            "Supabase:\n"
            "  • Project URL — адрес вашего проекта на supabase.com (https://xxx.supabase.co)\n"
            "  • Anon Public Key — публичный ключ (вкладка Settings → API на сайте Supabase)\n\n"
            "Telegram:\n"
            "  • Bot Token — токен от @BotFather\n"
            "  • Admin Chat ID — ваш ID из @userinfobot\n\n"
            "Отчёты:\n"
            "  • Красная зона KPI — порог (%), ниже которого KPI считается критическим\n"
            "  • Папка — куда сохраняются отчёты Word\n\n"
            "Поведение:\n"
            "  • «Сворачивать в трей» — при нажатии X окно прячется в трей вместо закрытия\n\n"
            "После изменения настроек нажмите «Сохранить настройки» и ПЕРЕЗАПУСТИТЕ приложение.", CHART_GRAY)

        scroll._bind_scroll(scroll)

    # ══════════════════════════════════════════════════════════════════════════
    # НАСТРОЙКИ — исправленные ComboBox и поля из config
    # ══════════════════════════════════════════════════════════════════════════
    def _build_settings(self):
        p = self._page("settings","Настройки","Конфигурация системы")
        outer, scroll, canvas = make_scroll_frame(p)
        outer.pack(fill="both", expand=True)
        self._sv = {}   # StringVar registry

        def fld(sec, key, lbl, show="", w=320):
            # Используем НАТИВНЫЙ tk.Entry — CTkEntry ломает Ctrl+C/V на Windows
            v = tk.StringVar(value=self.cfg.get(sec, key, fallback=""))
            self._sv[f"{sec}.{key}"] = v
            row = tk.Frame(scroll, bg=BG); row.pack(fill="x", padx=20, pady=4)
            tk.Label(row, text=lbl, bg=BG, fg=TEXT, font=FONT_SM_B,
                     width=36, anchor="w").pack(side="left")
            e = tk.Entry(row, textvariable=v, show=show, width=w//7,
                         font=("Arial",12), relief="solid", bd=1,
                         bg=BG_INPUT, fg=TEXT,
                         insertbackground=TEXT,
                         selectbackground="#3080CC", selectforeground="#FFFFFF")
            e.pack(side="left", ipady=6)
            # Правый клик — контекстное меню копирования
            def _ctx(ev, _e=e):
                m = tk.Menu(_e, tearoff=0)
                m.add_command(label="Вырезать",      command=lambda: _e.event_generate("<<Cut>>"))
                m.add_command(label="Копировать",    command=lambda: _e.event_generate("<<Copy>>"))
                m.add_command(label="Вставить",      command=lambda: _e.event_generate("<<Paste>>"))
                m.add_separator()
                m.add_command(label="Выделить всё",  command=lambda: (_e.select_range(0,"end"), _e.focus()))
                try: m.tk_popup(ev.x_root, ev.y_root)
                finally: m.grab_release()
            e.bind("<Button-3>", _ctx)
            return v

        def combo(sec, key, lbl, values, w=280):
            v = ctk.StringVar(value=self.cfg.get(sec, key, fallback=values[0]))
            self._sv[f"{sec}.{key}"] = v
            row = tk.Frame(scroll, bg=BG); row.pack(fill="x", padx=20, pady=4)
            tk.Label(row, text=lbl, bg=BG, fg=TEXT, font=FONT_SM_B,
                     width=36, anchor="w").pack(side="left")
            Combo(row, v, values, w=w).pack(side="left")
            return v

        def tog(sec, key, lbl):
            v = ctk.BooleanVar(value=self.cfg.getboolean(sec, key, fallback=False))
            self._sv[f"{sec}.{key}"] = v
            ctk.CTkCheckBox(scroll, text=lbl, variable=v,
                            font=Fc(12), fg_color=BORDER_D,
                            hover_color=TEXT_MID, checkmark_color=BG,
                            border_color=BORDER, text_color=TEXT).pack(anchor="w", padx=20, pady=5)
            return v

        # Supabase/Telegram убраны из UI-настроек: подключение и токены вшиты в код (локальное использование).

        SectionLbl(scroll,"GITHUB  —  Резервная копия (для локального режима)")
        fld("github", "token",    "Personal Access Token:", show="•")
        fld("github", "repo_url", "Repository URL:")

        SectionLbl(scroll,"ПРОИЗВОДИТЕЛЬНОСТЬ")
        combo("umamusume", "page_size", "Строк за раз:", ["25","50","100","200"])
        tog("sync", "cache_enabled", "Кэшировать данные локально")

        pur = tk.Frame(scroll, bg=BG); pur.pack(fill="x", padx=20, pady=4)
        tk.Label(pur, text="Очистка KPI-логов (>12 мес.):", bg=BG, fg=TEXT,
                 font=FONT_SM_B, width=36, anchor="w").pack(side="left")
        Btn(pur, "Очистить старые логи", self._purge_logs, w=180, h=30,
            style="danger").pack(side="left", padx=8)

        SectionLbl(scroll,"ОТЧЁТЫ  —  Nautica")
        tk.Label(scroll,
            text="  ℹ  Папка сохранения отчётов настраивается прямо на вкладке «Отчёты»",
            bg=BG, fg=TEXT_SOFT, font=FONT_SMALL).pack(anchor="w", padx=20, pady=(0,4))
        combo("nautica","report_template","Шаблон отчёта:",["official","brief"])
        combo("nautica","kpi_red_zone","Красная зона KPI (ниже %):",
              ["20","30","40","50","60"])

        SectionLbl(scroll,"ПОВЕДЕНИЕ ПРИЛОЖЕНИЯ")
        tog("app","minimize_to_tray","При закрытии — свернуть в трей (иначе выход)")
        tog("app","hardware_bind",  "Привязать сессию к оборудованию (MAC-адрес)")

        SectionLbl(scroll,"БЕЗОПАСНОСТЬ  —  Смена пароля")
        pw_r = tk.Frame(scroll, bg=BG); pw_r.pack(fill="x", padx=20, pady=4)
        tk.Label(pw_r, text="Новый пароль:", bg=BG, fg=TEXT, font=FONT_SM_B,
                 width=36, anchor="w").pack(side="left")
        self._npw = ctk.StringVar()
        Entry(pw_r, self._npw, show="•", w=200).pack(side="left")
        Btn(pw_r,"Сменить",self._chpw,w=100,h=34,style="danger").pack(side="left",padx=8)

        tk.Frame(scroll, bg=BORDER, height=1).pack(fill="x", padx=20, pady=16)
        Btn(scroll,"Сохранить настройки",lambda: self._save_cfg(),
            w=240,h=42).pack(pady=8)
        self._cfg_st = tk.Label(scroll, text="", bg=BG, fg=CLR_OK, font=FONT_MAIN)
        self._cfg_st.pack(pady=4)
        scroll._bind_scroll(scroll)

    def _save_cfg(self):
        from modules.rubuska import save_config, set_cfg_ref
        for k, v in self._sv.items():
            sec, opt = k.split(".", 1)
            if not self.cfg.has_section(sec):
                self.cfg.add_section(sec)
            self.cfg.set(sec, opt, str(v.get()))
        save_config(self.cfg)
        set_cfg_ref(self.cfg)
        if self._worker: self._worker.reload_cfg(self.cfg)

        # Обновить поле папки в отчётах
        if hasattr(self, "_rpt_dir"):
            self._rpt_dir.set(self.cfg.get("nautica","report_path",fallback="").strip() or str(Path.home()))

        # Применить page_size к уже созданным таблицам без перезапуска
        try:
            new_ps = int(self.cfg.get("umamusume","page_size",fallback="50"))
            for attr in ("_etbl",):
                tbl = getattr(self, attr, None)
                if tbl: tbl.PAGE_SIZE = new_ps
        except Exception:
            pass

        self._cfg_st.configure(
            text="✓ Настройки сохранены и применены.", fg=CLR_OK)
        self.after(5000, lambda: self._cfg_st.configure(text=""))

    def _chpw(self):
        from modules.rubuska import change_password
        pw = self._npw.get().strip()
        if len(pw) < 4:
            self._cfg_st.configure(text="Пароль — не менее 4 символов.", fg=CLR_CRIT); return
        threading.Thread(target=change_password, args=(self.username, pw), daemon=True).start()
        self._npw.set(""); self._cfg_st.configure(text="✓ Пароль изменён.", fg=CLR_OK)

    def _purge_logs(self):
        from modules.rubuska import purge_old_logs
        threading.Thread(target=purge_old_logs, args=(12,), daemon=True).start()
        self._cfg_st.configure(text="✓ Старые логи удалены.", fg=CLR_OK)

    # _import_to_supabase удалён из UI (локально вшитое подключение)

    # ── Realtime ───────────────────────────────────────────────────────────────
    def _on_realtime(self, changed: list):
        """Вызывается BackgroundWorker при обнаружении изменений в Supabase."""
        try:
            if not self.winfo_exists(): return
        except Exception:
            return
        if "emp" in changed and "employees" in self._pages:
            self.after(0, self._emp_reload)
        if "res" in changed and "resources" in self._pages:
            self.after(0, self._res_reload)
        if "kpi" in changed and "kpi" in self._pages:
            self.after(0, self._kpi_load)
        if "ntf" in changed:
            self.after(0, self._refresh_badge)
            if "notifications" in self._pages:
                self.after(0, self._notif_reload)

    # ── Notifications badge ────────────────────────────────────────────────────
    def _refresh_badge(self):
        def _do():
            try:
                from modules.rubuska import get_notification_count
                n = get_notification_count()
                def _upd():
                    try:
                        if self.winfo_exists():
                            self._bell_cnt.configure(text=f" {n}" if n else "")
                    except Exception:
                        pass
                self.after(0, _upd)
            except Exception:
                pass
        threading.Thread(target=_do, daemon=True).start()
        try:
            if self.winfo_exists():
                self.after(30000, self._refresh_badge)
        except Exception:
            pass

    # ── Engine ─────────────────────────────────────────────────────────────────
    def _start_engine(self):
        from modules.rubuska import set_cfg_ref
        from modules.umamusume import BackgroundWorker, create_tray_icon, run_tray_in_thread
        set_cfg_ref(self.cfg)
        self._worker = BackgroundWorker(self.cfg)
        self._worker.start(
            on_low_resources=lambda low: self.after(0, self._on_low, low),
            on_sync=self._on_realtime)
        ico        = str(Path(__file__).parent.parent / "assets" / "izolde.ico")
        self._tray = create_tray_icon(self, ico)
        run_tray_in_thread(self._tray)

    def _on_low(self, low):
        cnt = len(low)
        self._usr_lbl.configure(text=f"  ⚠ {cnt} ресурсов на минимуме  ", fg="#FF6B6B")
        self.after(10000, lambda: threading.Thread(
            target=self._load_uname, daemon=True).start())

    def show_window(self):
        self.after(0, lambda: (self.deiconify(), self.lift(), self.focus_force()))

    def _on_close(self):
        if self.cfg.getboolean("app","minimize_to_tray",fallback=False):
            self.withdraw()
        else:
            self._quit()

    def _quit(self):
        if self._worker: self._worker.stop()
        if self._tray:
            try: self._tray.stop()
            except: pass
        self.destroy()

    def quit_app(self): self._quit()


# ══════════════════════════════════════════════════════════════════════════════
# FORMS
# ══════════════════════════════════════════════════════════════════════════════
class _Form(ctk.CTkToplevel):
    def __init__(self, parent, title, w=480, h=420):
        super().__init__(parent)
        self.title(title); self.geometry(f"{w}x{h}")
        self.resizable(False, False)
        self.configure(fg_color=BG); self.grab_set()
        top = tk.Frame(self, bg=BG_TOPBAR, height=44); top.pack(fill="x")
        tk.Label(top, text=title, bg=BG_TOPBAR, fg=TEXT_INV,
                 font=FONT_BOLD).pack(expand=True)

    def _body(self):
        f = tk.Frame(self, bg=BG); f.pack(fill="both", expand=True, padx=24, pady=12)
        return f

    def _fld(self, parent, lbl, var, ph="", show="", combo=None):
        tk.Label(parent, text=lbl, bg=BG, fg=TEXT, font=FONT_SM_B,
                 anchor="w").pack(fill="x", pady=(8,2))
        if combo:
            Combo(parent, var, combo, w=400).pack(fill="x")
        else:
            e = ctk.CTkEntry(parent, textvariable=var, placeholder_text=ph,
                             show=show, height=34, fg_color=BG_INPUT,
                             border_color=BORDER_D, text_color=TEXT, font=Fc(12))
            e.pack(fill="x")
            _patch_entry_clipboard(e)

    def _save_btn(self, parent, cmd):
        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", pady=10)
        Btn(parent,"Сохранить",cmd,w=180,h=38).pack()


class EmpForm(_Form):
    def __init__(self, parent, mode, emp_id=None, on_save=None, **kw):
        super().__init__(parent,
            "Новый сотрудник" if mode=="add" else "Редактирование сотрудника",
            480, 480 if mode=="edit" else 460)
        self.mode=mode; self.emp_id=emp_id; self.on_save=on_save
        b=self._body()
        self.v = {k: ctk.StringVar() for k in ["name","dept","pos","date","sal"]}
        self.v["date"].set(datetime.now().strftime("%Y-%m-%d"))
        self.v["sal"].set("45000")
        self._fld(b,"ФИО:",self.v["name"],"Иванов Иван Иванович")
        self._fld(b,"Подразделение:",self.v["dept"],
                  combo=["АХД","Транспортный цех","Мастерская"])
        self._fld(b,"Должность:",self.v["pos"],"Водитель")
        self._fld(b,"Дата найма (ГГГГ-ММ-ДД):",self.v["date"])
        self._fld(b,"Зарплата (₽):",self.v["sal"])
        if mode=="edit":
            self.v_act=ctk.BooleanVar(value=True)
            ctk.CTkCheckBox(b,text="Активен",variable=self.v_act,
                            fg_color=BORDER_D,checkmark_color=BG,
                            text_color=TEXT,font=Fc(12)).pack(anchor="w",pady=6)
        self.st=tk.Label(b,text="",bg=BG,fg=CLR_CRIT,font=FONT_SMALL); self.st.pack()
        self._save_btn(b,self._save)
        if mode=="edit" and emp_id: self._load()

    def _load(self):
        from modules.rubuska import get_employees_page
        e=next((x for x in get_employees_page(limit=9999) if x["id"]==self.emp_id),None)
        if e:
            self.v["name"].set(e["full_name"]); self.v["dept"].set(e["department"])
            self.v["pos"].set(e["position"]); self.v["date"].set(e["hire_date"])
            self.v["sal"].set(str(e["salary"]))
            if hasattr(self,"v_act"): self.v_act.set(bool(e.get("active",1)))

    def _save(self):
        from modules.rubuska import add_employee, update_employee
        fn=self.v["name"].get().strip(); dp=self.v["dept"].get().strip()
        po=self.v["pos"].get().strip(); hd=self.v["date"].get().strip()
        try: sl=float(self.v["sal"].get() or 0)
        except: self.st.configure(text="Зарплата — число."); return
        if not fn or not dp: self.st.configure(text="ФИО и отдел обязательны."); return
        self.st.configure(text="Сохранение...", fg=TEXT_MID)
        def _do():
            try:
                if self.mode=="add":
                    add_employee(fn,dp,po,hd,sl)
                else:
                    act=int(getattr(self,"v_act",ctk.BooleanVar(value=True)).get())
                    update_employee(self.emp_id,fn,dp,po,hd,sl,act)
                if self.on_save: self.after(400,self.on_save)
                self.after(0,self.destroy)
            except Exception as e:
                self.after(0,lambda: self.st.configure(text=f"Ошибка: {e}",fg=CLR_CRIT))
        threading.Thread(target=_do,daemon=True).start()


class ResForm(_Form):
    def __init__(self, parent, mode, res_id=None, on_save=None):
        super().__init__(parent,"Новый ресурс" if mode=="add" else "Редактирование ресурса",480,400)
        self.mode=mode; self.res_id=res_id; self.on_save=on_save
        b=self._body()
        self.v={k:ctk.StringVar() for k in ["name","cat","unit","qty","min"]}
        self._fld(b,"Наименование:",self.v["name"],"Дизельное топливо")
        self._fld(b,"Категория:",self.v["cat"],combo=["Топливо","Масла","Запчасти","Канцтовары","Спецодежда","Расходники"])
        self._fld(b,"Единица:",self.v["unit"],"л / шт / уп")
        self._fld(b,"Количество:",self.v["qty"],"0")
        self._fld(b,"Минимальный порог:",self.v["min"],"10")
        self.st=tk.Label(b,text="",bg=BG,fg=CLR_CRIT,font=FONT_SMALL); self.st.pack()
        self._save_btn(b,self._save)
        if mode=="edit" and res_id: self._load()

    def _load(self):
        from modules.rubuska import get_all_resources
        r=next((x for x in get_all_resources() if x["id"]==self.res_id),None)
        if r:
            self.v["name"].set(r["name"]); self.v["cat"].set(r["category"])
            self.v["unit"].set(r["unit"]); self.v["qty"].set(str(r["quantity"]))
            self.v["min"].set(str(r["min_quantity"]))

    def _save(self):
        from modules.rubuska import add_resource, update_resource
        n=self.v["name"].get().strip(); c=self.v["cat"].get().strip()
        u=self.v["unit"].get().strip()
        try: q=float(self.v["qty"].get() or 0); m=float(self.v["min"].get() or 0)
        except: self.st.configure(text="Количество — число."); return
        def _do():
            try:
                if self.mode=="add": add_resource(n,c,u,q,m)
                else: update_resource(self.res_id,n,c,u,q,m)
                if self.on_save: self.after(400,self.on_save)
                self.after(0,self.destroy)
            except Exception as e:
                self.after(0,lambda: self.st.configure(text=f"Ошибка: {e}",fg=CLR_CRIT))
        threading.Thread(target=_do,daemon=True).start()


class KpiForm(_Form):
    def __init__(self, parent, on_save=None):
        super().__init__(parent,"Добавить KPI",480,340)
        self.on_save=on_save
        from modules.rubuska import get_employees_page
        emps=get_employees_page(limit=9999)
        self.emp_map={f"{e['full_name']} (ID:{e['id']})":e for e in emps}
        names=list(self.emp_map.keys())
        b=self._body()
        self.v_emp=ctk.StringVar(value=names[0] if names else "")
        self.v_per=ctk.StringVar(value=datetime.now().strftime("%Y-%m"))
        self.v_sc=ctk.StringVar(value="80"); self.v_t=ctk.StringVar(value="10")
        self._fld(b,"Сотрудник:",self.v_emp,combo=names)
        self._fld(b,"Период (ГГГГ-ММ):",self.v_per)
        self._fld(b,"KPI (0–100):",self.v_sc)
        self._fld(b,"Задач выполнено:",self.v_t)
        self.st=tk.Label(b,text="",bg=BG,fg=CLR_CRIT,font=FONT_SMALL); self.st.pack()
        self._save_btn(b,self._save)

    def _save(self):
        from modules.rubuska import add_kpi_log
        emp_data=self.emp_map.get(self.v_emp.get())
        if not emp_data: self.st.configure(text="Выберите сотрудника."); return
        try: sc=float(self.v_sc.get()); t=int(self.v_t.get())
        except: self.st.configure(text="Проверьте формат."); return
        def _do():
            try:
                add_kpi_log(emp_data["id"],self.v_per.get().strip(),sc,t,
                            emp_name=emp_data.get("full_name",""))
                if self.on_save: self.after(400,self.on_save)
                self.after(0,self.destroy)
            except Exception as e:
                self.after(0,lambda: self.st.configure(text=f"Ошибка: {e}",fg=CLR_CRIT))
        threading.Thread(target=_do,daemon=True).start()


class AdminForm(_Form):
    def __init__(self, parent, on_save=None):
        super().__init__(parent,"Добавить арбитра",480,360)
        self.on_save=on_save
        b=self._body()
        self.v_u=ctk.StringVar(); self.v_fn=ctk.StringVar()
        self.v_p=ctk.StringVar(); self.v_r=ctk.StringVar(value="admin")
        self._fld(b,"Логин:",self.v_u,"arbiter_01")
        self._fld(b,"ФИО:",self.v_fn,"Иванов Иван Иванович")
        self._fld(b,"Пароль:",self.v_p,show="•")
        self._fld(b,"Роль:",self.v_r,combo=["admin","superadmin"])
        self.st=tk.Label(b,text="",bg=BG,fg=CLR_CRIT,font=FONT_SMALL); self.st.pack()
        self._save_btn(b,self._save)

    def _save(self):
        from modules.rubuska import add_admin
        u=self.v_u.get().strip(); fn=self.v_fn.get().strip()
        p=self.v_p.get().strip(); r=self.v_r.get().strip()
        if not u or len(p)<4:
            self.st.configure(text="Логин обязателен, пароль ≥ 4 символов."); return
        def _do():
            try:
                add_admin(u,p,fn,r)
                if self.on_save: self.after(400,self.on_save)
                self.after(0,self.destroy)
            except Exception as e:
                self.after(0,lambda: self.st.configure(text=f"Ошибка: {e}",fg=CLR_CRIT))
        threading.Thread(target=_do,daemon=True).start()


# ══════════════════════════════════════════════════════════════════════════════
# MURKA GPT — Чат с ИИ-ассистентом
# ══════════════════════════════════════════════════════════════════════════════
from modules.izolde_murka_patch import MurkaChat