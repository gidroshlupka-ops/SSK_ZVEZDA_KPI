"""
rubuska.py — Data Engine v5
SSK Zvezda | The First Whistle
"""
import sqlite3, sys, uuid, hashlib, configparser, logging, random, threading, base64
from datetime import datetime, timedelta
from pathlib import Path
from cryptography.fernet import Fernet
import bcrypt, requests

log = logging.getLogger("rubuska")

class _LocalSecrets:
    """
    Локальные секреты (приложение используется только владельцем, без публикации).
    Храним здесь, чтобы не светить в config.ini/UI.
    """
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    TG_BOT_TOKEN: str = ""
    TG_CHAT_ID: str = ""

def get_data_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent

DATA_PATH  = get_data_path()
DB_PATH    = DATA_PATH / "zvezda-kpi.db"
CFG_PATH   = DATA_PATH / "config.ini"
KEY_PATH   = DATA_PATH / ".session.key"
TOKEN_PATH = DATA_PATH / ".session.token"

_DEFAULTS = {
    "supabase":  {"url": "", "anon_key": ""},
    "github":    {"token": "", "repo_url": ""},
    "telegram":  {"bot_token": "", "chat_id": ""},
    "sync":      {"interval_minutes": "5", "backend": "supabase"},
    "app":       {"remember_me": "false", "hardware_bind": "false",
                  "minimize_to_tray": "false", "theme": "light"},
    "umamusume": {"page_limit": "50", "page_size": "50"},
    "nautica":   {"report_path": "", "report_template": "official", "kpi_red_zone": "40"},
}

def load_config() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    for s, v in _DEFAULTS.items():
        cfg[s] = dict(v)
    if CFG_PATH.exists():
        cfg.read(CFG_PATH, encoding="utf-8")
        for s, v in _DEFAULTS.items():
            if not cfg.has_section(s):
                cfg.add_section(s)
            for k, dv in v.items():
                if not cfg.has_option(s, k):
                    cfg.set(s, k, dv)
    save_config(cfg)
    return cfg

def save_config(cfg: configparser.ConfigParser):
    with open(CFG_PATH, "w", encoding="utf-8") as f:
        cfg.write(f)

# ── Session ────────────────────────────────────────────────────────────────────
def get_hardware_id():
    return hashlib.sha256(str(uuid.getnode()).encode()).hexdigest()[:32]

def _fernet():
    if KEY_PATH.exists():
        return Fernet(KEY_PATH.read_bytes())
    key = Fernet.generate_key()
    KEY_PATH.write_bytes(key)
    return Fernet(key)

def save_session(username, bind_hw=False):
    payload = f"{username}|{datetime.now().isoformat()}"
    if bind_hw:
        payload += f"|{get_hardware_id()}"
    TOKEN_PATH.write_bytes(_fernet().encrypt(payload.encode()))

def load_session(bind_hw=False):
    if not TOKEN_PATH.exists():
        return None
    try:
        parts = _fernet().decrypt(TOKEN_PATH.read_bytes()).decode().split("|")
        if bind_hw and len(parts) >= 3 and parts[2] != get_hardware_id():
            return None
        return parts[0]
    except Exception:
        return None

def clear_session():
    if TOKEN_PATH.exists():
        TOKEN_PATH.unlink()

# ══════════════════════════════════════════════════════════════════════════════
# SUPABASE CLIENT
# ══════════════════════════════════════════════════════════════════════════════
class SupabaseClient:
    def __init__(self, url: str, anon_key: str):
        self.url  = url.rstrip("/")
        self.key  = anon_key
        self._h   = {
            "apikey":        anon_key,
            "Authorization": f"Bearer {anon_key}",
            "Content-Type":  "application/json",
            "Prefer":        "return=representation",
        }

    def _u(self, table): return f"{self.url}/rest/v1/{table}"

    def select(self, table, filters="", order="", limit=0, offset=0):
        params = []
        if filters: params.append(filters)
        if order:   params.append(f"order={order}")
        if limit:   params.append(f"limit={limit}")
        if offset:  params.append(f"offset={offset}")
        qs  = "&".join(params)
        url = self._u(table) + (f"?{qs}" if qs else "")
        r   = requests.get(url, headers=self._h, timeout=12)
        r.raise_for_status()
        return r.json()

    def insert(self, table, data):
        r = requests.post(self._u(table), headers=self._h, json=data, timeout=12)
        r.raise_for_status()
        res = r.json()
        return res[0] if isinstance(res, list) else res

    def upsert(self, table, data):
        h = {**self._h, "Prefer": "resolution=merge-duplicates,return=representation"}
        r = requests.post(self._u(table), headers=h, json=data, timeout=12)
        r.raise_for_status()
        return r.json()

    def update(self, table, filters, data):
        r = requests.patch(self._u(table) + f"?{filters}", headers=self._h, json=data, timeout=12)
        r.raise_for_status()
        return r.json()

    def delete(self, table, filters):
        r = requests.delete(self._u(table) + f"?{filters}", headers=self._h, timeout=12)
        r.raise_for_status()

    def count(self, table, filters=""):
        h   = {**self._h, "Prefer": "count=exact", "Range-Unit": "items", "Range": "0-0"}
        url = self._u(table) + (f"?{filters}" if filters else "")
        r   = requests.head(url, headers=h, timeout=10)
        try:
            return int(r.headers.get("Content-Range","0/0").split("/")[1])
        except Exception:
            return 0

_sb: SupabaseClient | None = None
_cfg_ref: configparser.ConfigParser | None = None

def get_sb():
    return _sb

def set_cfg_ref(cfg: configparser.ConfigParser):
    global _sb, _cfg_ref
    _cfg_ref = cfg
    # Supabase берём из кода (fallback на config для совместимости)
    url = (_LocalSecrets.SUPABASE_URL or "").strip() or cfg.get("supabase", "url", fallback="").strip()
    key = (_LocalSecrets.SUPABASE_ANON_KEY or "").strip() or cfg.get("supabase", "anon_key", fallback="").strip()
    if url and key and url.startswith("http") and len(key) > 20:
        _sb = SupabaseClient(url, key)
        log.info("Supabase OK: %s", url)
    else:
        _sb = None
        log.info("Supabase не настроен — SQLite fallback")

def is_cloud():
    return _sb is not None

# ══════════════════════════════════════════════════════════════════════════════
# LOCAL SQLITE
# ══════════════════════════════════════════════════════════════════════════════
_SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS Admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL, full_name TEXT DEFAULT '', role TEXT DEFAULT 'admin',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS Employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT, full_name TEXT NOT NULL,
    department TEXT NOT NULL, position TEXT NOT NULL, hire_date TEXT NOT NULL,
    salary REAL DEFAULT 0, active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS Resources (
    id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, category TEXT NOT NULL,
    unit TEXT NOT NULL, quantity REAL DEFAULT 0, min_quantity REAL DEFAULT 10,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS KPI_Logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id INTEGER NOT NULL,
    period TEXT NOT NULL, score REAL NOT NULL, tasks_done INTEGER DEFAULT 0,
    comment TEXT DEFAULT '', logged_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES Employees(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS Notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, message TEXT NOT NULL,
    read INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
"""

def init_db():
    first = not DB_PATH.exists()
    conn  = sqlite3.connect(DB_PATH)
    conn.executescript(_SCHEMA)
    conn.commit()
    if first:
        _seed_admins(conn)
        _seed_employees(conn)
        _seed_resources(conn)
        _seed_kpi(conn)
        conn.commit()
        log.info("Локальная БД инициализирована и засеяна.")
    conn.close()

def get_conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c

# ── Seed ───────────────────────────────────────────────────────────────────────
_LM = ["Иванов","Смирнов","Кузнецов","Попов","Васильев","Петров","Соколов","Михайлов","Новиков","Фёдоров"]
_FM = ["Александр","Дмитрий","Максим","Сергей","Андрей","Алексей","Артём","Илья","Кирилл","Михаил"]
_PM = ["Александрович","Дмитриевич","Сергеевич","Андреевич","Алексеевич","Михайлович","Павлович"]
_LF = ["Иванова","Смирнова","Кузнецова","Попова","Васильева","Петрова","Соколова","Михайлова"]
_FF = ["Анна","Мария","Елена","Ольга","Наталья","Татьяна","Ирина","Светлана"]
_PF = ["Александровна","Дмитриевна","Сергеевна","Андреевна","Алексеевна","Михайловна"]
_DEPTS = {
    "АХД":              ["Начальник АХД","Зам. начальника","Специалист по снабжению","Делопроизводитель","Бухгалтер","Кассир","Сис. администратор"],
    "Транспортный цех": ["Начальник цеха","Диспетчер","Водитель","Механик","Слесарь"],
    "Мастерская":       ["Начальник мастерской","Мастер участка","Токарь","Сварщик","Электрик","Слесарь","Грузчик"],
}

def _rname():
    if random.random() > .35:
        return f"{random.choice(_LM)} {random.choice(_FM)} {random.choice(_PM)}"
    return f"{random.choice(_LF)} {random.choice(_FF)} {random.choice(_PF)}"

def _seed_admins(c):
    h = bcrypt.hashpw(b"admin", bcrypt.gensalt()).decode()
    c.execute("INSERT OR IGNORE INTO Admins (username,password,full_name,role) VALUES (?,?,?,?)",
              ("admin", h, "Главный Арбитр", "superadmin"))

def _seed_employees(c):
    rows = []
    for _ in range(110):
        d = random.choice(list(_DEPTS))
        p = random.choice(_DEPTS[d])
        h = (datetime.now() - timedelta(days=random.randint(30, 3650))).strftime("%Y-%m-%d")
        rows.append((_rname(), d, p, h, round(random.uniform(28000, 95000), 2), 1))
    c.executemany("INSERT INTO Employees (full_name,department,position,hire_date,salary,active) VALUES (?,?,?,?,?,?)", rows)

_RES = [
    ("Дизельное топливо","Топливо","л",1200,200),("Бензин АИ-92","Топливо","л",800,150),
    ("Бензин АИ-95","Топливо","л",400,100),("Моторное масло 5W-30","Масла","л",60,15),
    ("Тормозная жидкость","Масла","л",12,5),("Антифриз","Масла","л",35,10),
    ("Фильтр масляный","Запчасти","шт",18,5),("Фильтр воздушный","Запчасти","шт",10,3),
    ("Тормозные колодки","Запчасти","компл",6,2),("Аккумулятор 60Ач","Запчасти","шт",4,2),
    ("Шины R16","Запчасти","шт",12,4),("Бумага А4","Канцтовары","пач",25,5),
    ("Ручки шариковые","Канцтовары","уп",10,3),("Картриджи принтера","Канцтовары","шт",5,2),
    ("Защитные перчатки","Спецодежда","пар",45,10),("Каски защитные","Спецодежда","шт",20,5),
    ("Спецовки рабочие","Спецодежда","шт",15,5),("Сварочные электроды","Расходники","уп",12,3),
    ("Папки-регистраторы","Канцтовары","шт",18,5),("Свечи зажигания","Запчасти","компл",8,3),
]

def _seed_resources(c):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.executemany("INSERT INTO Resources (name,category,unit,quantity,min_quantity,updated_at) VALUES (?,?,?,?,?,?)",
                  [(n, cat, u, q, m, now) for n, cat, u, q, m in _RES])

def _seed_kpi(c):
    ids  = [r[0] for r in c.execute("SELECT id FROM Employees").fetchall()]
    now  = datetime.now()
    cmts = ["Отличный результат", "Норма выполнена", "Небольшие задержки", ""]
    rows = []
    for off in range(6):
        period = (now - timedelta(days=30 * off)).strftime("%Y-%m")
        for eid in ids:
            rows.append((eid, period, round(random.uniform(55, 100), 1), random.randint(5, 45), random.choice(cmts)))
    c.executemany("INSERT INTO KPI_Logs (employee_id,period,score,tasks_done,comment) VALUES (?,?,?,?,?)", rows)

# ══════════════════════════════════════════════════════════════════════════════
# SEED SUPABASE — импорт локальных данных в облако
# ══════════════════════════════════════════════════════════════════════════════
def seed_supabase_from_local():
    """
    Импортировать всё из локальной SQLite в Supabase.
    Защита от дублей: сначала проверяем count() — если таблица уже заполнена,
    пропускаем её. Admins всегда upsert по username (безопасно повторять).
    """
    if not is_cloud() or not DB_PATH.exists():
        return False, "Supabase не настроен или локальная БД не найдена."
    try:
        conn     = get_conn()
        imported = {}
        skipped  = {}

        # ── Admins (upsert — всегда безопасно) ────────────────────────────────
        rows = [dict(r) for r in conn.execute("SELECT * FROM Admins").fetchall()]
        ok = 0
        for r in rows:
            try:
                _sb.upsert("Admins", {"username": r["username"],
                    "password": r["password"],
                    "full_name": r["full_name"], "role": r["role"]})
                ok += 1
            except Exception: pass
        imported["Admins"] = ok

        # ── Employees ──────────────────────────────────────────────────────────
        cloud_emp = _sb.count("Employees")
        rows = [dict(r) for r in conn.execute("SELECT * FROM Employees").fetchall()]
        if cloud_emp >= len(rows):
            skipped["Employees"] = cloud_emp
        else:
            ok = 0
            for r in rows:
                try:
                    _sb.insert("Employees", {
                        "full_name": r["full_name"], "department": r["department"],
                        "position": r["position"],  "hire_date":  r["hire_date"],
                        "salary":   r["salary"],     "active":     bool(r["active"])})
                    ok += 1
                except Exception: pass
            imported["Employees"] = ok

        # ── Resources ──────────────────────────────────────────────────────────
        cloud_res = _sb.count("Resources")
        rows = [dict(r) for r in conn.execute("SELECT * FROM Resources").fetchall()]
        if cloud_res >= len(rows):
            skipped["Resources"] = cloud_res
        else:
            ok = 0
            for r in rows:
                try:
                    _sb.insert("Resources", {
                        "name": r["name"], "category": r["category"],
                        "unit": r["unit"], "quantity": r["quantity"],
                        "min_quantity": r["min_quantity"]})
                    ok += 1
                except Exception: pass
            imported["Resources"] = ok

        # ── KPI_Logs ───────────────────────────────────────────────────────────
        cloud_kpi = _sb.count("KPI_Logs")
        rows = [dict(r) for r in conn.execute("SELECT * FROM KPI_Logs").fetchall()]
        if cloud_kpi > 0 and cloud_kpi >= len(rows):
            skipped["KPI_Logs"] = cloud_kpi
        else:
            # Строим карту: локальный employee_id → full_name
            local_emps = {r["id"]: r["full_name"] for r in
                          [dict(x) for x in conn.execute(
                              "SELECT id, full_name FROM Employees").fetchall()]}
            # Строим карту: full_name → облачный id
            cloud_emps  = _sb.select("Employees", "select=id,full_name", limit=9999)
            name_to_cid = {}
            for e in cloud_emps:
                name_to_cid[e["full_name"]] = e["id"]
            ok = 0; skip_no_emp = 0
            for r in rows:
                fname = local_emps.get(r["employee_id"])
                cid   = name_to_cid.get(fname) if fname else None
                if not cid:
                    skip_no_emp += 1
                    continue
                try:
                    _sb.insert("KPI_Logs", {
                        "employee_id": cid,   "period":     r["period"],
                        "score":       r["score"], "tasks_done": r["tasks_done"],
                        "comment":     r["comment"] or ""})
                    ok += 1
                except Exception:
                    pass
            imported["KPI_Logs"] = ok
            if skip_no_emp:
                skipped["KPI без сотрудника"] = skip_no_emp

        conn.close()
        parts = []
        if imported: parts.append("Импортировано: " + ", ".join(f"{k}: {v}" for k,v in imported.items()))
        if skipped:  parts.append("Пропущено (уже есть): " + ", ".join(f"{k}: {v}" for k,v in skipped.items()))
        return True, "  |  ".join(parts) or "Нет данных для импорта"
    except Exception as e:
        return False, str(e)

# ══════════════════════════════════════════════════════════════════════════════
# AUTH
# ══════════════════════════════════════════════════════════════════════════════
def verify_login(username: str, password: str) -> bool:
    try:
        if is_cloud():
            rows = _sb.select("Admins", f"username=eq.{username}&select=password")
            if not rows:
                return False
            return bcrypt.checkpw(password.encode(), rows[0]["password"].encode())
        else:
            c   = get_conn()
            row = c.execute("SELECT password FROM Admins WHERE username=?", (username,)).fetchone()
            c.close()
            return row and bcrypt.checkpw(password.encode(), row["password"].encode())
    except Exception as e:
        log.error("verify_login: %s", e)
        return False

def get_admin(username: str):
    try:
        if is_cloud():
            rows = _sb.select("Admins", f"username=eq.{username}")
            return rows[0] if rows else None
        else:
            c   = get_conn()
            row = c.execute("SELECT * FROM Admins WHERE username=?", (username,)).fetchone()
            c.close()
            return dict(row) if row else None
    except Exception:
        return None

def get_all_admins():
    try:
        if is_cloud():
            return _sb.select("Admins", "select=id,username,full_name,role,created_at", "id.asc")
        else:
            c    = get_conn()
            rows = c.execute("SELECT id,username,full_name,role,created_at FROM Admins ORDER BY id").fetchall()
            c.close()
            return [dict(r) for r in rows]
    except Exception:
        return []

def add_admin(username, password, full_name, role="admin"):
    h = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    if is_cloud():
        _sb.insert("Admins", {"username": username, "password": h, "full_name": full_name, "role": role})
    else:
        c = get_conn()
        c.execute("INSERT INTO Admins (username,password,full_name,role) VALUES (?,?,?,?)", (username, h, full_name, role))
        c.commit(); c.close()

def delete_admin(admin_id):
    if is_cloud():
        _sb.delete("Admins", f"id=eq.{admin_id}&role=neq.superadmin")
    else:
        c = get_conn()
        c.execute("DELETE FROM Admins WHERE id=? AND role!='superadmin'", (admin_id,))
        c.commit(); c.close()

def change_password(username, new_pw):
    h = bcrypt.hashpw(new_pw.encode(), bcrypt.gensalt()).decode()
    if is_cloud():
        _sb.update("Admins", f"username=eq.{username}", {"password": h})
    else:
        c = get_conn()
        c.execute("UPDATE Admins SET password=? WHERE username=?", (h, username))
        c.commit(); c.close()

# ══════════════════════════════════════════════════════════════════════════════
# EMPLOYEES
# ══════════════════════════════════════════════════════════════════════════════
def get_employees_page(search="", limit=50, offset=0):
    try:
        if is_cloud():
            q = f"or=(full_name.ilike.*{search}*,department.ilike.*{search}*,position.ilike.*{search}*)" if search else ""
            return _sb.select("Employees", q, "department.asc,full_name.asc", limit, offset)
        else:
            c   = get_conn(); sq = f"%{search}%"
            sql = "SELECT * FROM Employees WHERE full_name LIKE ? OR department LIKE ? OR position LIKE ? ORDER BY department,full_name LIMIT ? OFFSET ?"
            rows = c.execute(sql, (sq, sq, sq, limit, offset)).fetchall(); c.close()
            return [dict(r) for r in rows]
    except Exception as e:
        log.error("get_employees_page: %s", e); return []

def count_employees(search=""):
    try:
        if is_cloud():
            q = f"or=(full_name.ilike.*{search}*,department.ilike.*{search}*)" if search else ""
            return _sb.count("Employees", q)
        else:
            c  = get_conn(); sq = f"%{search}%"
            n  = c.execute("SELECT COUNT(*) FROM Employees WHERE full_name LIKE ? OR department LIKE ? OR position LIKE ?", (sq, sq, sq)).fetchone()[0]
            c.close(); return n
    except Exception:
        return 0

def get_all_employees(search="", limit=0, offset=0):
    return get_employees_page(search, limit or 9999, offset)

def add_employee(full_name, department, position, hire_date, salary):
    if is_cloud():
        _sb.insert("Employees", {"full_name": full_name, "department": department,
                                  "position": position, "hire_date": hire_date,
                                  "salary": salary, "active": True})
    else:
        c = get_conn()
        c.execute("INSERT INTO Employees (full_name,department,position,hire_date,salary) VALUES (?,?,?,?,?)",
                  (full_name, department, position, hire_date, salary))
        c.commit(); c.close()
    add_notification("staff", f"Добавлен сотрудник: {full_name} ({department})")
    _tg_notify_async(f"👤 *Новый сотрудник*\n\nФИО: {full_name}\nОтдел: {department}\nДолжность: {position}\nДата найма: {hire_date}\nЗарплата: {salary:,.0f} ₽")

def update_employee(eid, full_name, department, position, hire_date, salary, active):
    if is_cloud():
        _sb.update("Employees", f"id=eq.{eid}",
                   {"full_name": full_name, "department": department, "position": position,
                    "hire_date": hire_date, "salary": salary, "active": bool(active)})
    else:
        c = get_conn()
        c.execute("UPDATE Employees SET full_name=?,department=?,position=?,hire_date=?,salary=?,active=? WHERE id=?",
                  (full_name, department, position, hire_date, salary, active, eid))
        c.commit(); c.close()

def delete_employee(eid):
    if is_cloud():
        _sb.delete("KPI_Logs", f"employee_id=eq.{eid}")
        _sb.delete("Employees", f"id=eq.{eid}")
    else:
        c = get_conn()
        c.execute("DELETE FROM Employees WHERE id=?", (eid,))
        c.commit(); c.close()

# ══════════════════════════════════════════════════════════════════════════════
# RESOURCES
# ══════════════════════════════════════════════════════════════════════════════
def get_all_resources(search=""):
    try:
        if is_cloud():
            q = f"or=(name.ilike.*{search}*,category.ilike.*{search}*)" if search else ""
            return _sb.select("Resources", q, "category.asc,name.asc")
        else:
            c   = get_conn(); sq = f"%{search}%"
            rows = c.execute("SELECT * FROM Resources WHERE name LIKE ? OR category LIKE ? ORDER BY category,name", (sq, sq)).fetchall()
            c.close(); return [dict(r) for r in rows]
    except Exception as e:
        log.error("get_resources: %s", e); return []

def get_low_resources():
    try:
        if is_cloud():
            return _sb.select("Resources", "quantity=lte.min_quantity", "quantity.asc")
        else:
            c    = get_conn()
            rows = c.execute("SELECT * FROM Resources WHERE quantity<=min_quantity ORDER BY quantity").fetchall()
            c.close(); return [dict(r) for r in rows]
    except Exception:
        return []

def add_resource(name, category, unit, quantity, min_quantity):
    if is_cloud():
        _sb.insert("Resources", {"name": name, "category": category, "unit": unit,
                                  "quantity": quantity, "min_quantity": min_quantity,
                                  "updated_at": datetime.now().isoformat()})
    else:
        c = get_conn()
        c.execute("INSERT INTO Resources (name,category,unit,quantity,min_quantity,updated_at) VALUES (?,?,?,?,?,?)",
                  (name, category, unit, quantity, min_quantity, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        c.commit(); c.close()
    if quantity <= min_quantity:
        _tg_notify_async(f"⚠️ *Низкий запас после добавления*\n\n{name}: {quantity} {unit}\nМинимум: {min_quantity} {unit}")

def update_resource(rid, name, category, unit, quantity, min_quantity):
    if is_cloud():
        _sb.update("Resources", f"id=eq.{rid}",
                   {"name": name, "category": category, "unit": unit,
                    "quantity": quantity, "min_quantity": min_quantity,
                    "updated_at": datetime.now().isoformat()})
    else:
        c = get_conn()
        c.execute("UPDATE Resources SET name=?,category=?,unit=?,quantity=?,min_quantity=?,updated_at=? WHERE id=?",
                  (name, category, unit, quantity, min_quantity, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), rid))
        c.commit(); c.close()
    if quantity <= min_quantity:
        _tg_notify_async(f"⚠️ *Запас ниже минимума*\n\n{name}: {quantity} {unit}\nМинимум: {min_quantity} {unit}\nКатегория: {category}")

def delete_resource(rid):
    if is_cloud():
        _sb.delete("Resources", f"id=eq.{rid}")
    else:
        c = get_conn()
        c.execute("DELETE FROM Resources WHERE id=?", (rid,))
        c.commit(); c.close()

# ══════════════════════════════════════════════════════════════════════════════
# KPI
# ══════════════════════════════════════════════════════════════════════════════
def get_kpi_summary(period=None):
    try:
        if is_cloud():
            q    = (f"period=eq.{period}&" if period else "") + "select=period,score,tasks_done,employee_id,Employees(full_name,department)"
            rows = _sb.select("KPI_Logs", q, "period.desc,score.desc")
            from collections import defaultdict
            grp  = defaultdict(list)
            for r in rows:
                emp = r.get("Employees") or {}
                key = (emp.get("full_name",""), emp.get("department",""), r["period"])
                grp[key].append(r)
            out = []
            for (fn, dept, per), recs in grp.items():
                out.append({"full_name": fn, "department": dept, "period": per,
                            "avg_score": round(sum(r["score"] for r in recs)/len(recs), 1),
                            "total_tasks": sum(r["tasks_done"] for r in recs)})
            return sorted(out, key=lambda x: (x["period"], x["avg_score"]), reverse=True)
        else:
            c    = get_conn()
            sql  = "SELECT e.full_name,e.department,k.period,ROUND(AVG(k.score),1) as avg_score,SUM(k.tasks_done) as total_tasks FROM KPI_Logs k JOIN Employees e ON k.employee_id=e.id {w} GROUP BY e.id,k.period ORDER BY k.period DESC,avg_score DESC"
            rows = c.execute(sql.format(w="WHERE k.period=?" if period else ""), ((period,) if period else ())).fetchall()
            c.close(); return [dict(r) for r in rows]
    except Exception as e:
        log.error("get_kpi: %s", e); return []

def get_dept_avg_kpi():
    try:
        if is_cloud():
            rows = _sb.select("KPI_Logs", "select=score,employee_id,Employees(department)")
            from collections import defaultdict
            grp  = defaultdict(list)
            for r in rows:
                dept = (r.get("Employees") or {}).get("department", "")
                if dept: grp[dept].append(r["score"])
            return {d: round(sum(v)/len(v), 1) for d, v in grp.items()}
        else:
            c    = get_conn()
            rows = c.execute("SELECT e.department,ROUND(AVG(k.score),1) as avg_score FROM KPI_Logs k JOIN Employees e ON k.employee_id=e.id WHERE k.period=(SELECT MAX(period) FROM KPI_Logs) GROUP BY e.department").fetchall()
            c.close(); return {r["department"]: r["avg_score"] for r in rows}
    except Exception:
        return {}

def get_kpi_trend(months=6):
    try:
        if is_cloud():
            rows = _sb.select("KPI_Logs", "select=period,score")
            from collections import defaultdict
            grp  = defaultdict(list)
            for r in rows: grp[r["period"]].append(r["score"])
            items = sorted(grp.items())[-months:]
            return {"periods": [x[0] for x in items],
                    "scores":  [round(sum(v)/len(v), 1) for _, v in items]}
        else:
            c    = get_conn()
            rows = c.execute("SELECT period,ROUND(AVG(score),1) as avg FROM KPI_Logs GROUP BY period ORDER BY period DESC LIMIT ?", (months,)).fetchall()
            c.close()
            items = sorted(rows, key=lambda r: r["period"])
            return {"periods": [r["period"] for r in items], "scores": [r["avg"] for r in items]}
    except Exception:
        return {"periods": [], "scores": []}

def get_top_employees(n=10):
    try:
        if is_cloud():
            rows = _sb.select("KPI_Logs", "select=score,employee_id,Employees(full_name,department)")
            from collections import defaultdict
            grp  = defaultdict(list); meta = {}
            for r in rows:
                eid  = r["employee_id"]; emp = r.get("Employees") or {}
                meta[eid] = emp; grp[eid].append(r["score"])
            scored = sorted([(eid, round(sum(v)/len(v), 1)) for eid, v in grp.items()], key=lambda x: x[1], reverse=True)
            return [{"full_name": meta[eid].get("full_name",""), "department": meta[eid].get("department",""), "avg_score": sc} for eid, sc in scored[:n]]
        else:
            c    = get_conn()
            rows = c.execute("SELECT e.full_name,e.department,ROUND(AVG(k.score),1) as avg_score FROM KPI_Logs k JOIN Employees e ON k.employee_id=e.id WHERE k.period=(SELECT MAX(period) FROM KPI_Logs) GROUP BY e.id ORDER BY avg_score DESC LIMIT ?", (n,)).fetchall()
            c.close(); return [dict(r) for r in rows]
    except Exception:
        return []

def add_kpi_log(emp_id, period, score, tasks_done, comment="", emp_name=""):
    if is_cloud():
        _sb.insert("KPI_Logs", {"employee_id": emp_id, "period": period,
                                 "score": score, "tasks_done": tasks_done, "comment": comment})
    else:
        c = get_conn()
        c.execute("INSERT INTO KPI_Logs (employee_id,period,score,tasks_done,comment) VALUES (?,?,?,?,?)",
                  (emp_id, period, score, tasks_done, comment))
        c.commit(); c.close()
    if score < int(_cfg_ref.get("nautica","kpi_red_zone",fallback="40") if _cfg_ref else "40"):
        add_notification("kpi", f"Критический KPI: {score:.1f} — {emp_name or f'ID:{emp_id}'} ({period})")
        _tg_notify_async(
            f"🔴 *Критический KPI!*\n\n"
            f"Сотрудник: {emp_name or f'ID:{emp_id}'}\n"
            f"Период: {period}\n"
            f"KPI: *{score:.1f}* баллов\n"
            f"Задач выполнено: {tasks_done}\n"
            f"{'Комментарий: ' + comment if comment else ''}\n\n"
            f"⚠️ Требуется внимание руководителя.")

def purge_old_logs(months=12):
    cutoff = (datetime.now() - timedelta(days=30*months)).strftime("%Y-%m")
    if is_cloud():
        _sb.delete("KPI_Logs", f"period=lt.{cutoff}")
    else:
        c = get_conn()
        c.execute("DELETE FROM KPI_Logs WHERE period < ?", (cutoff,))
        c.commit(); c.close()

# ══════════════════════════════════════════════════════════════════════════════
# NOTIFICATIONS
# ══════════════════════════════════════════════════════════════════════════════
def add_notification(kind, message):
    try:
        if is_cloud():
            _sb.insert("Notifications", {"kind": kind, "message": message, "read": False})
        else:
            c = get_conn()
            c.execute("INSERT INTO Notifications (kind,message) VALUES (?,?)", (kind, message))
            c.commit(); c.close()
    except Exception as e:
        log.error("add_notification: %s", e)

def get_unread_notifications():
    try:
        if is_cloud():
            return _sb.select("Notifications", "read=eq.false", "created_at.desc", 50)
        else:
            c    = get_conn()
            rows = c.execute("SELECT * FROM Notifications WHERE read=0 ORDER BY created_at DESC LIMIT 50").fetchall()
            c.close(); return [dict(r) for r in rows]
    except Exception:
        return []

def mark_notifications_read():
    try:
        if is_cloud():
            _sb.update("Notifications", "read=eq.false", {"read": True})
        else:
            c = get_conn()
            c.execute("UPDATE Notifications SET read=1")
            c.commit(); c.close()
    except Exception:
        pass

def get_notification_count():
    try:
        if is_cloud():
            return _sb.count("Notifications", "read=eq.false")
        else:
            c = get_conn()
            n = c.execute("SELECT COUNT(*) FROM Notifications WHERE read=0").fetchone()[0]
            c.close(); return n
    except Exception:
        return 0

# ══════════════════════════════════════════════════════════════════════════════
# TELEGRAM
# ══════════════════════════════════════════════════════════════════════════════
def send_telegram(cfg, message: str) -> bool:
    # Telegram берём из кода (fallback на config для совместимости)
    token = (_LocalSecrets.TG_BOT_TOKEN or "").strip() or cfg.get("telegram", "bot_token", fallback="").strip()
    chat  = (_LocalSecrets.TG_CHAT_ID or "").strip() or cfg.get("telegram", "chat_id",   fallback="").strip()
    if not token or not chat or len(token) < 10:
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat, "text": message, "parse_mode": "Markdown"},
            timeout=10)
        return r.status_code == 200
    except Exception as e:
        log.error("TG: %s", e); return False

def _tg_notify_async(message: str):
    """Отправить TG-уведомление в фоновом потоке."""
    if _cfg_ref is None: return
    cfg = _cfg_ref
    threading.Thread(target=send_telegram, args=(cfg, message), daemon=True).start()

# ══════════════════════════════════════════════════════════════════════════════
# GITHUB BACKUP (только для SQLite-режима)
# ══════════════════════════════════════════════════════════════════════════════
def _parse_repo(url):
    parts = url.rstrip("/").split("/")
    return parts[-2], parts[-1].replace(".git", "")

def github_push_backup(cfg, message="backup"):
    if is_cloud() or not DB_PATH.exists(): return False
    token = cfg.get("github", "token",    fallback="").strip()
    repo  = cfg.get("github", "repo_url", fallback="").strip()
    if not token or not repo: return False
    try:
        owner, rname = _parse_repo(repo)
        api  = f"https://api.github.com/repos/{owner}/{rname}/contents/zvezda-kpi.db"
        hdrs = {"Authorization": f"token {token}", "Content-Type": "application/json"}
        sha  = None
        gr   = requests.get(api, headers={"Authorization": f"token {token}"}, timeout=10)
        if gr.status_code == 200: sha = gr.json().get("sha")
        payload = {"message": message, "content": base64.b64encode(DB_PATH.read_bytes()).decode()}
        if sha: payload["sha"] = sha
        r = requests.put(api, headers=hdrs, json=payload, timeout=30)
        return r.status_code in (200, 201)
    except Exception as e:
        log.error("github_push: %s", e); return False
