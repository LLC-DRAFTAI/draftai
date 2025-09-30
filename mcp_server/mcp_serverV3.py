#!/usr/bin/env python3
"""
MCP Server (FreeCAD) — размещение примитивов (радиаторов) по stubs.json.

Поведение:
- безопасно импортируется без FreeCAD (в CI не падает),
- если выполняется как скрипт в FreeCAD (exec(...) в Python Console) — попытается автоматически
  создать документ (если нужно) и запустить сервер в фоне,
- предоставляет старт/запуск в фоне: start_server(), run_in_background().
"""

from __future__ import annotations
import os
import sys
import socket
import json
import threading
import logging

# Логирование по умолчанию (возможно caller переопределит уровень)
logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s", level=logging.INFO)

# ----- BEGIN INSERT: FreeCAD logging handler -----

class FreeCADLogHandler(logging.Handler):
    """logging.Handler, который направляет сообщения в FreeCAD Report View / Python Console."""
    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            # Если FreeCAD доступен — делаем вывод через его Console API.
            # Используем PrintError для ошибок и PrintMessage для остального.
            if 'FreeCAD' in globals() and globals().get('FreeCAD') is not None:
                try:
                    if record.levelno >= logging.ERROR:
                        FreeCAD.Console.PrintError(msg + "\n")
                    else:
                        FreeCAD.Console.PrintMessage(msg + "\n")
                    return
                except Exception:
                    # если FreeCAD присутствует, но Console.* недоступен — fallback на stdout
                    pass
            # fallback — вывод в stderr/stdout
            if record.levelno >= logging.ERROR:
                print(msg, file=sys.stderr)
            else:
                print(msg)
        except Exception:
            # гарантируем, что логгер не будет ломаться из-за ошибок в handler-е
            pass

def attach_freecad_logging(level: int = logging.DEBUG) -> None:
    """
    Добавляет FreeCADLogHandler к корневому логгеру, если он ещё не добавлен.
    Вызывать **после** успешного импорта FreeCAD.
    """
    root = logging.getLogger()
    # проверяем, не добавлен ли уже этот handler
    for h in root.handlers:
        if isinstance(h, FreeCADLogHandler):
            return
    fh = FreeCADLogHandler()
    fh.setLevel(level)
    fmt = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
    fh.setFormatter(fmt)
    root.addHandler(fh)
# ----- END INSERT -----

# Попытка подложить путь к FreeCAD из переменной окружения FREECAD_PATH
_freecad_env = os.environ.get("FREECAD_PATH")
if _freecad_env:
    # если путь указывает на бинарную папку, добавим её
    if os.path.exists(_freecad_env) and _freecad_env not in sys.path:
        sys.path.insert(0, _freecad_env)
        logging.debug("Добавлен FREECAD_PATH в sys.path: %s", _freecad_env)

# Попытка импортировать FreeCAD (рабочая при запуске внутри FreeCAD или если FREECAD_PATH корректен)
try:
    import FreeCAD  # type: ignore
    import Part     # type: ignore
    # подключаем лог-хендлер, чтобы logging шёл в Report View
    attach_freecad_logging()
    logging.debug("FreeCAD logging handler attached")
except Exception:
    FreeCAD = None
    Part = None
    logging.warning("⚠ FreeCAD не найден. MCP сервер можно запускать только локально в окружении FreeCAD.")

# По умолчанию
HOST = "127.0.0.1"
PORT = 9090

def create_radiator(doc, stub: dict):
    """Создает радиатор в FreeCAD документе по данным stub."""
    if FreeCAD is None:
        logging.error("FreeCAD не доступен — невозможно создать примитив.")
        return None

    coords = stub.get("coordinates", [0, 0, 0])
    try:
        x, y, z = [float(c) * 1000 for c in coords]  # метры -> мм
    except Exception:
        logging.warning("Некорректные coordinates в stub, использую [0,0,0]")
        x, y, z = 0.0, 0.0, 0.0

    length = float(stub.get("length", 0.2)) * 1000
    width  = float(stub.get("width", 0.06)) * 1000
    height = float(stub.get("height", 0.01)) * 1000

    rtype = stub.get("radiator_type", "box")

    try:
        if rtype == "cylinder":
            obj = doc.addObject("Part::Cylinder", f"Radiator_{stub.get('id','')}")
            obj.Radius = width / 2
            obj.Height = height
            obj.Placement.Base = FreeCAD.Vector(x, y, z - height / 2)
        else:
            obj = doc.addObject("Part::Box", f"Radiator_{stub.get('id','')}")
            obj.Length = length
            obj.Width  = width
            obj.Height = height
            obj.Placement.Base = FreeCAD.Vector(
                x - length / 2,
                y - width / 2,
                z - height / 2
            )
        try:
            obj.ViewObject.ShapeColor = (1.0, 1.0, 0.0)
        except Exception:
            # В headless/без GUI ViewObject может быть недоступен
            pass
        logging.info("✅ Радиатор %s -> XYZ=(%.1f, %.1f, %.1f) мм", stub.get("id","?"), x, y, z)
        return obj
    except Exception as e:
        logging.exception("Ошибка создания примитива: %s", e)
        return None

def handle_client(conn: socket.socket, addr):
    logging.info("🔌 Подключение: %s", addr)
    buffer = ""
    try:
        while True:
            data = conn.recv(4096).decode("utf-8")
            if not data:
                break
            buffer += data
            # принимаем сообщения, разделённые newline
            while "\n" in buffer:
                msg, buffer = buffer.split("\n", 1)
                try:
                    stubs = json.loads(msg)
                except Exception as e:
                    logging.error("❌ Ошибка парсинга JSON от клиента: %s", e)
                    continue

                if FreeCAD is None:
                    logging.error("❌ FreeCAD недоступен. Нельзя разместить stubs.")
                    continue

                doc = getattr(FreeCAD, "ActiveDocument", None)
                if doc is None:
                    logging.error("❌ Нет активного документа FreeCAD. Создайте новый документ в GUI.")
                    continue

                for stub in stubs:
                    create_radiator(doc, stub)

                try:
                    doc.recompute()
                except Exception:
                    logging.debug("recompute() вызвал исключение или недоступен в этом окружении.")
                logging.info("📦 Размещено %d радиаторов", len(stubs))
    finally:
        try:
            conn.close()
        except Exception:
            pass

def start_server() -> None:
    """Блокирующий запуск сервера; если FreeCAD не доступен — не запускает."""
    if FreeCAD is None:
        logging.error("❌ FreeCAD не найден. MCP сервер не может быть запущен в этом окружении.")
        return

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        logging.info("🚀 MCP сервер запущен на %s:%s", HOST, PORT)
        try:
            while True:
                conn, addr = s.accept()
                threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
        except KeyboardInterrupt:
            logging.info("Остановка MCP сервера (KeyboardInterrupt).")
        except Exception as e:
            logging.exception("Ошибка в TCP-сервере: %s", e)

def run_in_background() -> bool:
    """
    Попытка запустить сервер в фоновом потоке (daemon).
    Возвращает True если поток создан и FreeCAD доступен, иначе False.
    """
    if FreeCAD is None:
        logging.error("❌ FreeCAD не найден. Невозможно запустить сервер в фоне.")
        return False

    t = threading.Thread(target=start_server, daemon=True)
    t.start()
    logging.info("✅ MCP сервер запущен в фоне (daemon thread).")
    return True


# --- Авто-старт при запуске файла как скрипта (например exec(...) в FreeCAD Python Console) ---
if __name__ == "__main__":
    # Если FreeCAD недоступен — выводим понятные инструкции, не падая
    if FreeCAD is None:
        logging.error("⚠ FreeCAD не найден в текущем окружении. MCP сервер можно запускать только внутри FreeCAD.")
        logging.error("Примеры запуска:")
        logging.error("  - В FreeCAD Python Console:")
        logging.error("      exec(open(r'C:\\path\\to\\mcp_serverV3.py', encoding='utf-8').read())")
        logging.error("  - Или системным python с указанием FREECAD_PATH (PowerShell пример):")
        logging.error(r"      $env:FREECAD_PATH='C:\Program Files\FreeCAD 0.21\bin'")
        logging.error(r"      python C:\path\to\mcp_serverV3.py")
    else:
        # Попытка убедиться, что есть активный документ (создадим, если нет)
        try:
            if getattr(FreeCAD, "ActiveDocument", None) is None:
                FreeCAD.newDocument("MCP_doc")
                logging.info("Создан новый FreeCAD документ 'MCP_doc' для MCP сервера.")
        except Exception:
            logging.debug("Не удалось автоматически создать документ (возможно headless/без GUI).")

        # Запуск в фоне (daemon). Если запуск не удался, сообщим и покажем инструкцию.
        try:
            ok = run_in_background()
            if ok:
                logging.info("Авто-старт: MCP сервер запущен в фоне.")
            else:
                logging.error("Авто-старт: MCP сервер не запущен. Проверьте FreeCAD окружение.")
        except Exception as e:
            logging.exception("Исключение при попытке автозапуска MCP: %s", e)
