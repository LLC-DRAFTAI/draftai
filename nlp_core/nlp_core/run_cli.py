#!/usr/bin/env python3
"""
CLI wrapper for nlp_core/run.py
from pathlib import Path
import sys

Usage examples:
  python run_cli.py --tz nlp_core/input/my_tz.docx --out nlp_core/OUT/result.json
  python run_cli.py --out nlp_core/OUT/result.json   # ищет файл в nlp_core/input/
"""

import argparse
import logging
import sys
from pathlib import Path
import importlib

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))


def parse_args():
    p = argparse.ArgumentParser(description="NLP Core CLI wrapper")
    p.add_argument(
        "--tz",
        help="Path to input technical assignment (docx/pdf/txt). If omitted, wrapper will try to find a file in nlp_core/input/.",
        default=None,
    )
    p.add_argument(
        "--out", help="Output JSON file path", default="nlp_core/OUT/result.json"
    )
    p.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    return p.parse_args()


def setup_logging(verbose: bool):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s", level=level)


def find_input_in_folder() -> Path | None:
    here = Path(__file__).resolve()
    comp_input = here.parents[1] / "input"
    if comp_input.exists() and comp_input.is_dir():
        for ext in ("*.docx", "*.pdf", "*.txt"):
            files = sorted(comp_input.glob(ext))
            if files:
                return files[0]
            repo_input = here.parents[2] / "input"
    if repo_input.exists() and repo_input.is_dir():
        for ext in ("*.docx", "*.pdf", "*.txt"):
            files = sorted(repo_input.glob(ext))
            if files:
                return files[0]
    return None


def ensure_out_dir(out_path: Path):
    out_dir = out_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)


def import_nlp_module():
    """
    Импортируем модуль nlp_core.run. Поскольку в твоём run.py при импортe
    происходит попытка загрузить модель spacy (и возможный sys.exit),
    перехватываем SystemExit для аккуратного сообщения.
    """
    try:
        module = importlib.import_module("nlp_core.run")
        return module
    except SystemExit as se:
        # Если импорт вызвал sys.exit (например, из-за отсутствия модели spaCy),
        # сообщим пользователю и завершимся с кодом 1.
        print(
            "Импорт nlp_core.run завершился с ошибкой (SystemExit). Проверьте, установлена ли модель spaCy 'ru_core_news_sm' и зависимости."
        )
        raise se
    except Exception as e:
        logging.exception("Ошибка при импорте nlp_core.run: %s", e)
        raise


def main():
    args = parse_args()
    setup_logging(args.verbose)

    # Определяем входной файл
    if args.tz:
        input_path = Path(args.tz)
    else:
        found = find_input_in_folder()
        if found:
            input_path = found
            logging.info("Входной файл не указан. Использую найденный: %s", input_path)
        else:
            logging.error(
                "Входной файл не указан и не найден в nlp_core/input/. Укажите --tz <path>."
            )
            sys.exit(1)

    if not input_path.exists():
        logging.error("Входной файл не найден: %s", input_path)
        sys.exit(1)

    out_path = Path(args.out)
    ensure_out_dir(out_path)

    # Импортировать модуль и вызвать main(input_file, output_file)
    try:
        nlp_mod = import_nlp_module()
    except SystemExit:
        # Сообщение уже выведено в import_nlp_module
        sys.exit(1)
    except Exception:
        sys.exit(2)

    # Проверяем, что в модуле есть callable main(input, output) или run(...)
    try:
        if hasattr(nlp_mod, "main"):
            logging.info(
                "Вызов %s.main(%s, %s)", nlp_mod.__name__, input_path, out_path
            )
            rc = nlp_mod.main(str(input_path), str(out_path))
            # Если main вернул код — используем его как exit code
            if isinstance(rc, int):
                sys.exit(rc)
            else:
                sys.exit(0)
        elif hasattr(nlp_mod, "run"):
            logging.info("Вызов %s.run(%s, %s)", nlp_mod.__name__, input_path, out_path)
            nlp_mod.run(str(input_path), str(out_path))
            sys.exit(0)
        else:
            logging.error(
                "В модуле nlp_core.run не найдено expected entrypoint (main или run)."
            )
            sys.exit(3)
    except SystemExit as se:
        # Если run.py сделал sys.exit(0) — считаем это успешным завершением.
        # Если sys.exit(c) где c != 0 — считаем ошибкой и возвращаем код.
        code = 0
        try:
            # se.code может быть None, int или строка
            code = int(se.code) if se.code is not None else 0
        except Exception:
            # если не число — считать ошибкой
            logging.warning("SystemExit с неконвертируемым кодом: %r", se.code)
            code = 1

        if code == 0:
            logging.info("nlp_core.run завершился с кодом 0 — успех.")
            sys.exit(0)
        else:
            logging.error(
                "nlp_core.run завершился с кодом %s — считаем это ошибкой.", code
            )
            sys.exit(code)


if __name__ == "__main__":
    main()
