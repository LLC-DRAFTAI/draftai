Модуль NLP Core отвечает за анализ текстового технического задания (ТЗ) и формирование структурированного JSON, который используется на следующих этапах пайплайна (BIM Core и MCP Server).

📂 Структура
nlp_core/
├── config/            # Конфигурационные файлы (если нужны)
├── input/             # Входные ТЗ (docx/pdf/txt)
├── nlp_core/
│   ├── __init__.py    # пустой или с минимальным кодом
│   ├── run.py         # Основная логика анализа ТЗ
│   └── run_cli.py     # CLI-обёртка (точка входа для запуска)
├── OUT/               # Результаты анализа (JSON)
├── requirements.txt   # Зависимости Python
└── README.md          # Документация модуля

⚙️ Установка

Перейдите в каталог модуля:

cd draftai\nlp_core


Создайте и активируйте виртуальное окружение:

python -m venv .venv
.\.venv\Scripts\Activate.ps1


Установите зависимости:

pip install --upgrade pip
pip install -r requirements.txt


Установите модель spaCy для русского языка:

python -m spacy download ru_core_news_sm

🚀 Запуск
Показ справки
python .\nlp_core\nlp_core\run_cli.py --help

Запуск с указанием входного файла
python .\nlp_core\nlp_core\run_cli.py --tz .\input\TZ_object.docx --out .\OUT\result.json -v

Автоматический поиск входного файла

Если --tz не указан, wrapper попытается найти первый *.docx, *.pdf или *.txt в папке nlp_core/input/:

python .\nlp_core\nlp_core\run_cli.py --out .\OUT\result.json -v

📄 Пример результата (OUT/result.json)
{
    "project_name": "«Проект системы отопления офисного здания»",
    "object_name": "«Офисное здание»",
    "building_area": "3000",
    "floor_area": "1500",
    "levels": "2",
    "ORG": ["ООО «Проектное бюро»"],
    "LOC": ["Москва"],
    "heating_system": {
        "system_name": "отопление",
        "boiler_power": "350",
        "radiator_type": "напольные",
        "temperature": "90/65",
        "heat_source": "ИТП."
    },
    "room_temperatures": {
        "Офис": "24",
        "Коридор": "16",
        "Веранда": "18"
    }
}

🔑 Основные моменты

Запускать только run_cli.py, а не run.py.

Входные файлы должны быть в формате DOCX, PDF или TXT.

Результаты сохраняются в папку OUT/.

Код возврата процесса:

0 — успешное выполнение,

>0 — ошибка (например, файл не найден или неверный формат).