"""
umamusume.py — Engine v5
BackgroundWorker: ресурсы + realtime polling Supabase
"""
import logging, threading, requests
log = logging.getLogger("umamusume")


class BackgroundWorker:
    def __init__(self, cfg):
        self.cfg      = cfg
        self._stop    = threading.Event()
        self._on_low  = None
        self._on_sync = None   # callback при появлении новых данных

    def start(self, on_low_resources=None, on_sync=None):
        self._on_low  = on_low_resources
        self._on_sync = on_sync
        threading.Thread(target=self._res_loop,    daemon=True, name="res").start()
        threading.Thread(target=self._realtime_loop, daemon=True, name="realtime").start()

    def stop(self):
        self._stop.set()

    def reload_cfg(self, cfg):
        self.cfg = cfg

    def _res_loop(self):
        """Проверка низких запасов — каждый час."""
        while not self._stop.wait(3600):
            if self._stop.is_set(): break
            try:
                from modules.rubuska import get_low_resources, send_telegram, get_all_employees
                low = get_low_resources()
                if low:
                    if self._on_low: self._on_low(low)
                    # Подробный TG-алерт
                    total_emps = len(get_all_employees())
                    lines = [
                        f"⚠️ *КРИТИЧЕСКИЕ ЗАПАСЫ — ССК Звезда*",
                        f"",
                        f"📅 Дата проверки: {__import__('datetime').datetime.now().strftime('%d.%m.%Y %H:%M')}",
                        f"🏭 Предприятие: ССК «Звезда»",
                        f"👥 Сотрудников в системе: {total_emps}",
                        f"",
                        f"📦 *Позиций ниже минимума: {len(low)}*",
                        f"",
                    ]
                    for r in low[:10]:
                        deficit = r["min_quantity"] - r["quantity"]
                        lines.append(f"🔴 *{r['name']}*")
                        lines.append(f"   Категория: {r['category']}")
                        lines.append(f"   Остаток: {r['quantity']} {r['unit']} | Минимум: {r['min_quantity']} {r['unit']}")
                        lines.append(f"   Дефицит: {deficit:.1f} {r['unit']}")
                        lines.append("")
                    if len(low) > 10:
                        lines.append(f"...и ещё {len(low)-10} позиций.")
                    lines.append("❗ Требуется незамедлительное пополнение склада.")
                    send_telegram(self.cfg, "\n".join(lines))
            except Exception as e:
                log.error("res_loop: %s", e)

    def _realtime_loop(self):
        """
        Polling Supabase каждые 15 сек — если данные изменились, вызываем on_sync.
        Сравниваем count() таблиц — быстро и без лишней нагрузки.
        """
        from modules.rubuska import is_cloud, get_sb
        last_state = {}
        while not self._stop.wait(15):
            if self._stop.is_set(): break
            if not is_cloud(): continue
            try:
                sb      = get_sb()
                current = {
                    "emp": sb.count("Employees"),
                    "res": sb.count("Resources"),
                    "kpi": sb.count("KPI_Logs"),
                    "ntf": sb.count("Notifications", "read=eq.false"),
                }
                if last_state and current != last_state:
                    changed = [k for k in current if current[k] != last_state.get(k, current[k])]
                    log.info("Realtime: изменения в %s", changed)
                    if self._on_sync:
                        self._on_sync(changed)
                last_state = current
            except Exception as e:
                log.debug("realtime: %s", e)


def create_tray_icon(app_ref, icon_path=None):
    try:
        import pystray
        from PIL import Image, ImageDraw
        from pathlib import Path
        if icon_path and Path(icon_path).exists():
            image = Image.open(icon_path).resize((32, 32))
        else:
            image = Image.new("RGB", (32, 32), "#1A1A1A")
            d = ImageDraw.Draw(image)
            d.text((8, 6), "Z", fill="#FFFFFF")

        def on_show(icon, item):
            if hasattr(app_ref, "show_window"): app_ref.show_window()

        def on_quit(icon, item):
            icon.stop()
            if hasattr(app_ref, "quit_app"): app_ref.quit_app()

        menu = pystray.Menu(
            pystray.MenuItem("Открыть", on_show, default=True),
            pystray.MenuItem("Выйти",   on_quit))
        return pystray.Icon("zvezda", image, "ССК Звезда — KPI", menu=menu)
    except ImportError:
        log.warning("pystray не установлен"); return None


def run_tray_in_thread(icon):
    if icon is None: return
    threading.Thread(target=icon.run, daemon=True, name="tray").start()
