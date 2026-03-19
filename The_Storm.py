"""The_Storm.py — Main Entry Point v5"""
import sys, logging
from pathlib import Path

if getattr(sys, "frozen", False):
    _base = Path(sys._MEIPASS)
    _data = Path(sys.executable).parent
else:
    _base = Path(__file__).parent
    _data = _base

sys.path.insert(0, str(_base))
sys.path.insert(0, str(_base / "modules"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(_data / "zvezda.log", encoding="utf-8"),
    ])
log = logging.getLogger("The_Storm")

def main():
    from modules.rubuska import load_config, init_db, set_cfg_ref, load_session
    from modules.izolde  import LoginWindow, MainApp

    cfg = load_config()
    set_cfg_ref(cfg)

    from modules.rubuska import is_cloud
    if not is_cloud():
        init_db()

    bind_hw    = cfg.getboolean("app", "hardware_bind", fallback=False)
    saved_user = load_session(bind_hw=bind_hw)

    def launch(username):
        app = MainApp(username=username, cfg=cfg)
        app.mainloop()

    if saved_user:
        launch(saved_user)
    else:
        done = [False]
        def on_login(u):
            done[0] = True
            launch(u)
        LoginWindow(cfg=cfg, on_success=on_login).mainloop()
        if not done[0]:
            sys.exit(0)

if __name__ == "__main__":
    main()
