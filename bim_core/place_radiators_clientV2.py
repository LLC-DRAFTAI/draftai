import socket
import json

# ==== Параметры ====
STUBS_FILE = r"C:\DraftAI_PoC_BIM_Core_IFC_USER\runs\stubs.json"
MCP_HOST = "127.0.0.1"
MCP_PORT = 9090

# Загружаем stubs.json
with open(STUBS_FILE, "r", encoding="utf-8") as f:
    stubs = json.load(f)

# Подключаемся к MCP серверу и отправляем данные
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((MCP_HOST, MCP_PORT))
    s.sendall((json.dumps(stubs) + "\n").encode("utf-8"))
    print(f"✅ Отправлено {len(stubs)} радиаторов в MCP сервер")
