#!/usr/bin/env python3
"""
CLI wrapper for MCP server.

Пример:
  python run_cli.py --background -v
  python run_cli.py --host 127.0.0.1 --port 9090
  python run_cli.py --freecad-path "C:\Program Files\FreeCAD 0.21\bin" --background
"""
from __future__ import annotations
import argparse
import logging
import sys
import importlib.util
from pathlib import Path
import os

def parse_args():
    p = argparse.ArgumentParser(description="MCP Server CLI")
    p.add_argument("--host", default="127.0.0.1", help="Host для MCP сервера")
    p.add_argument("--port", type=int, default=9090, help="Port для MCP сервера")
    p.add_argument("--background", "-b", action="store_true", help="Запуск сервера в фоне (daemon thread)")
    p.add_argument("--freecad-path", help="Путь к FreeCAD bin (опционально). Можно задать переменную окружения FREECAD_PATH.", required=False)
    p.add_argument("--verbose", "-v", action="store_true", help="Подробный лог")
    return p.parse_args()

def setup_logging(verbose: bool):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s", level=level)

def import_mcp_module(mcp_path: Path):
    if not mcp_path.exists():
        logging.error("MCP сервер не найден: %s", mcp_path)
        raise FileNotFoundError(mcp_path)
    spec = importlib.util.spec_from_file_location("mcp_server_module", str(mcp_path))
    module = importlib.util.module_from_spec(spec)
    sys.modules["mcp_server_module"] = module
    loader = spec.loader
    if loader is None:
        raise ImportError("no loader")
    loader.exec_module(module)
    return module

def example_freecad_commands(mcp_file: Path) -> str:
    """Возвращает пример команд для запуска MCP внутри FreeCAD/FreeCAD-python."""
    lines = []
    lines.append("Если хотите запустить внутри FreeCAD GUI (в Python-консоли FreeCAD):")
    lines.append(f"  exec(open(r'{mcp_file}', encoding='utf-8').read())")
    lines.append("")
    lines.append("Если хотите запустить обычным python, используя интерпретатор FreeCAD (Windows пример):")
    lines.append(r"  'C:\\Program Files\\FreeCAD 0.21\\bin\\python.exe' " + f"\"{mcp_file}\"")
    lines.append("")
    lines.append("Или укажите FREECAD_PATH (путь к папке с FreeCAD .pyd) и запустите run_cli.py обычным python.")
    return "\n".join(lines)

def main():
    args = parse_args()
    setup_logging(args.verbose)

    # Если пользователь указал путь к FreeCAD — временно добавим в sys.path / env
    if args.freecad_path:
        freecad_p = Path(args.freecad_path)
        if freecad_p.exists():
            os.environ["FREECAD_PATH"] = str(freecad_p)
            if str(freecad_p) not in sys.path:
                sys.path.insert(0, str(freecad_p))
            logging.info("FREECAD_PATH установлен временно: %s", freecad_p)
        else:
            logging.warning("Указанный FREECAD_PATH не найден: %s", freecad_p)

    mcp_py = Path(__file__).resolve().parent / "mcp_serverV3.py"

    try:
        mcp_mod = import_mcp_module(mcp_py)
    except Exception as e:
        logging.exception("Не удалось импортировать mcp_serverV3.py: %s", e)
        # Подсказка пользователю как запускать внутри FreeCAD
        logging.error("FreeCAD модули не найдены. Чтобы запустить MCP локально, используйте FreeCAD.")
        logging.error(example_freecad_commands(mcp_py))
        sys.exit(2)

    # Подставляем параметры хоста/порта
    try:
        setattr(mcp_mod, "HOST", args.host)
        setattr(mcp_mod, "PORT", args.port)
    except Exception:
        logging.debug("Не удалось установить HOST/PORT в модуле (не критично).")

    # Запуск
    if args.background:
        started = False
        try:
            started = mcp_mod.run_in_background()
        except Exception as e:
            logging.exception("Ошибка при попытке запуска в фоне: %s", e)
            started = False

        if not started:
            logging.error("Сервер не был запущен в фоне. Проверьте наличие FreeCAD и повторите.")
            logging.error(example_freecad_commands(mcp_py))
            sys.exit(3)
        else:
            logging.info("MCP сервер запущен в фоне (daemon).")
            # main завершится, поток daemon продолжит работать
            return
    else:
        try:
            logging.info("Запуск MCP сервера (foreground) на %s:%s ...", args.host, args.port)
            mcp_mod.start_server()
        except Exception as e:
            logging.exception("Ошибка при запуске MCP сервера: %s", e)
            logging.error(example_freecad_commands(mcp_py))
            sys.exit(4)

if __name__ == "__main__":
    main()
