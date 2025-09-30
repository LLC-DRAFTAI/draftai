#!/usr/bin/env python3
"""
CLI wrapper for bim_core/run.py

Usage examples:
  # call with tz (NL P JSON) and out directory
  python run_cli.py --tz ../nlp_core/OUT/result.json --out runs/result_dir -v

  # or use --nlp as alias for --tz (useful in pipeline)
  python run_cli.py --nlp ../nlp_core/OUT/result.json --ifc samples/model.ifc --out runs/result_dir
"""

from __future__ import annotations
import argparse
import logging
import sys
from pathlib import Path
import importlib
import importlib.util
import runpy


def parse_args():
    p = argparse.ArgumentParser(description="BIM Core CLI wrapper")
    p.add_argument("--tz", help="Path to TZ JSON (from NLP)", required=False)
    p.add_argument("--nlp", help="Alias for --tz", required=False)
    p.add_argument("--ifc", help="Path to IFC model (optional)", required=False)
    p.add_argument("--spaces", help="Path to spaces.json (optional)", required=False)
    p.add_argument(
        "--out",
        help="Output directory path (will contain stubs.json and match_report.json)",
        required=True,
    )
    p.add_argument("--config", help="Optional config path", required=False)
    p.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    return p.parse_args()


def setup_logging(verbose: bool):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s", level=level)


def ensure_out_dir(out_path: Path):
    out_dir = out_path
    out_dir.mkdir(parents=True, exist_ok=True)


def add_parent_to_syspath():
    """
    Добавляем parent папку (bim_core/) в sys.path.
    Это нужно, чтобы import bim_core.run работал, когда запускаем wrapper из подпапки.
    """
    here = Path(__file__).resolve()
    pkg_parent = here.parents[1]  # .../bim_core
    if str(pkg_parent) not in sys.path:
        sys.path.insert(0, str(pkg_parent))


def import_bim_module():
    """
    Пытаемся импортировать bim_core.run как пакет. Если не получается,
    пробуем загрузить run.py напрямую по пути.
    """
    here = Path(__file__).resolve()
    run_py_path = here.parent / "run.py"

    try:
        module = importlib.import_module("bim_core.run")
        return module
    except SystemExit:
        # propagate - если импорт сам вызывает sys.exit
        raise
    except Exception:
        # fallback: загрузить run.py напрямую
        if run_py_path.exists():
            try:
                spec = importlib.util.spec_from_file_location(
                    "bim_core_run_local", str(run_py_path)
                )
                module = importlib.util.module_from_spec(spec)
                sys.modules["bim_core_run_local"] = module
                loader = spec.loader
                if loader is None:
                    raise ImportError(f"No loader for {run_py_path}")
                loader.exec_module(module)
                return module
            except SystemExit:
                raise
            except Exception:
                logging.exception("Ошибка при загрузке %s напрямую", run_py_path)
                raise
        else:
            logging.exception(
                "Не удалось импортировать bim_core.run и файл %s не найден.",
                run_py_path,
            )
            raise


def call_module_main_with_argv(module, argv_list):
    """
    Временно подменяем sys.argv и вызываем module.main().
    Это подходит для run.py, который использует argparse внутри своего main().
    """
    saved_argv = sys.argv[:]
    try:
        sys.argv = [
            str(Path(getattr(module, "__file__", "") or "").resolve())
        ] + argv_list
        # вызвать main (если есть)
        if hasattr(module, "main"):
            return module.main()
        # fallback: выполнить как скрипт
        runpy.run_path(getattr(module, "__file__", ""), run_name="__main__")
    finally:
        sys.argv = saved_argv


def main():
    args = parse_args()
    setup_logging(args.verbose)

    # choose tz from --tz or --nlp alias
    tz_path = args.tz or args.nlp
    if not tz_path:
        logging.error("Не указан путь к TZ JSON. Укажите --tz <path> или --nlp <path>.")
        sys.exit(1)
    tz_path = Path(tz_path)
    if not tz_path.exists():
        logging.error("TZ файл не найден: %s", tz_path)
        sys.exit(2)

    # IFC: если не указан --ifc, ищем первый *.ifc в samples/
    if args.ifc:
        ifc_path = Path(args.ifc)
        if not ifc_path.exists():
            logging.error("IFC файл не найден: %s", ifc_path)
            sys.exit(3)
    else:
        samples_dir = Path(__file__).resolve().parents[1] / "samples"
        found_ifc = (
            next(samples_dir.glob("*.ifc"), None) if samples_dir.exists() else None
        )
        if found_ifc:
            ifc_path = found_ifc
            logging.info("IFC файл не указан. Автоматически выбран: %s", found_ifc)
        else:
            ifc_path = None
            logging.warning(
                "Не найдено ни одного IFC-файла в папке samples/. Продолжаем без IFC."
            )

    # spaces optional (file)
    spaces_path = Path(args.spaces) if args.spaces else None
    if spaces_path and not spaces_path.exists():
        logging.error("spaces.json не найден: %s", spaces_path)
        sys.exit(4)

    out_path = Path(args.out)
    ensure_out_dir(out_path)

    # prepare sys.path so package import works
    add_parent_to_syspath()

    try:
        bim_mod = import_bim_module()
    except SystemExit as se:
        logging.error("Импорт bim_core.run завершился SystemExit: %s", se)
        code = int(se.code) if isinstance(se.code, int) else 1
        sys.exit(code)
    except Exception as e:
        logging.exception("Не удалось импортировать bim_core.run: %s", e)
        sys.exit(5)

    # Prepare argv for module.main() (module expects --tz/--ifc/--spaces/--out)
    argv = []
    # pass tz via --tz (note: run.py expects --tz arg name)
    argv += ["--tz", str(tz_path)]
    if ifc_path:
        argv += ["--ifc", str(ifc_path)]
    if spaces_path:
        argv += ["--spaces", str(spaces_path)]
    argv += ["--out", str(out_path)]
    if args.config:
        argv += ["--config", str(args.config)]

    try:
        # Module may define main() that uses argparse internally (your run.py does).
        # We call it by substituting sys.argv via call_module_main_with_argv.
        rc = call_module_main_with_argv(bim_mod, argv)
        # If main returned an int — use it as exit code
        if isinstance(rc, int):
            sys.exit(rc)
        # Otherwise success
        sys.exit(0)
    except SystemExit as se:
        # Handle SystemExit: 0 -> success, else -> propagate as error
        code = 0
        try:
            code = int(se.code) if se.code is not None else 0
        except Exception:
            logging.warning("SystemExit с неконвертируемым кодом: %r", se.code)
            code = 1
        if code == 0:
            logging.info("bim_core.run завершился с кодом 0 — успех.")
            sys.exit(0)
        else:
            logging.error("bim_core.run завершился с кодом %s — ошибка.", code)
            sys.exit(code)
    except Exception as e:
        logging.exception("Ошибка при выполнении bim_core.run: %s", e)
        sys.exit(6)


if __name__ == "__main__":
    main()
