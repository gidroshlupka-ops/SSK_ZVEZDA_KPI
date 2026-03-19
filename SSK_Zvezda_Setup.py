"""
SSK_Zvezda_Setup.py
Установщик ССК Звезда KPI Monitor v5
──────────────────────────────────────────────────────────────────
Запускается рядом с SSK_Zvezda_KPI.exe
Спрашивает куда установить, копирует файлы, создаёт ярлык, прописывает деинсталлятор.
"""

import sys, os, shutil, threading, winreg, time
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

# ── Версия и мета ──────────────────────────────────────────────────────────────
APP_NAME    = "ССК Звезда — KPI Monitor"
APP_VERSION = "5.0"
APP_EXE     = "SSK_Zvezda_KPI.exe"
PUBLISHER   = "ССК Звезда"
UNINSTALLER = "Uninstall.exe"

# ── Цвета ─────────────────────────────────────────────────────────────────────
BG      = "#FFFFFF"
TOPBAR  = "#1A1A1A"
PANEL   = "#F5F5F5"
BORDER  = "#DDDDDD"
TEXT    = "#1A1A1A"
TEXT_M  = "#555555"
TEXT_S  = "#888888"
GREEN   = "#1A7A3A"
RED     = "#AA1A1A"
INV     = "#FFFFFF"
BLUE    = "#2980B9"


class InstallerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"Установка — {APP_NAME}")
        self.geometry("580x520")
        self.resizable(False, False)
        self.configure(bg=BG)
        try:
            self.iconbitmap(self._find_ico())
        except Exception:
            pass

        self._step     = 0
        self._dst_var  = tk.StringVar()
        self._shortcut = tk.BooleanVar(value=True)
        self._desktop  = tk.BooleanVar(value=True)
        self._agree    = tk.BooleanVar(value=False)

        # По умолчанию — Program Files
        pf = os.environ.get("ProgramFiles", "C:\\Program Files")
        self._dst_var.set(str(Path(pf) / "SSK_Zvezda_KPI"))

        self._frames = {}
        self._build_topbar()
        self._content = tk.Frame(self, bg=BG)
        self._content.pack(fill="both", expand=True)
        self._build_footer()

        self._show_step(0)

    # ── Topbar ────────────────────────────────────────────────────────────────
    def _build_topbar(self):
        top = tk.Frame(self, bg=TOPBAR, height=64)
        top.pack(fill="x"); top.pack_propagate(False)
        tk.Label(top, text="ССК «ЗВЕЗДА»", bg=TOPBAR, fg=INV,
                 font=("Arial",15,"bold")).place(x=20, y=10)
        tk.Label(top, text="Мастер установки", bg=TOPBAR, fg="#AAAAAA",
                 font=("Arial",10)).place(x=20, y=36)
        tk.Label(top, text=f"v{APP_VERSION}", bg=TOPBAR, fg="#777777",
                 font=("Arial",9)).place(relx=1.0, x=-20, y=22, anchor="ne")

    # ── Footer ────────────────────────────────────────────────────────────────
    def _build_footer(self):
        foot = tk.Frame(self, bg=PANEL, height=54)
        foot.pack(fill="x", side="bottom"); foot.pack_propagate(False)
        tk.Frame(foot, bg=BORDER, height=1).pack(fill="x")

        self._btn_next = tk.Button(foot, text="Далее  ›",
            command=self._next, bg=TOPBAR, fg=INV,
            font=("Arial",11,"bold"), relief="flat",
            padx=20, pady=6, cursor="hand2",
            activebackground="#333333", activeforeground=INV)
        self._btn_next.pack(side="right", padx=14, pady=10)

        self._btn_back = tk.Button(foot, text="‹  Назад",
            command=self._back, bg=PANEL, fg=TEXT,
            font=("Arial",11), relief="flat",
            padx=14, pady=6, cursor="hand2",
            activebackground="#E0E0E0")
        self._btn_back.pack(side="right", padx=2, pady=10)

        self._btn_cancel = tk.Button(foot, text="Отмена",
            command=self._cancel, bg=PANEL, fg=TEXT_M,
            font=("Arial",10), relief="flat",
            padx=14, pady=6, cursor="hand2",
            activebackground="#E0E0E0")
        self._btn_cancel.pack(side="left", padx=14, pady=10)

    # ── Steps ─────────────────────────────────────────────────────────────────
    def _show_step(self, n):
        self._step = n
        for f in self._content.winfo_children():
            f.pack_forget()
        builders = [
            self._step_welcome,
            self._step_license,
            self._step_path,
            self._step_options,
            self._step_confirm,
            self._step_install,
            self._step_done,
        ]
        key = str(n)
        if key not in self._frames:
            self._frames[key] = builders[n]()
        self._frames[key].pack(fill="both", expand=True)

        # Кнопки
        self._btn_back.configure(state="normal" if 0 < n < 5 else "disabled")
        self._btn_next.configure(
            text="Установить" if n == 4 else ("Готово" if n == 6 else "Далее  ›"),
            state="normal")
        if n in (5, 6):
            self._btn_back.configure(state="disabled")
            self._btn_cancel.configure(state="disabled" if n == 5 else "normal",
                                       text="Закрыть" if n == 6 else "Отмена")
            if n == 6:
                self._btn_next.configure(text="Запустить  ›")

    def _next(self):
        if self._step == 1 and not self._agree.get():
            messagebox.showwarning("Лицензия", "Примите лицензионное соглашение для продолжения.")
            return
        if self._step == 6:
            self._launch_app(); return
        if self._step == 4:
            self._show_step(5)
            threading.Thread(target=self._do_install, daemon=True).start()
            return
        self._show_step(self._step + 1)

    def _back(self):
        if 0 < self._step < 5:
            self._show_step(self._step - 1)

    def _cancel(self):
        if self._step == 6:
            self.destroy(); return
        if messagebox.askyesno("Отмена установки", "Прервать установку ССК Звезда?"):
            self.destroy()

    # ── Step 0: Добро пожаловать ──────────────────────────────────────────────
    def _step_welcome(self):
        f = tk.Frame(self._content, bg=BG)
        # Большой логотип-блок
        hero = tk.Frame(f, bg="#F0F0F0", height=140)
        hero.pack(fill="x"); hero.pack_propagate(False)
        tk.Label(hero, text="⚙", bg="#F0F0F0", fg=TOPBAR,
                 font=("Segoe UI",52)).place(x=30, y=20)
        tk.Label(hero, text=APP_NAME, bg="#F0F0F0", fg=TEXT,
                 font=("Arial",17,"bold")).place(x=110, y=30)
        tk.Label(hero, text=f"Версия {APP_VERSION}  ·  {PUBLISHER}",
                 bg="#F0F0F0", fg=TEXT_M,
                 font=("Arial",10)).place(x=112, y=64)
        tk.Label(hero, text="Система учёта KPI и складских запасов",
                 bg="#F0F0F0", fg=TEXT_S,
                 font=("Arial",10)).place(x=112, y=90)

        body = tk.Frame(f, bg=BG)
        body.pack(fill="both", expand=True, padx=30, pady=20)
        tk.Label(body, text="Добро пожаловать в мастер установки!",
                 bg=BG, fg=TEXT, font=("Arial",13,"bold")).pack(anchor="w")
        tk.Label(body, text=
            "Этот мастер установит ССК Звезда KPI Monitor на ваш компьютер.\n\n"
            "Приложение включает:\n"
            "  • Систему учёта KPI сотрудников\n"
            "  • Управление складскими запасами\n"
            "  • Генерацию отчётов Word\n"
            "  • Синхронизацию с облачной БД Supabase\n"
            "  • Telegram-уведомления\n\n"
            "Нажмите «Далее» для продолжения.",
            bg=BG, fg=TEXT_M, font=("Arial",11),
            justify="left", anchor="nw").pack(anchor="w", pady=(8,0))
        return f

    # ── Step 1: Лицензия ──────────────────────────────────────────────────────
    def _step_license(self):
        f = tk.Frame(self._content, bg=BG)
        self._page_header(f, "Лицензионное соглашение",
                          "Прочитайте соглашение перед установкой.")
        txt = tk.Text(f, height=12, bg=PANEL, fg=TEXT_M,
                      font=("Arial",9), wrap="word",
                      relief="flat", bd=0, padx=10, pady=8)
        txt.pack(fill="both", expand=True, padx=20)
        license_text = (
            "ЛИЦЕНЗИОННОЕ СОГЛАШЕНИЕ\n"
            "ССК Звезда KPI Monitor v5\n\n"
            "Настоящее соглашение заключается между пользователем и предприятием ССК «Звезда».\n\n"
            "1. ПРЕДОСТАВЛЕНИЕ ЛИЦЕНЗИИ\n"
            "Данное программное обеспечение предоставляется для использования исключительно "
            "сотрудниками и уполномоченными лицами ССК «Звезда». Любое использование в иных "
            "целях запрещено.\n\n"
            "2. ОГРАНИЧЕНИЯ\n"
            "Пользователь не вправе: копировать, распространять, продавать, "
            "изменять или передавать программное обеспечение третьим лицам "
            "без письменного разрешения правообладателя.\n\n"
            "3. КОНФИДЕНЦИАЛЬНОСТЬ\n"
            "Все данные, обрабатываемые системой (информация о сотрудниках, KPI, "
            "складские остатки), являются конфиденциальными и не подлежат разглашению.\n\n"
            "4. ОГРАНИЧЕНИЕ ОТВЕТСТВЕННОСТИ\n"
            "Программное обеспечение предоставляется «как есть». Разработчики не несут "
            "ответственности за прямые или косвенные убытки, возникшие в результате "
            "использования программы.\n\n"
            "5. ОБНОВЛЕНИЯ\n"
            "Правообладатель вправе выпускать обновления программы. Пользователь обязуется "
            "устанавливать критические обновления безопасности.\n\n"
            "Нажимая «Далее», вы подтверждаете, что прочитали, поняли и принимаете "
            "все условия данного соглашения."
        )
        txt.insert("1.0", license_text)
        txt.configure(state="disabled")
        cb_f = tk.Frame(f, bg=BG); cb_f.pack(anchor="w", padx=20, pady=8)
        tk.Checkbutton(cb_f, text="Я прочитал(-а) и принимаю условия лицензионного соглашения",
                       variable=self._agree, bg=BG, fg=TEXT,
                       font=("Arial",10), activebackground=BG).pack(side="left")
        return f

    # ── Step 2: Путь установки ────────────────────────────────────────────────
    def _step_path(self):
        f = tk.Frame(self._content, bg=BG)
        self._page_header(f, "Папка установки",
                          "Выберите, куда установить ССК Звезда KPI Monitor.")

        body = tk.Frame(f, bg=BG); body.pack(fill="x", padx=24, pady=8)
        tk.Label(body, text="Папка установки:", bg=BG, fg=TEXT,
                 font=("Arial",11,"bold")).pack(anchor="w", pady=(0,4))

        row = tk.Frame(body, bg=BG); row.pack(fill="x")
        self._path_entry = tk.Entry(row, textvariable=self._dst_var,
                                    font=("Arial",11), relief="solid", bd=1,
                                    bg=BG, fg=TEXT)
        self._path_entry.pack(side="left", fill="x", expand=True, ipady=6)
        tk.Button(row, text="Обзор...", command=self._browse_dst,
                  font=("Arial",10), bg=PANEL, relief="flat",
                  padx=12, cursor="hand2").pack(side="left", padx=(6,0), ipady=6)

        # Место на диске
        info_f = tk.Frame(body, bg=PANEL); info_f.pack(fill="x", pady=12)
        tk.Frame(info_f, bg=BORDER, height=1).pack(fill="x")
        inner = tk.Frame(info_f, bg=PANEL); inner.pack(fill="x", padx=10, pady=8)
        tk.Label(inner, text="Требуется места на диске:", bg=PANEL,
                 fg=TEXT_M, font=("Arial",10)).pack(anchor="w")
        tk.Label(inner, text="≈ 80 МБ  (включая Python-зависимости)",
                 bg=PANEL, fg=TEXT, font=("Arial",10,"bold")).pack(anchor="w")
        tk.Label(inner, text="Рекомендуется: C:\\Program Files\\SSK_Zvezda_KPI",
                 bg=PANEL, fg=TEXT_S, font=("Arial",9)).pack(anchor="w", pady=(4,0))

        tk.Label(body, text="⚠  Для установки в Program Files может потребоваться "
                            "подтверждение администратора.",
                 bg=BG, fg=TEXT_S, font=("Arial",9),
                 wraplength=500, justify="left").pack(anchor="w", pady=4)
        return f

    def _browse_dst(self):
        d = filedialog.askdirectory(title="Выберите папку установки",
                                    initialdir=self._dst_var.get())
        if d:
            self._dst_var.set(d.replace("/", "\\"))

    # ── Step 3: Параметры ─────────────────────────────────────────────────────
    def _step_options(self):
        f = tk.Frame(self._content, bg=BG)
        self._page_header(f, "Параметры установки",
                          "Настройте дополнительные параметры.")
        body = tk.Frame(f, bg=BG); body.pack(fill="x", padx=24, pady=8)

        def chk(var, text, note=""):
            r = tk.Frame(body, bg=BG); r.pack(fill="x", pady=6)
            tk.Checkbutton(r, variable=var, text=text,
                           bg=BG, fg=TEXT, font=("Arial",11),
                           activebackground=BG).pack(anchor="w")
            if note:
                tk.Label(r, text=f"       {note}", bg=BG, fg=TEXT_S,
                         font=("Arial",9)).pack(anchor="w")

        tk.Label(body, text="Ярлыки запуска:", bg=BG, fg=TEXT,
                 font=("Arial",11,"bold")).pack(anchor="w", pady=(0,6))
        chk(self._shortcut, "Создать ярлык в меню «Пуск»",
            "Папка: Пуск → Программы → ССК Звезда")
        chk(self._desktop,  "Создать ярлык на рабочем столе")

        tk.Frame(body, bg=BORDER, height=1).pack(fill="x", pady=10)
        tk.Label(body, text="После установки:", bg=BG, fg=TEXT,
                 font=("Arial",11,"bold")).pack(anchor="w", pady=(0,6))

        self._launch_after = tk.BooleanVar(value=True)
        chk(self._launch_after, "Запустить ССК Звезда после установки")

        tk.Frame(body, bg=BORDER, height=1).pack(fill="x", pady=10)
        tk.Label(body,
            text="ℹ  После первого запуска введите данные Supabase в Настройках\n"
                 "    для облачной синхронизации между компьютерами.\n"
                 "    Логин по умолчанию: admin  /  Пароль: admin",
            bg=BG, fg=TEXT_S, font=("Arial",9),
            justify="left").pack(anchor="w")
        return f

    # ── Step 4: Подтверждение ─────────────────────────────────────────────────
    def _step_confirm(self):
        f = tk.Frame(self._content, bg=BG)
        self._page_header(f, "Готово к установке",
                          "Проверьте параметры и нажмите «Установить».")
        body = tk.Frame(f, bg=BG); body.pack(fill="both", expand=True, padx=24, pady=8)

        def row(lbl, val, color=TEXT):
            r = tk.Frame(body, bg=BG); r.pack(fill="x", pady=4)
            tk.Label(r, text=lbl, bg=BG, fg=TEXT_M,
                     font=("Arial",10), width=24, anchor="w").pack(side="left")
            tk.Label(r, text=val, bg=BG, fg=color,
                     font=("Arial",10,"bold"), anchor="w").pack(side="left")

        row("Приложение:",     APP_NAME)
        row("Версия:",         APP_VERSION)
        row("Папка установки:", self._dst_var.get())
        row("Ярлык в Пуске:",  "Да" if self._shortcut.get() else "Нет",
            GREEN if self._shortcut.get() else TEXT_S)
        row("Ярлык на рабочем столе:", "Да" if self._desktop.get() else "Нет",
            GREEN if self._desktop.get() else TEXT_S)
        row("Запустить после установки:", "Да" if self._launch_after.get() else "Нет")

        tk.Frame(body, bg=BORDER, height=1).pack(fill="x", pady=12)
        tk.Label(body,
            text="Нажмите «Установить» для начала установки.\n"
                 "Процесс займёт несколько минут.",
            bg=BG, fg=TEXT_M, font=("Arial",10)).pack(anchor="w")
        return f

    # ── Step 5: Установка ─────────────────────────────────────────────────────
    def _step_install(self):
        f = tk.Frame(self._content, bg=BG)
        self._page_header(f, "Установка...",
                          "Подождите, идёт установка ССК Звезда KPI Monitor.")
        body = tk.Frame(f, bg=BG); body.pack(fill="both", expand=True, padx=24, pady=8)

        self._inst_lbl = tk.Label(body, text="Подготовка...",
                                   bg=BG, fg=TEXT, font=("Arial",11))
        self._inst_lbl.pack(anchor="w")

        # Прогрессбар (tk.Canvas чтобы не зависеть от ttk)
        pb_bg = tk.Frame(body, bg=BORDER, height=28)
        pb_bg.pack(fill="x", pady=8)
        self._pb_inner = tk.Frame(pb_bg, bg=GREEN, height=28)
        self._pb_inner.place(x=0, y=0, relheight=1, width=0)
        self._pb_bg_frame = pb_bg

        self._pct_lbl = tk.Label(body, text="0%", bg=BG,
                                  fg=TEXT_M, font=("Arial",10))
        self._pct_lbl.pack(anchor="e")

        self._log_box = tk.Text(body, height=8, bg=PANEL, fg=TEXT_M,
                                 font=("Courier New",9), relief="flat",
                                 bd=0, state="disabled", wrap="word")
        self._log_box.pack(fill="both", expand=True, pady=4)
        return f

    def _log(self, msg):
        self._log_box.configure(state="normal")
        self._log_box.insert("end", msg + "\n")
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    def _progress(self, pct, msg=""):
        self.after(0, self._set_progress, pct, msg)

    def _set_progress(self, pct, msg):
        w = int(self._pb_bg_frame.winfo_width() * pct / 100)
        self._pb_inner.place(width=w)
        self._pct_lbl.configure(text=f"{pct}%")
        if msg:
            self._inst_lbl.configure(text=msg)
            self._log(f"[{pct:3d}%] {msg}")

    def _do_install(self):
        dst = Path(self._dst_var.get())
        src = Path(sys.executable).parent if getattr(sys,"frozen",False) else Path(__file__).parent

        steps = [
            (5,  "Создание папки установки...",     lambda: dst.mkdir(parents=True, exist_ok=True)),
            (15, "Копирование исполняемого файла...", lambda: self._copy_exe(src, dst)),
            (30, "Копирование модулей...",            lambda: self._copy_dir(src/"modules", dst/"modules")),
            (45, "Копирование ресурсов...",           lambda: self._copy_dir(src/"assets", dst/"assets")),
            (55, "Создание config.ini...",            lambda: self._create_config(dst)),
            (65, "Регистрация в реестре Windows...", lambda: self._register(dst)),
            (75, "Создание деинсталлятора...",       lambda: self._create_uninstaller(dst)),
            (85, "Создание ярлыков...",               lambda: self._create_shortcuts(dst)),
            (95, "Финальная проверка...",             lambda: self._verify(dst)),
            (100,"Установка завершена!",              lambda: None),
        ]
        try:
            for pct, msg, fn in steps:
                self._progress(pct, msg)
                fn()
                time.sleep(0.3)
            self.after(500, lambda: self._show_step(6))
        except Exception as e:
            self.after(0, lambda: self._inst_lbl.configure(
                text=f"Ошибка: {e}", fg=RED))
            self.after(0, lambda: self._log(f"ОШИБКА: {e}"))

    def _copy_exe(self, src, dst):
        exe = src / APP_EXE
        if exe.exists():
            shutil.copy2(exe, dst / APP_EXE)
        else:
            # Dev mode — копируем скрипт
            shutil.copy2(src / "The_Storm.py", dst / "The_Storm.py")

    def _copy_dir(self, src_dir, dst_dir):
        if src_dir.exists():
            if dst_dir.exists():
                shutil.rmtree(dst_dir)
            shutil.copytree(src_dir, dst_dir)

    def _create_config(self, dst):
        cfg = dst / "config.ini"
        if not cfg.exists():
            cfg.write_text(
                "[supabase]\nurl = \nanon_key = \n\n"
                "[telegram]\nbot_token = \nchat_id = \n\n"
                "[github]\ntoken = \nrepo_url = \n\n"
                "[sync]\ninterval_minutes = 5\nbackend = supabase\n\n"
                "[app]\nremember_me = false\nhardware_bind = false\nminimize_to_tray = false\n\n"
                "[umamusume]\npage_limit = 50\npage_size = 50\n\n"
                "[nautica]\nreport_path = \nreport_template = official\nkpi_red_zone = 40\n",
                encoding="utf-8")

    def _register(self, dst):
        try:
            exe   = dst / APP_EXE
            key   = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\SSKZvezdaKPI"
            unreg = dst / UNINSTALLER
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key) as k:
                winreg.SetValueEx(k, "DisplayName",     0, winreg.REG_SZ, APP_NAME)
                winreg.SetValueEx(k, "DisplayVersion",  0, winreg.REG_SZ, APP_VERSION)
                winreg.SetValueEx(k, "Publisher",       0, winreg.REG_SZ, PUBLISHER)
                winreg.SetValueEx(k, "InstallLocation", 0, winreg.REG_SZ, str(dst))
                winreg.SetValueEx(k, "UninstallString", 0, winreg.REG_SZ, str(unreg))
                winreg.SetValueEx(k, "DisplayIcon",     0, winreg.REG_SZ, str(exe))
                winreg.SetValueEx(k, "NoModify",        0, winreg.REG_DWORD, 1)
        except Exception as e:
            self._log(f"Реестр (предупреждение): {e}")

    def _create_uninstaller(self, dst):
        script = dst / "uninstall.bat"
        script.write_text(
            "@echo off\n"
            "echo Удаление ССК Звезда KPI Monitor...\n"
            f'reg delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\SSKZvezdaKPI" /f 2>nul\n'
            f'rmdir /s /q "{dst}"\n'
            "echo Программа удалена.\n"
            "pause\n",
            encoding="cp1251")

    def _create_shortcuts(self, dst):
        exe = dst / APP_EXE
        if not exe.exists():
            exe = dst / "The_Storm.py"

        # Пытаемся через win32com (если доступен)
        try:
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")

            if self._desktop.get():
                desktop = Path(shell.SpecialFolders("Desktop"))
                lnk     = str(desktop / f"{APP_NAME}.lnk")
                s = shell.CreateShortcut(lnk)
                s.TargetPath       = str(exe)
                s.WorkingDirectory = str(dst)
                s.Description      = APP_NAME
                try: s.IconLocation = str(dst/"assets"/"izolde.ico")
                except Exception: pass
                s.Save()

            if self._shortcut.get():
                start = Path(shell.SpecialFolders("Programs")) / PUBLISHER
                start.mkdir(exist_ok=True)
                lnk = str(start / f"{APP_NAME}.lnk")
                s = shell.CreateShortcut(lnk)
                s.TargetPath       = str(exe)
                s.WorkingDirectory = str(dst)
                s.Description      = APP_NAME
                try: s.IconLocation = str(dst/"assets"/"izolde.ico")
                except Exception: pass
                s.Save()
        except ImportError:
            # Fallback: создаём .url файл
            if self._desktop.get():
                desktop = Path.home() / "Desktop"
                url = desktop / f"{APP_NAME}.url"
                url.write_text(f"[InternetShortcut]\nURL=file:///{exe}\n", encoding="utf-8")

    def _verify(self, dst):
        exe = dst / APP_EXE
        py  = dst / "The_Storm.py"
        if not exe.exists() and not py.exists():
            raise FileNotFoundError(f"Исполняемый файл не найден в {dst}")

    # ── Step 6: Готово ────────────────────────────────────────────────────────
    def _step_done(self):
        f = tk.Frame(self._content, bg=BG)

        hero = tk.Frame(f, bg="#E8F8F0", height=120)
        hero.pack(fill="x"); hero.pack_propagate(False)
        tk.Label(hero, text="✓", bg="#E8F8F0", fg=GREEN,
                 font=("Arial",52,"bold")).place(x=30, y=20)
        tk.Label(hero, text="Установка завершена!", bg="#E8F8F0",
                 fg=GREEN, font=("Arial",16,"bold")).place(x=100, y=32)
        tk.Label(hero, text=f"{APP_NAME}  v{APP_VERSION}",
                 bg="#E8F8F0", fg=TEXT_M,
                 font=("Arial",10)).place(x=102, y=66)

        body = tk.Frame(f, bg=BG); body.pack(fill="both", expand=True, padx=24, pady=16)
        tk.Label(body, text="Что делать дальше:", bg=BG, fg=TEXT,
                 font=("Arial",12,"bold")).pack(anchor="w")
        steps_text = (
            "  1.  Запустите ССК Звезда KPI Monitor\n"
            "  2.  Войдите: логин admin  /  пароль admin\n"
            "  3.  Смените пароль в Настройках → Безопасность\n"
            "  4.  Введите данные Supabase в Настройках → Подключение\n"
            "       (для облачной синхронизации между несколькими ПК)\n"
            "  5.  Нажмите «Импортировать SQLite → Supabase» для первичной\n"
            "       загрузки тестовых данных в облако"
        )
        tk.Label(body, text=steps_text, bg=BG, fg=TEXT_M,
                 font=("Arial",10), justify="left",
                 anchor="nw").pack(anchor="w", pady=(6,0))

        tk.Label(body, text=f"\nПапка установки: {self._dst_var.get()}",
                 bg=BG, fg=TEXT_S, font=("Arial",9)).pack(anchor="w")
        return f

    def _launch_app(self):
        dst = Path(self._dst_var.get())
        exe = dst / APP_EXE
        py  = dst / "The_Storm.py"
        try:
            import subprocess
            if exe.exists():
                subprocess.Popen([str(exe)], cwd=str(dst))
            elif py.exists():
                subprocess.Popen([sys.executable, str(py)], cwd=str(dst))
        except Exception as e:
            messagebox.showerror("Ошибка запуска", str(e))
        self.destroy()

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _page_header(self, parent, title, subtitle=""):
        h = tk.Frame(parent, bg=BG, height=60); h.pack(fill="x"); h.pack_propagate(False)
        tk.Frame(h, bg=TOPBAR, width=4).pack(fill="y", side="left")
        ri = tk.Frame(h, bg=BG); ri.pack(side="left", fill="y", padx=16)
        tk.Label(ri, text=title, bg=BG, fg=TEXT,
                 font=("Arial",14,"bold")).pack(anchor="w", pady=(10,0))
        if subtitle:
            tk.Label(ri, text=subtitle, bg=BG, fg=TEXT_S,
                     font=("Arial",9)).pack(anchor="w")
        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x")

    def _find_ico(self):
        for p in [Path("assets/izolde.ico"), Path(__file__).parent/"assets"/"izolde.ico"]:
            if p.exists(): return str(p)
        return ""


if __name__ == "__main__":
    app = InstallerApp()
    app.mainloop()
