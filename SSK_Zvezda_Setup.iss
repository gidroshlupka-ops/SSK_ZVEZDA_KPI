; SSK_Zvezda_Setup.iss
; Скрипт Inno Setup для сборки установщика ССК Звезда KPI Monitor v5
; Как использовать:
;   1. Установи Inno Setup: https://jrsoftware.org/isinfo.php
;   2. Сначала запусти build_exe_v5.bat — получишь dist\SSK_Zvezda_KPI.exe
;   3. Открой этот файл в Inno Setup Compiler
;   4. Нажми Build → Compile (или F9)
;   5. Готовый установщик: Output\SSK_Zvezda_KPI_Setup_v5.exe

[Setup]
; Основные сведения о приложении
AppName=ССК Звезда — KPI Monitor
AppVersion=5.0
AppPublisher=ССК «Звезда»
AppPublisherURL=https://supabase.com
AppSupportURL=
AppUpdatesURL=

; Имя файла установщика
OutputBaseFilename=SSK_Zvezda_KPI_Setup_v5
OutputDir=Output

; Папка по умолчанию — Program Files\SSK_Zvezda_KPI
DefaultDirName={autopf}\SSK_Zvezda_KPI
DefaultGroupName=ССК Звезда
AllowNoIcons=yes

; Иконка установщика
SetupIconFile=assets\izolde.ico

; Минимальная версия Windows (7+)
MinVersion=6.1

; Сжатие
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern

; Лицензия — покажется пользователю
LicenseFile=LICENSE.txt

; Нужны права администратора?
; "lowest"  — устанавливает только для текущего пользователя (не нужны права)
; "admin"   — устанавливает для всех (нужны права администратора)
PrivilegesRequiredOverridesAllowed=dialog
PrivilegesRequired=lowest

; Описание для Панели управления
UninstallDisplayIcon={app}\SSK_Zvezda_KPI.exe
UninstallDisplayName=ССК Звезда — KPI Monitor v5

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
; Галочки при установке
Name: "desktopicon";    Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительные значки:"; Flags: checked
Name: "startmenuicon";  Description: "Добавить в меню Пуск";           GroupDescription: "Дополнительные значки:"; Flags: checked

[Files]
; Основной exe
Source: "dist\SSK_Zvezda_KPI.exe"; DestDir: "{app}"; Flags: ignoreversion

; Ресурсы (иконка, аватар Murka)
Source: "assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs

; Конфиг (только если ещё не существует у пользователя)
Source: "config_default.ini"; DestDir: "{app}"; DestName: "config.ini"; \
  Flags: ignoreversion onlyifdoesntexist

; SQL-схема для Supabase (справочный файл)
Source: "supabase_schema.sql"; DestDir: "{app}"; Flags: ignoreversion

; README
Source: "README.txt"; DestDir: "{app}"; Flags: ignoreversion isreadme

[Icons]
; Ярлык в меню Пуск
Name: "{group}\ССК Звезда KPI Monitor"; Filename: "{app}\SSK_Zvezda_KPI.exe"; \
  IconFilename: "{app}\assets\izolde.ico"
Name: "{group}\Удалить ССК Звезда"; Filename: "{uninstallexe}"

; Ярлык на рабочем столе — только если отметил галочку
Name: "{autodesktop}\ССК Звезда KPI Monitor"; \
  Filename: "{app}\SSK_Zvezda_KPI.exe"; \
  IconFilename: "{app}\assets\izolde.ico"; \
  Tasks: desktopicon

[Run]
; После установки — предложить запустить приложение
Filename: "{app}\SSK_Zvezda_KPI.exe"; \
  Description: "Запустить ССК Звезда KPI Monitor"; \
  Flags: nowait postinstall skipifsilent

[UninstallDelete]
; При удалении — убрать созданные файлы (БД, логи, кэш сессии)
Type: files;     Name: "{app}\zvezda.log"
Type: files;     Name: "{app}\zvezda-kpi.db"
Type: files;     Name: "{app}\.session.key"
Type: files;     Name: "{app}\.session.token"
Type: filesandordirs; Name: "{app}"

[Messages]
; Текст на экране приветствия
WelcomeLabel1=Добро пожаловать в мастер установки%nССК Звезда — KPI Monitor v5
WelcomeLabel2=Этот мастер установит систему учёта KPI и складских запасов ССК «Звезда» на ваш компьютер.%n%nРекомендуется закрыть все работающие приложения перед продолжением.
FinishedLabel=Установка ССК Звезда KPI Monitor v5 завершена.%n%nДля входа используйте:%n  Логин:  admin%n  Пароль: admin%n%nНе забудьте сменить пароль после первого входа!
