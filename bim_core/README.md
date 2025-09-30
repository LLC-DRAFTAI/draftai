# BIM Core

**BIM Core** — модуль для анализа IFC-модели и сопоставления помещений с данными из NLP (result.json). 
В результате работы модуль генерирует `stubs.json` (список примитивов) и `match_report.json` (отчёт о сопоставлении),
которые затем используются MCP Server для размещения примитивов в FreeCAD.

---

## Структура папки `bim_core/`

```
bim_core/
├── bim_core/
│   ├── __init__.py
│   ├── run.py              # основная логика анализа IFC и сопоставления
│   ├── run_cli.py          # CLI-wrapper (рекомендуется запускать его)
│   ├── ifc_reader.py       # экспорт spaces.json из IFC
│   ├── generate_stubs.py   # формирование примитивов/заглушек
│   ├── match_zones.py      # логика сопоставления помещений -> ТЗ
│   ├── params_adapter.py   # чтение/адаптация параметров из TZ json
│   └── synonyms.py         # словарь/маппинг синонимов
├── runs/                   # результаты анализа (stubs.json, match_report.json и т.д.)
├── samples/                # примеры входных данных (IFC, result.json из NLP)
├── place_radiators_clientV2.py  # клиент для загрузки stubs через MCP (тесты/утилиты)
├── requirements.txt
└── README.md               # этот файл
```

---

## Требования

- Python `>= 3.11` (проект тестировался на Python 3.13).  
- Для работы MCP (финальный этап визуализации) требуется локально установленный FreeCAD (не нужен для запуска анализа BIM Core).  
- Рекомендуется использовать виртуальное окружение (например, `.venv`), которое **не** коммитить.

---

## Установка (локально)

```powershell
cd draftai\
python -m venv .venv
.\.venv\Scripts\Activate.ps1    # PowerShell
pip install --upgrade pip
```

Для Linux/macOS используйте `python -m venv .venv && source .venv/bin/activate`.

---

## Запуск (рекомендуется через `run_cli.py`)

**Всегда** предпочтительнее запускать `bim_core/bim_core/run_cli.py`, а не `run.py` напрямую — wrapper подготавливает окружение, автопоиск IFC, корректно управляет `sys.path` и cwd.

### Примеры (из корня репозитория)

1. Запуск с явным указанием IFC-файла:
```powershell
python .\bim_core\bim_core\run_cli.py --tz .\nlp_core\OUT\result.json --ifc .\bim_core\samples\OfficeBuilding41_IFC1.ifc --out .\bim_core\runs\test_out -v
```

2. Запуск с автопоиском IFC в `bim_core/samples/`:
```powershell
python .\bim_core\bim_core\run_cli.py --tz .\nlp_core\OUT\result.json --out .\bim_core\runs\test_out -v
```


**Аргументы:**
- `--tz` / `--nlp`: путь к JSON из NLP (обязателен).
- `--ifc`: путь к IFC модели (опционально — автопоиск по `bim_core/samples/`).
- `--spaces`: путь к `spaces.json` (альтернатива `--ifc`).
- `--out`: директория вывода (обязательно).
- `--config`: опциональная конфигурация.
- `--verbose` / `-v`: подробный лог.

---

## Что генерирует BIM Core

В папке `--out` (например `bim_core/runs/`) вы найдёте:

- `stubs.json` — список сформированных примитивов для загрузки в MCP/FreeCAD. Пример элемента:
```json
{
  "id": "space-123",
  "name": "Офис",
  "system": "heating",
  "t_in": 90,
  "t_out": 65,
  "temperature": 24,
  "radiator_type": "напольные",
  "coordinates": [1.23, 4.56, 0.0]
}
```

- `match_report.json` — подробный отчёт с полями `matched` и `unmatched_spaces` (с предложениями по сопоставлению).
- `spaces.json` — подробный отчёт параметрами ifc модели.

---

## Интеграция с MCP / FreeCAD

После генерации `stubs.json` вы можете отправить его на MCP server (FreeCAD) для фактического размещения объектов. Пример (клиент в `scripts/send_stubs_cli.py`):

```powershell
python .\scripts\send_stubs_cli.py --stubs .\bim_core\runs\stubs.json -v
```

**Важно:** MCP требует установленного FreeCAD — этот шаг выполняется локально и не входит в CI по умолчанию.

---

## Отладка и часто встречающиеся ошибки

- **TZ файл не найден** — проверьте, что путь в `--tz` корректен; запускайте команды из корня репозитория или используйте абсолютные пути.  
- **No spaces.json provided or generated from IFC.** — укажите `--spaces` или проверьте, что `export_spaces` успешно создал `spaces.json` (в `bim_core/runs/` или `bim_core/bim_core/runs/` в зависимости от cwd).  
- **Проблемы с сопоставлением** — проверьте `bim_core/bim_core/synonyms.py` и `match_zones.py`; для диагностики запускайте с `-v`.  
- **IFC parser issues** — если `ifc_reader` падает, проверьте файл IFC (формат, целостность) и зависимости (парсеры IFC).

---

## Тестирование и CI

- В CI (.github/workflows/ci.yml) выполняются линтеры и тесты для NLP и BIM; шаги, зависящие от FreeCAD (MCP), пропускаются.  
- Рекомендуется писать unit-тесты для `match_zones.py`, `params_adapter.py` и `generate_stubs.py`. Для тестирования функций, взаимодействующих с FreeCAD, используйте моки `FreeCAD`/`Part`.

---

## Вклад и лицензия

- Пожалуйста, открывайте issue / pull request на GitHub. Добавьте воспроизводимый пример и логи (`-v`) при ошибках.  
- Лицензия проекта — укажите в корне (`LICENSE`) (например MIT или Apache-2.0).

---

## Контакты
Если требуется помощь с настройкой или CI, откройте issue в репозитории с подробным описанием окружения и шагов воспроизведения.
