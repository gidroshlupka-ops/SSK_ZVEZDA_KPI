# ⭐ SSK ZVEZDA — KPI Monitor
### "The First Whistle" | GitHub Cloud Edition

---

## Архитектура модулей

| Модуль | Файл | Назначение |
|--------|------|------------|
| `izolde` | `modules/izolde.py` | UI на CustomTkinter (все вкладки, диалоги) |
| `rubuska` | `modules/rubuska.py` | БД SQLite, сессии, CRUD, GitHub sync |
| `nautica` | `modules/nautica.py` | Генерация .docx отчётов с графиками |
| `umamusume` | `modules/umamusume.py` | Фоновый движок, Telegram, системный трей |
| `The_Storm` | `The_Storm.py` | Главный запускатель |

---

## Быстрый старт

### 1. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 2. Настройка config.ini
```ini
[github]
token = ghp_ВАШ_ТОКЕН_ЗДЕСЬ
repo_url = https://github.com/ВАШ_ЛОГИН/ВАШ_ПРИВАТНЫЙ_РЕПО

[telegram]
bot_token = 123456:ABC-DEF...
chat_id = -1001234567890

[app]
remember_me = false
hardware_bind = false
```

> **Важно:** Токен GitHub должен иметь права `repo` (полный доступ к приватным репозиториям).

### 3. Запуск
```bash
python The_Storm.py
```

**Первый вход:** логин `admin` / пароль `admin`

---

## Структура базы данных

### Таблица `Employees`
| Поле | Тип | Описание |
|------|-----|----------|
| id | INTEGER | Первичный ключ |
| full_name | TEXT | ФИО (рус.) |
| department | TEXT | АХД / Транспортный цех / Мастерская |
| position | TEXT | Должность |
| hire_date | TEXT | Дата найма |
| salary | REAL | Зарплата |
| active | INTEGER | 1=активен, 0=уволен |

### Таблица `Resources`
| Поле | Тип | Описание |
|------|-----|----------|
| id | INTEGER | Первичный ключ |
| name | TEXT | Наименование |
| category | TEXT | Категория |
| unit | TEXT | Единица измерения |
| quantity | REAL | Текущий остаток |
| min_quantity | REAL | Минимальный порог |

### Таблица `KPI_Logs`
| Поле | Тип | Описание |
|------|-----|----------|
| employee_id | INTEGER | FK на Employees |
| period | TEXT | Период (YYYY-MM) |
| score | REAL | Балл KPI (0-100) |
| tasks_done | INTEGER | Задач выполнено |

---

## GitHub "Вечная База"

**Стратегия синхронизации:**
- **При запуске** → `rubuska.github_pull()` скачивает последнюю БД через GitHub API
- **При закрытии** → `rubuska.github_push()` загружает обновлённую БД в репозиторий
- **Вручную** → вкладка ⚙ Настройки → кнопки «Скачать/Загрузить БД»

**Создание приватного репозитория:**
1. Зайди на github.com → New repository
2. Сделай его приватным (Private)
3. Создай Personal Access Token: Settings → Developer settings → Tokens (classic) → `repo` scope
4. Вставь токен и URL репо в `config.ini` или вкладку Настройки

---

## Telegram Sentinel

**Настройка:**
1. Создай бота через @BotFather → получи Bot Token
2. Добавь бота в группу/канал
3. Получи Chat ID (можно через @userinfobot или API)
4. Заполни поля в Настройках

**Когда срабатывает:**
- Фоновый воркер проверяет склад каждые 60 минут
- Кнопка «⚠ Проверить запасы» на вкладке Ресурсы
- При любом ресурсе ≤ минимального порога

---

## Сборка в .exe (PyInstaller)

```bash
# Установить PyInstaller
pip install pyinstaller

# Сборка одним файлом
pyinstaller build_pyinstaller.spec

# Результат: dist/SSK_Zvezda_KPI.exe
```

**Требования для иконки:** положи `izolde.ico` в папку `assets/`

---

## Функционал вкладок

### 👥 Сотрудники
- Полная таблица со всеми сотрудниками (110+ записей после сидинга)
- Поиск по ФИО, отделу, должности
- CRUD: добавление, редактирование, удаление (с каскадом KPI)
- Отметка активности (уволенные отображаются серым)

### 📦 Ресурсы
- 20 типов ресурсов (топливо, масла, запчасти, канцтовары, спецодежда)
- Подсветка красным при критическом уровне запасов
- Отправка Telegram-алерта по кнопке или автоматически

### 📊 KPI
- Live-диаграмма KPI по подразделениям (с цветовой градацией)
- Таблица последних записей
- Добавление новых KPI-оценок

### 📄 Отчёты (Nautica)
- Генерация Word (.docx) по выбранному периоду
- Включает: AI-резюме, 3 графика matplotlib, топ-15, таблицу ресурсов
- Файл сохраняется рядом с exe

### ⚙ Настройки (Tuning)
- GitHub Token + Repo URL
- Telegram Bot + Chat ID
- Привязка сессии к Hardware ID
- Смена пароля администратора
- Ручная синхронизация БД

---

## Первый запуск — что происходит

1. `rubuska.init_db()` создаёт `zvezda-kpi.db`
2. Автоматический сидинг: 110 сотрудников + 20 ресурсов + 660+ KPI-записей за 6 месяцев
3. Создаётся admin: логин `admin` / пароль `admin` (хэш bcrypt)
4. Попытка скачать БД из GitHub (если настроен)
5. Если нет токена сессии — показывается LoginWindow

---

## Безопасность

- Пароли хранятся только как **bcrypt-хэш** (соль встроена)
- Токен сессии хранится **зашифрованным** (Fernet/AES-128)
- Опциональная привязка к **MAC-адресу** компьютера
- GitHub токен и TG токен читаются из `config.ini` — **никогда не хардкодятся**

---

*SSK Zvezda KPI Monitor v1.0 | Python 3.11+ | CustomTkinter 5.x*
