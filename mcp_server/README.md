# MCP Server (FreeCAD)

**MCP Server** — лёгкий TCP-сервер, который принимает `stubs.json` (список примитивов) и размещает примитивы (радиаторы) в активном документе FreeCAD.  
Проект ориентирован на локальную работу: MCP запускается внутри FreeCAD (GUI) или через системный Python при наличии доступа к библиотекам FreeCAD (переменная окружения `FREECAD_PATH`).

> Важно: модули `FreeCAD`/`Part` доступны **только** в окружении FreeCAD или если вы указали корректную папку с бинарными модулями через `FREECAD_PATH`. MCP не запускается в CI (GitHub Actions) по умолчанию — FreeCAD там нет.

---

## Структура папки `mcp_server/`

```
mcp_server/
├── mcp_serverV3.py        # основной код сервера (безопасен при импорте без FreeCAD)
├── run_cli.py             # CLI-wrapper для запуска из системного Python
└── README.md              # этот файл
```

---

## Требования

- Python `>= 3.11` (для запуска wrapper и клиентских утилит).  
- Для фактического размещения примитивов — локально установленный **FreeCAD** (GUI или FreeCAD Python).  
- При запуске через системный `python` укажите `FREECAD_PATH`, указывающую на папку с `FreeCAD.pyd`/бинарными модулями (пример: `C:\Program Files\FreeCAD 0.21\bin`).

---

## Установка (локально)

1. Клонируйте репозиторий и перейдите в корень проекта.  
2. (Опционально) Создайте виртуальное окружение для утилит/скриптов `scripts/`:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # PowerShell
pip install --upgrade pip
# затем установка зависимостей для nlp/bim при необходимости
```

> MCP сам по себе не имеет внешних pip-зависимостей кроме стандартных библиотек, но для запуска pipeline нужны зависимости NLP/BIM.

---

## Сценарии запуска

### 1) Быстрый запуск внутри FreeCAD (рекомендуется для локального теста)

Откройте FreeCAD GUI → *Python Console* и выполните:

```python
exec(open(r"C:\path\to\draftai\mcp_server\mcp_serverV3.py", encoding="utf-8").read())
```

При выполнении как `__main__` модуль попытается:
- при необходимости создать новый документ (если ActiveDocument == None);
- запустить сервер в фоновом потоке (`run_in_background()`), чтобы GUI остался интерактивным.

Если автозапуск прошёл успешно — в Python Console/Report View появятся сообщения о старте сервера.

---

**Опции `run_cli.py`:**
- `--host` (по умолчанию `127.0.0.1`) — хост для привязки.  
- `--port` (по умолчанию `9090`) — TCP-порт.  
- `--background` / `-b` — запуск в фоне (daemon thread).  
- `--freecad-path` — путь к папке FreeCAD bin (опционально).  
- `--verbose` / `-v` — подробные логи.

---

### 3) Отправка `stubs.json` (клиент)

После того как BIM сформировал `stubs.json` (в `bim_core/runs/.../stubs.json`), отправьте его на MCP:

```powershell
python .\scripts\send_stubs_cli.py --stubs bim_core/runs/stubs.json -v

```

Клиент подключится к MCP и отправит JSON (одна строка + `\n`). В активном документе FreeCAD должны появиться объекты.

---

## Поведение кода и безопасность запуска в CI

- `mcp_serverV3.py` написан так, чтобы **безопасно импортироваться без FreeCAD**: при отсутствии FreeCAD модуль не падает, а логирует подсказки. Это позволяет запускать CI (линеры, тесты NLP/BIM) без ошибок.  
- Автозапуск при `__main__` (вызов `exec(...)` в FreeCAD) — удобная интерактивная фича; при импорте в wrapper (`run_cli.py`) автозапуск не происходит (чтобы CI/импорт не стартовал сервер).  
- В CI **не** запускаются шаги, требующие FreeCAD. Для покрытий, зависящих от MCP, используйте моки `FreeCAD`/`Part` в тестах.

---

## Логи и видимость в FreeCAD

- Для удобства логирование в `mcp_serverV3.py` направлено в стандартный `logging`. Мы также добавили `FreeCAD`-лог-хендлер, который при наличии `FreeCAD` перенаправляет `logging` в Report View / Python Console (`FreeCAD.Console.PrintMessage` / `PrintError`).  
- Если вы не видите сообщений в Report View, убедитесь, что вы:
  - выполнили `exec(...)` внутри FreeCAD (или подключили `run_cli.py` с `--freecad-path`),  
  - Report View открыт (View → Panels → Report view).  

---

## Troubleshooting (частые ошибки)

- **`ModuleNotFoundError: No module named 'FreeCAD'`**  
  — Запустите скрипт внутри FreeCAD (exec) или укажите `FREECAD_PATH` перед запуском `run_cli.py`.

- **`ConnectionRefusedError` при отправке stubs**  
  — MCP не слушает порт. Проверьте, запущен ли MCP (FreeCAD console / run_cli logs), и совпадают ли host/port у клиента и сервера.

- **Логи не отображаются в Report View**  
  — Убедитесь, что `attach_freecad_logging()` вызван (в `mcp_serverV3.py` он вызывается после успешного импорта `FreeCAD`) и Report View открыт.

---

## Интеграция с Pipeline

- В `scripts/run_pipeline_local.*` логика pipeline формирует `stubs.json` (NLP → BIM), затем предлагает/ждёт запуска MCP в FreeCAD, и отправляет `stubs.json` через `send_stubs_cli.py`. Это комбинация автоматизации и ручного шага, необходимого из-за GUI-зависимости FreeCAD.

---

## Тестирование

- Локально: откройте FreeCAD, выполните `exec(...)` или используйте `run_cli.py`, затем запустите `send_stubs_cli.py` и проверьте объекты в документе.  
- В CI: тесты, которые требуют работы с `FreeCAD` необходимо запускать с моками; сетевой клиент/сервер можно протестировать локально с простым TCP-эхо-сервером.

---

## Вклад и лицензия

- Открывайте issue / pull request на GitHub. При добавлении новых фич указывайте шаги воспроизведения и логи (`-v`).  
- Убедитесь, что `FREECAD_PATH` не хардкодится в коммитах — оставляйте инструкцию в README вместо конкретных путей.

---

