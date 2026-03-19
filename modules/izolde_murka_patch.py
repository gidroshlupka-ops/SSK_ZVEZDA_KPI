
import base64, io, threading
from datetime import datetime
from pathlib import Path
from tkinter import filedialog
import tkinter as tk

try:
    import customtkinter as ctk
    from PIL import Image as PILImage, ImageTk
    _PIL = True
except ImportError:
    _PIL = False

# Импорт палитры и утилит из izolde.py (они уже определены в пространстве имён)
# Если этот файл вставлен напрямую в izolde.py — всё доступно автоматически.
# Если импортируется как отдельный модуль — нужен явный импорт:
try:
    from modules.izolde import (
        BG, BG_TOPBAR, BG_PANEL, BG_INPUT, BG_CARD,
        BORDER, BORDER_D, TEXT, TEXT_INV, TEXT_MID, TEXT_SOFT,
        CHART_GREEN, CHART_AMBER, CHART_BLUE, CHART_RED,
        FONT_MAIN, FONT_BOLD, FONT_SMALL, FONT_SM_B, FONT_MICRO,
        Fc, Btn, _patch_entry_clipboard,
    )
except ImportError:
    pass   # вставляем напрямую в izolde.py — всё уже есть

from modules.murka_ai import engine, memory, read_file_content, image_to_base64, bytes_to_base64

import logging
log = logging.getLogger("murka_chat")

# ══════════════════════════════════════════════════════════════════════════════
# MURKA CHAT — переработанный Desktop-чат
# ══════════════════════════════════════════════════════════════════════════════
class MurkaChat(ctk.CTkToplevel):
    """
    Мультимодальный чат с Murka:
    • Текст, изображения, файлы (.txt/.py/.log/.zip), аудио
    • Кнопка «+» для прикрепления файлов/изображений
    • Рисование: prompt «Нарисуй ...» → Pollinations.ai → показ в чате
    • Вся память — в SQLite через MurkaMemory (общая с Telegram)
    """

    def __init__(self, parent, cfg, username: str = "desktop"):
        super().__init__(parent)
        self.cfg      = cfg
        self.username = username          # идентификатор пользователя для памяти
        self._typing  = False
        self._pending_file: dict | None = None   # прикреплённый файл/фото

        self.title("Murka GPT")
        self.geometry("660x720")
        self.minsize(500, 520)
        self.configure(fg_color=BG)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.transient(parent)
        self.lift(); self.focus_force()

        try:
            _ico = Path(__file__).parent.parent / "assets" / "izolde.ico"
            if _ico.exists():
                self.iconbitmap(str(_ico))
        except Exception:
            pass

        self._build()
        self.after(200, lambda: self._add_msg(
            "assistant",
            "Привет 😎 Я Мурка. Спрашивай что хочешь.\n"
            "Кидай фото или файлы «+» — всё прочитаю.\n"
            "Напиши «Нарисуй ...» — нарисую что-нибудь."
        ))
        self._input.focus_set()

    # ══════════════════════════════════════════════════════════════════════════
    # BUILD UI
    # ══════════════════════════════════════════════════════════════════════════
    def _build(self):
        # ── Шапка ────────────────────────────────────────────────────────────
        top = tk.Frame(self, bg=BG_TOPBAR, height=58)
        top.pack(fill="x"); top.pack_propagate(False)

        # Аватар
        AV = 40
        av_cv = tk.Canvas(top, width=AV, height=AV, bg=BG_TOPBAR, highlightthickness=0)
        av_cv.place(x=12, y=9)
        av_cv.create_oval(1, 1, AV-1, AV-1, fill="#444", outline="#888")
        # Попытка загрузить фото murka.png
        assets = Path(__file__).parent.parent / "assets"
        for ext in ["murka.png", "murka.jpg", "murka.jpeg"]:
            fp = assets / ext
            if fp.exists() and _PIL:
                try:
                    img = PILImage.open(fp).convert("RGBA").resize((AV-4, AV-4), PILImage.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    av_cv.create_image(AV//2, AV//2, image=photo)
                    av_cv._photo = photo
                    break
                except Exception:
                    pass

        tk.Label(top, text="Murka GPT", bg=BG_TOPBAR, fg=TEXT_INV,
                 font=("Arial", 13, "bold")).place(x=62, y=10)
        self._status_lbl = tk.Label(top, text="онлайн ●", bg=BG_TOPBAR,
                                     fg=CHART_GREEN, font=("Arial", 9))
        self._status_lbl.place(x=62, y=32)

        # Кнопка «Очистить историю»
        tk.Button(top, text="🗑 Сброс", command=self._clear_history,
                  bg="#333", fg=TEXT_INV, font=("Arial", 9),
                  relief="flat", padx=8, cursor="hand2").place(relx=1.0, x=-12, y=14, anchor="ne")

        # ── Область сообщений ─────────────────────────────────────────────────
        chat_wrap = tk.Frame(self, bg=BG)
        chat_wrap.pack(fill="both", expand=True)

        self._canvas = tk.Canvas(chat_wrap, bg=BG, highlightthickness=0, bd=0)
        vsb = tk.Scrollbar(chat_wrap, orient="vertical", command=self._canvas.yview,
                           width=8, bg=BG_PANEL, troughcolor=BG, relief="flat", bd=0)
        vsb.pack(side="right", fill="y")
        self._canvas.pack(fill="both", expand=True)
        self._canvas.configure(yscrollcommand=vsb.set)

        self._msgs = tk.Frame(self._canvas, bg=BG)
        self._win  = self._canvas.create_window((0, 0), window=self._msgs, anchor="nw")
        self._msgs.bind("<Configure>",
                        lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>",
                          lambda e: self._canvas.itemconfig(self._win, width=e.width))

        for w in (self._canvas, self._msgs, chat_wrap):
            w.bind("<MouseWheel>",
                   lambda e: self._canvas.yview_scroll(-1*(e.delta//120), "units"), add="+")
            w.bind("<Button-4>",
                   lambda e: self._canvas.yview_scroll(-3, "units"), add="+")
            w.bind("<Button-5>",
                   lambda e: self._canvas.yview_scroll( 3, "units"), add="+")

        # Индикатор печатания
        self._typing_lbl = tk.Label(self._msgs, text="", bg=BG, fg=TEXT_SOFT,
                                     font=("Arial", 10, "italic"))

        # ── Панель ввода ──────────────────────────────────────────────────────
        inp_wrap = tk.Frame(self, bg=BG_PANEL)
        inp_wrap.pack(fill="x", side="bottom")
        tk.Frame(inp_wrap, bg=BORDER_D, height=1).pack(fill="x")

        # Строка прикреплённого файла (показывается если есть)
        self._attach_bar = tk.Frame(inp_wrap, bg="#FFFBE6")
        self._attach_lbl = tk.Label(self._attach_bar, text="", bg="#FFFBE6",
                                     fg="#8A5A00", font=("Arial", 10))
        self._attach_lbl.pack(side="left", padx=8, pady=3)
        tk.Button(self._attach_bar, text="✕", command=self._detach_file,
                  bg="#FFFBE6", fg="#AA1A1A", relief="flat",
                  font=("Arial", 10, "bold"), cursor="hand2").pack(side="right", padx=4)

        inner = tk.Frame(inp_wrap, bg=BG_PANEL)
        inner.pack(fill="both", expand=True, padx=8, pady=8)

        # Кнопка «+» (скрепка)
        self._attach_btn = tk.Button(
            inner, text="+",
            command=self._open_attach_dialog,
            bg="#E8E8E8", fg=TEXT, relief="flat",
            font=("Arial", 16, "bold"), cursor="hand2",
            width=3, activebackground="#DDDDDD",
        )
        self._attach_btn.pack(side="left", fill="y", padx=(0, 6))

        # Кнопка отправки
        send_f = tk.Frame(inner, bg=BG_PANEL, width=88)
        send_f.pack(side="right", fill="y", padx=(6, 0))
        send_f.pack_propagate(False)
        self._send_btn = tk.Button(
            send_f, text="↑\nОтправить",
            command=self._send,
            bg=BG_TOPBAR, fg=TEXT_INV,
            font=("Arial", 10, "bold"), relief="flat",
            cursor="hand2", activebackground="#333333",
            activeforeground=TEXT_INV, bd=0,
        )
        self._send_btn.pack(fill="both", expand=True)

        # Поле ввода
        self._input = tk.Text(
            inner, font=("Arial", 12), wrap="word",
            relief="solid", bd=1, bg=BG, fg=TEXT,
            insertbackground=TEXT, padx=8, pady=6, height=3,
        )
        self._input.pack(side="left", fill="both", expand=True)
        self._input.bind("<Return>",       self._on_enter)
        self._input.bind("<Shift-Return>", lambda e: None)

    # ══════════════════════════════════════════════════════════════════════════
    # ATTACH / DETACH FILE
    # ══════════════════════════════════════════════════════════════════════════
    def _open_attach_dialog(self):
        """Открывает диалог выбора файла или изображения."""
        path = filedialog.askopenfilename(
            title="Прикрепить файл",
            filetypes=[
                ("Изображения",      "*.png *.jpg *.jpeg *.gif *.webp *.bmp"),
                ("Текст и код",      "*.txt *.py *.log *.md *.json *.csv *.ini"),
                ("ZIP-архивы",       "*.zip"),
                ("Аудио",            "*.ogg *.mp3 *.wav *.m4a"),
                ("Все файлы",        "*.*"),
            ]
        )
        if not path:
            return
        p   = Path(path)
        ext = p.suffix.lower()
        if ext in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}:
            self._pending_file = {"type": "image", "path": str(p), "name": p.name}
        elif ext in {".ogg", ".mp3", ".wav", ".m4a"}:
            self._pending_file = {"type": "audio", "path": str(p), "name": p.name}
        else:
            self._pending_file = {"type": "file",  "path": str(p), "name": p.name}

        self._attach_lbl.configure(text=f"📎 {p.name}")
        self._attach_bar.pack(fill="x", before=self._input.master)

    def _detach_file(self):
        self._pending_file = None
        self._attach_bar.pack_forget()
        self._attach_lbl.configure(text="")

    # ══════════════════════════════════════════════════════════════════════════
    # MESSAGES RENDERING
    # ══════════════════════════════════════════════════════════════════════════
    def _add_msg(self, role: str, text: str, image_bytes: bytes | None = None):
        is_user = (role == "user")
        bg_bub  = "#1A1A1A" if is_user else "#E8F0FE"
        fg_bub  = "#FFFFFF" if is_user else "#1A1A1A"
        fg_name = "#888888" if is_user else CHART_BLUE
        accent  = "#555555" if is_user else CHART_BLUE

        row = tk.Frame(self._msgs, bg=BG)
        row.pack(fill="x", pady=2, padx=8)

        bub = tk.Frame(row, bg=bg_bub)
        if is_user:
            bub.pack(side="right", anchor="e", padx=(60, 0))
        else:
            bub.pack(side="left",  anchor="w", padx=(0, 60))

        tk.Frame(bub, bg=accent, height=2).pack(fill="x")
        sender = "Ты" if is_user else "Murka"
        tk.Label(bub, text=sender, bg=bg_bub, fg=fg_name,
                 font=("Arial", 8, "bold")).pack(anchor="w", padx=10, pady=(5, 0))

        # Картинка (если передана)
        if image_bytes and _PIL:
            try:
                img = PILImage.open(io.BytesIO(image_bytes))
                img.thumbnail((320, 320), PILImage.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                lbl_img = tk.Label(bub, image=photo, bg=bg_bub)
                lbl_img.pack(padx=10, pady=4)
                lbl_img._photo = photo   # keep reference
            except Exception:
                pass

        # Текст
        if text:
            tk.Label(
                bub, text=text, bg=bg_bub, fg=fg_bub,
                font=("Arial", 11), anchor="w", justify="left",
                wraplength=400, padx=10, pady=4,
            ).pack(anchor="w", fill="x")

        tk.Label(bub, text=datetime.now().strftime("%H:%M"),
                 bg=bg_bub, fg="#888888" if is_user else "#7F8C8D",
                 font=("Arial", 8)).pack(anchor="e", padx=10, pady=(0, 5))

        self._canvas.after(60, lambda: self._canvas.yview_moveto(1.0))

    def _set_typing(self, on: bool):
        if on:
            self._typing_lbl.configure(text="  Murka печатает...")
            self._typing_lbl.pack(anchor="w", padx=12, pady=2)
            self._send_btn.configure(state="disabled", bg="#555555", text="⏳\nЖди...")
            self._status_lbl.configure(text="печатает ●", fg=CHART_AMBER)
        else:
            self._typing_lbl.configure(text="")
            self._typing_lbl.pack_forget()
            self._send_btn.configure(state="normal", bg=BG_TOPBAR, text="↑\nОтправить")
            self._status_lbl.configure(text="онлайн ●", fg=CHART_GREEN)
        self._canvas.after(60, lambda: self._canvas.yview_moveto(1.0))

    # ══════════════════════════════════════════════════════════════════════════
    # SEND / RECEIVE
    # ══════════════════════════════════════════════════════════════════════════
    def _on_enter(self, event):
        if not (event.state & 0x1):
            self._send()
            return "break"

    def _send(self):
        if self._typing:
            return
        text = self._input.get("1.0", "end").strip()
        attach = self._pending_file

        if not text and not attach:
            return

        # Показываем сообщение пользователя
        display_text = text
        if attach:
            display_text = (f"📎 {attach['name']}\n" + text) if text else f"📎 {attach['name']}"

        self._input.delete("1.0", "end")
        self._detach_file()
        self._add_msg("user", display_text)

        self._typing = True
        self._set_typing(True)

        threading.Thread(
            target=self._process_request,
            args=(text, attach),
            daemon=True
        ).start()

    def _process_request(self, text: str, attach: dict | None):
        """Основная логика обработки запроса (фоновый поток)."""
        uid = self.username
        answer_text  = ""
        answer_image = None

        try:
            # ── Проверяем: рисование ─────────────────────────────────────────
            if text and (text.startswith("Нарисуй") or text.startswith("нарисуй")):
                self.after(0, lambda: self._status_lbl.configure(
                    text="рисует 🎨", fg=CHART_BLUE))
                img_bytes = engine.draw(text)
                if img_bytes:
                    answer_text  = "На хавай 🎨"
                    answer_image = img_bytes
                else:
                    answer_text = "Анлучка Pollinations.ai недоступен."

            # ── Прикреплённый файл ───────────────────────────────────────────
            elif attach:
                if attach["type"] == "image":
                    b64, mt = image_to_base64(attach["path"])
                    answer_text = engine.chat_with_image(
                        uid, text or "Что на этом изображении?", b64, mt)

                elif attach["type"] == "audio":
                    raw = Path(attach["path"]).read_bytes()
                    transcript  = engine.transcribe(raw, attach["name"])
                    answer_text = engine.chat(
                        uid,
                        f"[Голосовое сообщение расшифровано]: {transcript}"
                        + (f"\n{text}" if text else "")
                    )

                else:  # text/code/zip
                    file_content = read_file_content(attach["path"])
                    answer_text  = engine.chat(
                        uid,
                        text or f"Объясни содержимое файла {attach['name']}",
                        extra_context=file_content
                    )

            # ── Обычный текст ────────────────────────────────────────────────
            else:
                answer_text = engine.chat(uid, text)
                engine.extract_fact_bg(uid, text)

        except Exception as e:
            answer_text = f"Ошибка: {e} 😾"

        self.after(0, self._on_response, answer_text, answer_image)

    def _on_response(self, text: str, image_bytes: bytes | None = None):
        self._typing = False
        self._set_typing(False)
        self._add_msg("assistant", text, image_bytes=image_bytes)

    # ══════════════════════════════════════════════════════════════════════════
    # UTILITY
    # ══════════════════════════════════════════════════════════════════════════
    def _clear_history(self):
        memory.clear(self.username)
        for w in self._msgs.winfo_children():
            w.destroy()
        self._typing_lbl.pack_forget()
        self._add_msg("assistant",
                      "пипец што ты наделал 😭😭😭")
