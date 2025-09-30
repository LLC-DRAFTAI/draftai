# DraftAI Documentation

Добро пожаловать в документацию проекта **DraftAI** — ИИ-система автоматизации создания чертежей инженерных сетей.

---

## 📌 Структура проекта

draftai/

├── nlp_core/ # Модуль NLP для анализа ТЗ

├── bim_core/ # Модуль BIM для обработки IFC моделей

├── mcp_server/ # MCP сервер для FreeCAD

├── scripts/ # Скрипты для настройки окружения и запуска пайплайна

├── Dockerfile.* # Docker-образ для каждого компонента

├── mkdocs.yml # Конфигурация документации

├── .github/workflows # CI/CD конфигурация GitHub Actions

└── README.md # Корневой README

## 📌 Подробно по модулям

#### NLP Core

nlp_core/config/ — настройки анализа ТЗ.

nlp_core/input/ — входные ТЗ.

nlp_core/OUT/ — результаты анализа.

nlp_core/nlp_core/run.py — основной скрипт.

nlp_core/nlp_core/run_cli.py — обёртка с argparse для CLI запуска.

#### BIM Core

bim_core/bim_core/run.py — основной модуль BIM.

bim_core/bim_core/run_cli.py — CLI-обёртка.

bim_core/runs/ — результаты обработки IFC моделей.

bim_core/samples/ — тестовые данные.

bim_core/place_radiators_clientV2.py — основной скрипт загрузки примитивов в IFC через MCP.

#### MCP Server

mcp_server/mcp_serverV3.py — запуск MCP сервера с масштабированием модели.

mcp_server/run_cli.py — CLI-обёртка.

## 📌 Последовательный запуск модулей (NLP → BIM → MCP)

**Pipeline состоит из трёх основных шагов:**

**NLP** — парсинг технического задания (DOCX/PDF/TXT) → генерируется nlp_core/OUT/result.json.

**BIM** — анализ IFC и сопоставление с данными из NLP → генерируются stubs.json и match_report.json в папке bim_core/runs/....

**MCP** — MCP-сервер (в окружении FreeCAD) принимает stubs.json и размещает примитивы (радиаторы) в активном документе FreeCAD.

Важно: шаг MCP требует локально установленного FreeCAD (модули FreeCAD/Part доступны только в окружении FreeCAD). На CI (GitHub Actions) MCP запускать нельзя — вместо этого MCP тестируется через моки или локально.

**Ожидаемые артефакты (куда смотреть)**

nlp_core/OUT/result.json — результат NLP (TZ → JSON).

bim_core/runs/stubs.json — сформированные примитивы.

bim_core/runs/match_report.json — отчёт о сопоставлении помещений.

bim_core/runs/spaces.json — отчёт о чтении параметров из IFC модели.


## 📌 Чеклист: что должно быть готово перед запуском pipeline

 - Python >= 3.11 и зависимости установлены для nlp_core и bim_core.

 - IFC-модель в bim_core/samples/ или путь к ней известен.

 - FreeCAD установлен локально и доступен (если хотите тестировать MCP).

*Процесс автоматизации запуска описан в корневом README.md.* 


