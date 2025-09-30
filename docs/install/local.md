# Локальная установка (Python + venv)

Эта инструкция — для локальной разработки (без Docker). Подойдёт, если запускать NLP, BIM и клиент MCP напрямую на машине.

## 1. Требования
- Python ≥ 3.11 (рекомендуется 3.11 — 3.13).
- Git.
- При тестировании MCP требуется локально установленный **FreeCAD** (MCP сервер работает внутри FreeCAD).


## 2. Клонирование репозитория
```bash
git clone <репозиторий-git> draftai
cd draftai```


## 3. Создание корневого виртуального окружения (рекомендуется) и устанвока зависимостей

Мы используем «гибрид»: предпочитаем корневой .venv, если его нет — используем компонентные .venv.

Windows (PowerShell)

```cd nlp_core```

```python -m venv .venv```

```.\.venv\Scripts\Activate.ps1```

```pip install --upgrade pip```
```pip install -r requirements.txt```


Linux / macOS
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel


ПРИМЕЧАНИЕ. В requirements.txt могут быть тяжёлые пакеты (transformers, ifcopenshell и т.д.) — установка займёт время.

Установка модели spaCy (обязательно для NLP)
```python -m spacy download ru_core_news_sm```

Если команда не срабатывает в текущем окружении — убедитесь, что активировали .venv перед запуском.


## 4. Запуск модулей

#### NLP Core

```python .\nlp_core\run_cli.py --out .\OUT\result.json -v```

*либо, явно:*

```python -m nlp_core.run nlp_core/input/TZ_object.docx nlp_core/OUT/result.json```


Проверь ```nlp_core/OUT/result.json.```



#### BIM Core (после успешного NLP)

PowerShell (из корня репо):

*автопоиск IFC в bim_core/samples:*

```python .\bim_core\bim_core\run_cli.py --tz .\nlp_core\OUT\result.json --out .\bim_core\runs -v```

В результате в bim_core/runs/ появятся stubs.json, match_report.json, spaces.json.


#### MCP (FreeCAD) — локально

MCP-сервер нельзя полноценно запускать вне окружения FreeCAD (модуль FreeCAD отсутствует в обычном интерпретаторе).

Запустить MCP в FreeCAD:

Открой FreeCAD GUI.

В Python-консоли (View → Panels → Python console) выполнить:

```exec(open(r"C:\path\to\draftai\mcp_server\mcp_serverV3.py", encoding="utf-8").read())```
(подставь реальный путь к файлу)

Например: ```exec(open(r"C:\draftai\mcp_server\mcp_serverV3.py", encoding="utf-8").read())```

После этого MCP будет слушать ```127.0.0.1:9090``` (или тот, что у тебя в коде).

#### Отправить примитивы на MCP:

```python .\scripts\send_stubs_cli.py --stubs bim_core/runs/stubs.json -v```

```python scripts/send_stubs_cli.py --stubs bim_core/runs/stubs.json --host 127.0.0.1 --port 9090 -v```

---

## 5. Советы / Troubleshooting

Если данные создаются внутри контейнера Docker (при использовании Docker) — см. ```docs/install/docker.md``` и как монтировать тома.

- **TZ файл не найден**

Проверьте путь, откуда вы запускаете команду. Рекомендуется запускать из корня репозитория. Используйте абсолютный путь или корректируйте относительный.

- **No spaces.json provided or generated from IFC**

Убедитесь, что ```--ifc``` указан или ```ifc_reader.export_spaces``` успешно создал ```runs/spaces.json.```
Проверьте логи ```bim_core``` — возможно ```ifc_reader``` упал из-за формата IFC.

- **ModuleNotFoundError: No module named 'FreeCAD'**

MCP можно запускать только внутри FreeCAD или с FREECAD_PATH, указывающим на папку с бинарными модулями FreeCAD.
Рекомендация: открыть FreeCAD GUI и выполнить ```exec(open(r'.../mcp_serverV3.py').read())``` в Python Console.

- **ConnectionRefusedError при отправке stubs**

MCP не слушает указанный порт: убедитесь, что MCP запущен и слушает HOST:PORT.
Проверьте, что ```send_stubs_cli.py``` посылает на тот же ```host/port```, что и MCP.

- **.venv не коммитить.** .venv должен быть в .gitignore.


## 6. Резюме

Для **PoC** удобнее локально: создать один ```.venv```, установить ```deps```, скачать **spaCy** модель, последовательно запускать ```nlp → bim → MCP в FreeCAD``` и отправлять ```stubs.json.```

## 7. Последовательный запуск скриптов (PowerShell)

```setup_dev_env.ps1``` - скрипт автоматического запуска виртуального окружения в корневой папке
запускается PowerShell командой: ```.\scripts\setup_dev_env.ps1```

```run_pipeline.ps1```  - скрипт автоматического последовательного выполнения NLP-BIM-MCP
запускается PowerShell командой: ```.\scripts\run_pipeline.ps1```. !!! Нужно проверить предварительно установку python -m spacy download ru_core_news_sm!!! без неё будет ошибка Step 1/4

Запуск скриптов (Linux/MacOS) тестировал через git_bash работает
```setup_dev_env.sh``` - скрипт автоматического запуска виртуального окружения 
```run_pipeline.sh``` - скрипт автоматического последовательного выполнения NLP-BIM-MCP 
