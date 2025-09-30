#!/usr/bin/env python3
"""
CLI client: отправка stubs.json на MCP сервер.
"""
from __future__ import annotations
import argparse
import socket
import json
from pathlib import Path
import sys
import logging

def parse_args():
    p = argparse.ArgumentParser(description="Send stubs.json to MCP server")
    p.add_argument("--stubs", default="bim_core/runs/stubs.json", help="Path to stubs.json")
    p.add_argument("--host", default="127.0.0.1", help="MCP host")
    p.add_argument("--port", type=int, default=9090, help="MCP port")
    p.add_argument("--timeout", type=float, default=5.0, help="Socket connect/send timeout (seconds)")
    p.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    return p.parse_args()

def setup_logging(verbose: bool):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s", level=level)

def main():
    args = parse_args()
    setup_logging(args.verbose)

    stubs_path = Path(args.stubs)
    if not stubs_path.exists():
        logging.error("Файл stubs не найден: %s", stubs_path)
        sys.exit(2)

    try:
        with stubs_path.open("r", encoding="utf-8") as f:
            stubs = json.load(f)
    except Exception as e:
        logging.exception("Ошибка чтения JSON: %s", e)
        sys.exit(3)

    data = (json.dumps(stubs, ensure_ascii=False) + "\n").encode("utf-8")

    try:
        with socket.create_connection((args.host, args.port), timeout=args.timeout) as s:
            s.sendall(data)
        logging.info("✅ Отправлено %d элементов в %s:%s", len(stubs), args.host, args.port)
    except ConnectionRefusedError:
        logging.error("Connection refused: Проверьте, что MCP сервер запущен на %s:%s", args.host, args.port)
        logging.error("Если используете FreeCAD, запустите MCP внутри FreeCAD (см. README).")
        sys.exit(4)
    except Exception as e:
        logging.exception("Ошибка при отправке: %s", e)
        sys.exit(5)

if __name__ == "__main__":
    main()
